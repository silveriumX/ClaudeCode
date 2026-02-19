# Monitor Pipeline

> Настройка автоматического непрерывного мониторинга соцсетей (Reddit, Telegram, HN, Twitter/X)
> с LLM-скорингом и доставкой структурированных отчётов в Telegram/Slack/Email.

---

## Когда использовать

- "Настрой мониторинг темы X в соцсетях"
- "Хочу получать еженедельные отчёты по теме Y"
- "Создай бота, который следит за упоминаниями Z"
- "Как настроить алерты по ключевым словам в Telegram-каналах?"
- "/monitor-pipeline"

---

## Архитектура системы

```
СБОР ДАННЫХ          ОБРАБОТКА           ХРАНЕНИЕ            ДОСТАВКА
─────────────        ──────────          ──────────           ────────
Reddit API    ──┐
Telegram      ──┤    Дедупликация  ──→  SQLite/Postgres  ──→ Telegram bot
(Telethon)      ├──→ LLM scoring   ──→  (scored_posts)   ──→ Slack webhook
RSS/HN        ──┤    Релевантность                        ──→ Email
Exa search    ──┘    Кластеризация ──→  weekly_reports   ──→ Markdown файл
                      ↓ по расписанию
                   APScheduler
                   (cron jobs)
```

**Минимальный стек (Python):**
```
APScheduler    — cron scheduling
praw           — Reddit (если есть доступ)
telethon       — Telegram MTProto
feedparser     — RSS + Hacker News
exa-py         — семантический поиск
anthropic      — LLM scoring + report generation
redis          — дедупликация (опционально, SQLite тоже ок)
python-telegram-bot — доставка отчётов
```

---

## Структура проекта

```
monitor/
├── .env                    # API ключи
├── config.yaml             # топики, источники, расписание
├── main.py                 # точка входа
├── collectors/
│   ├── reddit.py           # PRAW collector
│   ├── telegram.py         # Telethon collector
│   ├── rss.py              # RSS/HN collector
│   └── exa_collector.py    # Exa search collector
├── processors/
│   ├── dedup.py            # дедупликация
│   ├── scorer.py           # LLM relevance scoring
│   └── reporter.py         # генерация отчётов
├── storage/
│   └── db.py               # SQLite/Postgres
├── delivery/
│   ├── telegram_bot.py     # Telegram delivery
│   └── slack.py            # Slack webhook
└── scheduler.py            # APScheduler jobs
```

---

## Конфигурация (config.yaml)

```yaml
monitors:
  - name: "AI Coding Tools"
    topics:
      - "Claude Code"
      - "Cursor IDE"
      - "AI coding assistant"
    sources:
      - reddit
      - hacker_news
      - exa_web
    period_hours: 6          # как часто собирать
    min_relevance_score: 6   # порог LLM-скоринга (1-10)

  - name: "Telegram Monitoring Tech"
    topics:
      - "telegram scraping"
      - "telethon"
    sources:
      - telegram_channels
      - reddit
    telegram_channels:
      - "@python_ru"
      - "@devops_chat"
    period_hours: 12

delivery:
  telegram:
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_REPORT_CHAT_ID}"
    report_schedule: "0 9 * * 1"   # каждый понедельник в 9:00

  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    report_schedule: "0 9 * * 1"

storage:
  type: sqlite               # sqlite | postgres
  path: "monitor.db"        # для sqlite
  # dsn: "postgresql://..."  # для postgres

dedup:
  backend: sqlite            # sqlite | redis
  ttl_days: 30
```

---

## Коллекторы

### Reddit (PRAW)

```python
# collectors/reddit.py
import praw
from datetime import datetime, timedelta
from typing import List, Dict

def collect_reddit(topics: List[str], period_hours: int) -> List[Dict]:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="MonitorBot/1.0"
    )

    posts = []
    since = datetime.utcnow() - timedelta(hours=period_hours)

    for topic in topics:
        # Поиск по всему Reddit
        for submission in reddit.subreddit("all").search(
            topic,
            sort="new",
            time_filter="day",
            limit=50
        ):
            if datetime.utcfromtimestamp(submission.created_utc) > since:
                posts.append({
                    "source": "reddit",
                    "url": f"https://reddit.com{submission.permalink}",
                    "title": submission.title,
                    "text": submission.selftext[:1000],
                    "score": submission.score,
                    "created_at": datetime.utcfromtimestamp(submission.created_utc),
                    "metadata": {
                        "subreddit": submission.subreddit.display_name,
                        "comments": submission.num_comments
                    }
                })

    return posts
```

