# Social Research

> On-demand глубокий ресёрч по теме в социальных сетях: Reddit, Hacker News, Twitter/X, Telegram, веб.
> Генерирует структурированный Markdown-отчёт с реальными данными.

---

## Когда использовать

- "Что люди говорят о X на Reddit?"
- "Проведи ресёрч по теме Y в соцсетях"
- "Какой сентимент по теме Z в Twitter?"
- "Найди топ обсуждения по теме за последние 7 дней"
- "/social-research"

---

## Примеры вызова

```
/social-research topic="Claude Code vs Cursor" sources="reddit,hn" period="30d"
/social-research topic="AI coding assistants" sources="all" period="7d"
/social-research topic="Rust vs Go" sources="reddit,twitter"
```

---

## Доступные источники

| Источник | Инструмент | Что нужно |
|----------|------------|-----------|
| Reddit | Exa с `include_domains=["reddit.com"]` или Reddit MCP | Exa API key |
| Hacker News | Exa с `include_domains=["news.ycombinator.com"]` | Exa API key |
| Twitter/X | Exa с `include_domains=["twitter.com","x.com"]` | Exa API key |
| Telegram | TGStat API keyword search | TGStat API key ($25+/mo) |
| Веб (любой) | Exa semantic search + Firecrawl | Exa API key |
| Perplexity | Sonar API (Reddit Social mode) | Perplexity API key |

---

## Алгоритм выполнения

### 1. Сбор данных из источников

**Exa (основной инструмент — умеет фильтровать по домену + по дате):**

```python
from exa_py import Exa
from datetime import datetime, timedelta

exa = Exa(api_key=os.getenv("EXA_API_KEY"))

# Reddit
reddit_results = exa.search_and_contents(
    f"{topic} discussion experience",
    include_domains=["reddit.com"],
    start_published_date=(datetime.now() - timedelta(days=period_days)).isoformat(),
    num_results=30,
    contents={"highlights": True}  # только релевантные куски, экономит токены
)

# Hacker News
hn_results = exa.search_and_contents(
    topic,
    include_domains=["news.ycombinator.com"],
    start_published_date=...,
    num_results=15,
    contents={"highlights": True}
)

# Twitter/X (частичное покрытие)
twitter_results = exa.search_and_contents(
    topic,
    include_domains=["twitter.com", "x.com"],
    start_published_date=...,
    num_results=20,
    contents={"highlights": True}
)
```

**Perplexity Sonar (для Reddit social mode):**

```python
import requests

response = requests.post(
    "https://api.perplexity.ai/chat/completions",
    headers={"Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"},
    json={
        "model": "sonar",
        "messages": [{
            "role": "user",
            "content": f"What are people discussing about '{topic}' on Reddit in the past {period}? What are the main opinions, pain points, and praises? Give specific examples with subreddits."
        }],
        "return_citations": True,
        "search_recency_filter": "week"  # или month
    }
)
```

**TGStat API (для Telegram):**

```python
import requests

# Поиск постов по ключевому слову
response = requests.get(
    "https://api.tgstat.ru/posts/search",
    params={
        "token": os.getenv("TGSTAT_TOKEN"),
        "q": topic,
        "limit": 50,
        "startDate": int((datetime.now() - timedelta(days=period_days)).timestamp()),
    }
)
posts = response.json().get("response", {}).get("items", [])
```

---

### 2. Дедупликация и фильтрация

```python
import hashlib

seen_urls = set()
filtered_results = []

for result in all_results:
    url_hash = hashlib.md5(result.url.encode()).hexdigest()
    if url_hash not in seen_urls:
        seen_urls.add(url_hash)
        filtered_results.append(result)

# Минимальный фильтр качества:
# - Убираем страницы длиннее 50 символов в тексте (не пустые)
# - Убираем очевидный спам по ключевым словам
```

---

### 3. LLM-оценка релевантности (батч, экономит токены)

```python
import json
from anthropic import Anthropic

client = Anthropic()

# Оцениваем 20-30 источников за один вызов
batch_texts = [
    {"id": i, "url": r.url, "text": (r.highlights or [r.text[:300]])[0]}
    for i, r in enumerate(filtered_results)
]

response = client.messages.create(
    model="claude-haiku-4-5",  # дешевле для scoring
    max_tokens=2000,
    messages=[{
        "role": "user",
        "content": f"""Score each source's relevance to topic '{topic}' from 1-10.
Return JSON array only: [{{"id": N, "score": N, "sentiment": "pos/neg/neu", "noise": bool}}]

SOURCES: {json.dumps(batch_texts)}"""
    }]
)

scores = json.loads(response.content[0].text)
# Оставляем только score >= 6
relevant = [r for r, s in zip(filtered_results, scores) if s["score"] >= 6 and not s["noise"]]
```