### Telegram (Telethon — MTProto)

```python
# collectors/telegram.py
# ВАЖНО: требует user account (не бот токен!)
# Используй отдельный аккаунт, не основной!
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterEmpty
import asyncio

class TelegramCollector:
    def __init__(self, api_id: int, api_hash: str, session_name: str = "monitor_session"):
        self.client = TelegramClient(session_name, api_id, api_hash)

    async def collect_keywords(
        self,
        channels: List[str],
        keywords: List[str],
        limit_per_channel: int = 100
    ) -> List[Dict]:
        """Собирает сообщения из каналов, содержащие ключевые слова"""
        posts = []

        async with self.client:
            for channel in channels:
                try:
                    entity = await self.client.get_entity(channel)
                    messages = await self.client.get_messages(entity, limit=limit_per_channel)

                    for msg in messages:
                        if not msg.text:
                            continue
                        if any(kw.lower() in msg.text.lower() for kw in keywords):
                            posts.append({
                                "source": "telegram",
                                "url": f"https://t.me/{channel.lstrip('@')}/{msg.id}",
                                "title": "",
                                "text": msg.text[:1000],
                                "score": msg.views or 0,
                                "created_at": msg.date,
                                "metadata": {"channel": channel, "views": msg.views}
                            })
                except Exception as e:
                    logger.error(f"Ошибка при сборе {channel}: {e}")

        return posts

    async def start_realtime_listener(
        self,
        channels: List[str],
        keywords: List[str],
        callback  # async function(post: Dict)
    ):
        """Real-time мониторинг — слушает новые сообщения"""
        async with self.client:
            @self.client.on(events.NewMessage(chats=channels))
            async def handler(event):
                if any(kw.lower() in event.message.text.lower() for kw in keywords):
                    post = {
                        "source": "telegram_realtime",
                        "url": f"https://t.me/...",
                        "text": event.message.text,
                        "score": 0,
                        "created_at": event.message.date
                    }
                    await callback(post)

            await self.client.run_until_disconnected()
```

### Exa (семантический поиск — без API лимитов Reddit)

```python
# collectors/exa_collector.py
from exa_py import Exa
from datetime import datetime, timedelta

def collect_exa(
    topics: List[str],
    domains: List[str] = None,
    period_hours: int = 24,
    num_results: int = 20
) -> List[Dict]:
    exa = Exa(api_key=os.getenv("EXA_API_KEY"))
    since = (datetime.now() - timedelta(hours=period_hours)).isoformat()

    posts = []
    for topic in topics:
        kwargs = {
            "start_published_date": since,
            "num_results": num_results,
            "contents": {"highlights": True}
        }
        if domains:
            kwargs["include_domains"] = domains

        results = exa.search_and_contents(topic, **kwargs)

        for r in results.results:
            posts.append({
                "source": f"exa_{','.join(domains or ['web'])}",
                "url": r.url,
                "title": r.title or "",
                "text": (r.highlights or [r.text or ""])[0][:800],
                "score": 0,
                "created_at": datetime.fromisoformat(r.published_date) if r.published_date else datetime.now(),
                "metadata": {}
            })

    return posts
```

### RSS / Hacker News

```python
# collectors/rss.py
import feedparser
from datetime import datetime, timezone

RSS_SOURCES = {
    "hacker_news_top": "https://hnrss.org/frontpage",
    "hacker_news_new": "https://hnrss.org/newest",
    "hacker_news_search": "https://hnrss.org/newest?q={topic}",
}

def collect_rss(topic: str, period_hours: int = 24) -> List[Dict]:
    url = RSS_SOURCES["hacker_news_search"].format(topic=topic.replace(" ", "+"))
    feed = feedparser.parse(url)

    posts = []
    since = datetime.now(timezone.utc) - timedelta(hours=period_hours)

    for entry in feed.entries:
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if published < since:
            continue

        posts.append({
            "source": "hacker_news",
            "url": entry.link,
            "title": entry.title,
            "text": entry.get("summary", "")[:500],
            "score": 0,
            "created_at": published,
            "metadata": {"comments": entry.get("comments", "")}
        })

    return posts
```

---

## Дедупликация