---

### 4. Генерация структурированного отчёта

```python
# Промпт для финального отчёта (claude-sonnet-4-6 — лучше для синтеза)
report_prompt = f"""
You are a research analyst. Synthesize the following social media discussions into a structured report.

TOPIC: {topic}
PERIOD: last {period}
SOURCES: {len(relevant)} posts from {", ".join(sources)}

Generate a report in Markdown format:

## Executive Summary
(2-3 sentences: what's the overall picture)

## Main Themes
(3-5 themes with post count estimate and representative quotes)

## Sentiment Analysis
- Overall: Positive / Negative / Mixed
- Key reasons for positive sentiment
- Key reasons for negative sentiment / criticism

## Key Voices & Communities
(Top subreddits, accounts, or communities driving the conversation)

## Notable Posts / Discussions
(5-7 specific posts worth reading, with URLs)

## Emerging Signals
(What's new or surprising compared to the expected narrative)

## What to Watch Next
(Follow-up topics or questions worth monitoring)

---

SOURCE MATERIAL:
{chr(10).join(f"[{r.url}] {(r.highlights or [''])[0][:400]}" for r in relevant[:40])}
"""

report_response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4000,
    messages=[{"role": "user", "content": report_prompt}]
)

report = report_response.content[0].text
```

---

## Зависимости

```bash
pip install exa-py anthropic requests python-dotenv
```

### MCP альтернативы (если настроены)

Если в Claude Desktop настроены MCP серверы — можно использовать напрямую без кода:

**Reddit MCP Buddy** (в официальном Anthropic Directory):
```json
{
  "mcpServers": {
    "reddit-mcp-buddy": {
      "command": "npx",
      "args": ["-y", "reddit-mcp-buddy"]
    }
  }
}
```

**Exa MCP:**
```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": {"EXA_API_KEY": "your_key"}
    }
  }
}
```

**Telegram channel explorer MCP** (для Telegram):
```
pip install kfastov/telegram-channel-explorer
```

---

## Быстрый старт (минимальный сетап)

Без платных API, только Exa free tier (1000 запросов/месяц):

```python
# quick_social_research.py
import os
from exa_py import Exa
from anthropic import Anthropic
from datetime import datetime, timedelta

def research_topic(topic: str, days: int = 14) -> str:
    exa = Exa(api_key=os.getenv("EXA_API_KEY"))
    client = Anthropic()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    # Параллельный поиск по источникам
    all_results = []
    for domain in ["reddit.com", "news.ycombinator.com"]:
        results = exa.search_and_contents(
            topic,
            include_domains=[domain],
            start_published_date=since,
            num_results=20,
            contents={"highlights": True}
        )
        all_results.extend(results.results)

    # Синтез отчёта
    sources_text = "\n".join(
        f"[{r.url}]\n{(r.highlights or [''])[0][:400]}"
        for r in all_results
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"Research report on '{topic}' based on these sources:\n\n{sources_text}\n\nGenerate structured Markdown report with: summary, themes, sentiment, notable posts."
        }]
    )

    return response.content[0].text

if __name__ == "__main__":
    print(research_topic("Claude Code vs Cursor 2025", days=30))
```

---

## Таблица выбора инструмента

| Задача | Инструмент | Цена |
|--------|------------|------|
| Быстрый ресёрч Reddit + HN | Exa `include_domains` | $0 (free tier) |
| Синтез "что говорят в Reddit" | Perplexity Sonar | ~$0.001/запрос |
| Поиск по всем Telegram-каналам | TGStat API | $25/мес |
| Мониторинг Telegram real-time | Telemetr.io "Spy" | платно |
| Scraping конкретных страниц | Firecrawl Claude plugin | free tier |
| Twitter/X данные без $5K/мес | SociaVault API | ~$29/мес |

---

## Важные ограничения (2026)

- **Twitter/X официальный API**: Free tier = только запись, чтение = $100/мес (10K твитов)
- **Reddit API**: теперь требует pre-approval + $0.24/1000 коммерческих запросов
- **Telegram Bot API**: не может читать каналы без членства
- **Telegram MTProto**: нужен user account (не бот) — серая зона ToS
- **Pushshift мёртв**: замена — pullpush.io (100 результатов за запрос)
- **GummySearch закрылся**: ноябрь 2025; лучшие замены — Syften ($20/мес), Brand24 ($79/мес)

---

## Связанные инструменты

- `/research-system` — общий ресёрч через EXA без фокуса на соцсети
- `/monitor-pipeline` — настройка автоматического мониторинга (непрерывный)
- `/openai-json-extraction` — если нужна надёжная JSON-структура из LLM ответа