```python
# processors/dedup.py
import hashlib
import sqlite3
from datetime import datetime, timedelta

class Deduplicator:
    def __init__(self, db_path: str = "monitor.db", ttl_days: int = 30):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_urls (
                url_hash TEXT PRIMARY KEY,
                url TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def is_new(self, url: str) -> bool:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cursor = self.conn.execute(
            "SELECT 1 FROM seen_urls WHERE url_hash = ?", (url_hash,)
        )
        if cursor.fetchone():
            return False

        self.conn.execute(
            "INSERT INTO seen_urls (url_hash, url) VALUES (?, ?)",
            (url_hash, url)
        )
        self.conn.commit()
        return True

    def filter_new(self, posts: List[Dict]) -> List[Dict]:
        return [p for p in posts if self.is_new(p["url"])]

    def cleanup_old(self):
        """Удаляем записи старше ttl_days"""
        cutoff = datetime.now() - timedelta(days=30)
        self.conn.execute("DELETE FROM seen_urls WHERE seen_at < ?", (cutoff,))
        self.conn.commit()
```

---

## LLM-скоринг (батч, дёшево)

```python
# processors/scorer.py
import json
from anthropic import Anthropic

client = Anthropic()

def score_posts_batch(posts: List[Dict], topic: str, batch_size: int = 30) -> List[Dict]:
    """Оцениваем посты батчами — один LLM вызов на 30 постов"""
    scored = []

    for i in range(0, len(posts), batch_size):
        batch = posts[i:i + batch_size]
        batch_data = [
            {
                "id": j,
                "title": p.get("title", "")[:100],
                "text": p.get("text", "")[:300],
                "source": p["source"],
                "engagement": p.get("score", 0)
            }
            for j, p in enumerate(batch)
        ]

        response = client.messages.create(
            model="claude-haiku-4-5",  # дешевле для scoring
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Score each item's relevance to topic '{topic}' from 1-10.
Noise = promotional, off-topic, bot-generated, duplicate claim, <50 chars.
Return ONLY JSON array: [{{"id": N, "score": N, "sentiment": "pos|neg|neu", "noise": true|false, "subtopic": "short label"}}]

ITEMS: {json.dumps(batch_data, ensure_ascii=False)}"""
            }]
        )

        try:
            scores = json.loads(response.content[0].text)
            for s in scores:
                idx = s["id"]
                if idx < len(batch):
                    batch[idx].update({
                        "relevance_score": s["score"],
                        "sentiment": s["sentiment"],
                        "is_noise": s["noise"],
                        "subtopic": s.get("subtopic", "general")
                    })
                    scored.append(batch[idx])
        except json.JSONDecodeError:
            # Если LLM вернул не JSON — добавляем без скоринга
            scored.extend(batch)

    return [p for p in scored if not p.get("is_noise") and p.get("relevance_score", 0) >= 6]
```

---

## Генератор отчётов

```python
# processors/reporter.py
from anthropic import Anthropic
from datetime import datetime

client = Anthropic()

REPORT_PROMPT = """
You are a research analyst. Generate a structured Markdown report.

TOPIC: {topic}
PERIOD: {period}
SOURCES: {source_count} items from {sources}

Report format:
## Executive Summary
(2-3 sentences: overall picture)

## Main Themes
(3-5 themes with quotes)

## Sentiment
- Overall: Positive / Negative / Mixed
- Reasons for positive: ...
- Reasons for negative: ...

## Notable Discussions
(5-7 specific posts with URLs)

## Emerging Signals
(что новое или неожиданное)

## Watch Next Week
(что мониторить дальше)

---
SOURCE DATA:
{sources_text}
"""

def generate_report(
    topic: str,
    posts: List[Dict],
    period: str = "last 7 days"
) -> str:
    # Топ-40 постов для контекста
    top_posts = sorted(posts, key=lambda x: x.get("relevance_score", 0), reverse=True)[:40]

    sources_text = "\n\n".join(
        f"[{p['source']}] {p['url']}\n{p.get('title','')}\n{p.get('text','')[:400]}"
        for p in top_posts
    )

    source_names = list(set(p["source"] for p in posts))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": REPORT_PROMPT.format(
                topic=topic,
                period=period,
                source_count=len(posts),
                sources=", ".join(source_names),
                sources_text=sources_text
            )
        }]
    )

    return response.content[0].text
```

---

## Планировщик (APScheduler)

```python
# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import yaml
import logging

logger = logging.getLogger(__name__)
scheduler = BlockingScheduler(timezone="Europe/Moscow")

def run_collection(monitor_config: dict):
    """Сбор данных для одного монитора"""
    topic_name = monitor_config["name"]
    topics = monitor_config["topics"]

    logger.info(f"Collecting: {topic_name}")
    all_posts = []

    if "reddit" in monitor_config["sources"]:
        all_posts.extend(collect_reddit(topics, monitor_config["period_hours"]))

    if "exa_web" in monitor_config["sources"]:
        all_posts.extend(collect_exa(topics, period_hours=monitor_config["period_hours"]))

    if "hacker_news" in monitor_config["sources"]:
        for topic in topics:
            all_posts.extend(collect_rss(topic, monitor_config["period_hours"]))

    # Дедуп + скоринг
    new_posts = deduplicator.filter_new(all_posts)
    scored_posts = score_posts_batch(new_posts, topic_name)

    # Сохраняем в DB
    db.save_posts(topic_name, scored_posts)

    # Алерт если что-то важное (score >= 9)
    hot_posts = [p for p in scored_posts if p.get("relevance_score", 0) >= 9]
    if hot_posts:
        send_hot_alert(topic_name, hot_posts)

    logger.info(f"Done: {topic_name} — {len(new_posts)} new, {len(scored_posts)} relevant")

def run_weekly_report(monitor_config: dict):
    """Еженедельный отчёт"""
    topic_name = monitor_config["name"]
    posts = db.get_posts_for_week(topic_name)

    if not posts:
        logger.info(f"No posts for report: {topic_name}")
        return

    report = generate_report(topic_name, posts, period="last 7 days")
    deliver_report(topic_name, report)
    db.save_report(topic_name, report)

def setup_schedules(config: dict):
    for monitor in config["monitors"]:
        # Сбор каждые N часов
        scheduler.add_job(
            run_collection,
            "interval",
            hours=monitor["period_hours"],
            args=[monitor],
            id=f"collect_{monitor['name']}"
        )

    # Еженедельный отчёт по расписанию из config
    report_schedule = config["delivery"].get("telegram", {}).get("report_schedule", "0 9 * * 1")
    h, m, dow = parse_cron(report_schedule)  # упрощённо

    for monitor in config["monitors"]:
        scheduler.add_job(
            run_weekly_report,
            CronTrigger(day_of_week=dow, hour=h, minute=m),
            args=[monitor],
            id=f"report_{monitor['name']}"
        )

if __name__ == "__main__":
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    setup_schedules(config)
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    scheduler.start()
```

---

## Установка и запуск

```bash
# 1. Зависимости
pip install praw telethon feedparser exa-py anthropic \
            apscheduler python-telegram-bot pyyaml python-dotenv

# 2. .env файл
cp .env.example .env
# Заполни:
# EXA_API_KEY=...
# ANTHROPIC_API_KEY=...
# TELEGRAM_BOT_TOKEN=...          # бот для доставки отчётов
# TELEGRAM_REPORT_CHAT_ID=...     # куда слать отчёты
# REDDIT_CLIENT_ID=...            # если используешь Reddit API
# REDDIT_CLIENT_SECRET=...
# TELEGRAM_API_ID=...             # для Telethon (user account)
# TELEGRAM_API_HASH=...           # my.telegram.org → API development tools

# 3. Инициализация Telethon сессии (один раз)
python -c "from telethon.sync import TelegramClient; TelegramClient('monitor_session', API_ID, API_HASH).start()"

# 4. Запуск
python main.py
# или как сервис:
nohup python main.py > monitor.log 2>&1 &
```

---

## Telegram-каналы: предупреждения

```
ВАЖНО для Telethon:
- Используй ОТДЕЛЬНЫЙ Telegram аккаунт (не личный!)
- Не подключай более 200-300 каналов одновременно
- Добавляй каналы постепенно (не всё сразу — бан!)
- Ошибка FloodWaitError = замедли запросы, жди указанное время
- Храни session файл в безопасном месте (это фактически доступ к аккаунту)
- Запускай на VPS, не на домашнем IP
- По ToS Telegram это серая зона — используй на свой риск
```

---

## Альтернатива без кода: готовые сервисы

| Что хочешь мониторить | Бесплатный вариант | Платный ($20-100/мес) |
|----------------------|--------------------|-----------------------|
| Reddit | F5Bot (email alerts) | Syften ($20) |
| Reddit + HN | RSS нативный feed | Brand24 ($79) |
| Telegram каналы | — | Telemetr.io Spy |
| Twitter/X | X Pro (TweetDeck) | SnitchFeed ($24) |
| Всё вместе | — | Brand24 ($79) |

---

## Связанные инструменты

- `/social-research` — разовый ресёрч по теме (без постоянного мониторинга)
- `/deploy-linux-vps` — задеплоить мониторинг на VPS (запустить 24/7)
- `/config-env-portability` — правильно хранить все API ключи в .env
- `/telegram-bot-linux` — развернуть Telegram бот для доставки отчётов на Linux
