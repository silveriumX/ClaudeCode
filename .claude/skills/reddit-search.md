# Reddit Search

> Семантический поиск по Reddit через Exa MCP с фильтрами по дате и субреддиту.
> Работает в главной сессии — не требует делегирования sub-агентам.

---

## Когда использовать

- "Что говорят на Reddit о X?"
- "Найди обсуждения на Reddit по теме Y"
- "Какие боли у людей в r/[subreddit]?"
- "Последние обсуждения Claude Code / Cursor / [тема] на Reddit"
- "/reddit-search"

---

## Примеры вызова

```
/reddit-search topic="Claude Code vs Cursor" days=30
/reddit-search topic="Rust async" subreddit="r/rust" days=14
/reddit-search topic="AI coding tools pain points"
```

---

## Алгоритм (в главной сессии через Exa MCP)

### 1. Основной поиск

Использовать `mcp__exa__web_search_exa` напрямую с `include_domains=["reddit.com"]`.

**Параметры:**
- `query` — тема + контекст (не просто ключевое слово, а семантический запрос)
- `include_domains: ["reddit.com"]` — только Reddit
- `start_published_date` — дата среза (ISO format)
- `num_results` — 20-30 для обзора, 50+ для глубокого анализа
- `livecrawl: "preferred"` — свежие данные

**Примеры запросов:**
```
"[тема] community discussion user experience 2025"
"[тема] honest review problems issues"
"[тема] vs alternatives comparison reddit"
"[тема] pain points frustrations what went wrong"
"[тема] success story how it worked out"
```

### 2. Уточняющий поиск (если нужно)

Запускать параллельно несколько поисков с разными углами:

```
Поиск 1: "[тема] positive experience recommend"
Поиск 2: "[тема] problems issues criticism"
Поиск 3: "[тема] beginner guide how to start"
Поиск 4: "site:reddit.com/r/[subreddit] [тема]"  ← для конкретного субреддита
```

### 3. Синтез результатов

После получения результатов:
- Группировать по сентименту (позитив / негатив / нейтраль)
- Выделять конкретные субреддиты с наибольшей активностью
- Находить паттерны в жалобах и похвалах
- Цитировать конкретные треды с URL

---

## Формат отчёта

```markdown
## Reddit: [тема] — [период]

**Источников найдено:** N постов из M субреддитов

### Топ субреддиты
- r/[name] — [N постов], [сентимент]

### Основные темы обсуждений
1. [тема] — [краткое описание с цитатой]
2. ...

### Сентимент
- Позитив: [что хвалят]
- Негатив: [что критикуют]
- Нейтрально: [факты, вопросы]

### Топ треды
- [заголовок](URL) — [суть в одной строке]

### Инсайты
[Что неожиданного, что стоит запомнить]
```

---

## Полезные домены для Reddit

```
reddit.com              — основной сайт
old.reddit.com          — старый интерфейс (лучше индексируется)
```

**Конкретные субреддиты для tech/AI:**
- `r/MachineLearning`, `r/artificial`, `r/LocalLLaMA`
- `r/programming`, `r/Python`, `r/learnprogramming`
- `r/cursor`, `r/ClaudeAI`, `r/ChatGPT`
- `r/startups`, `r/entrepreneur`, `r/SideProject`

---

## Ограничения

- Exa индексирует публичные посты Reddit — приватные субреддиты недоступны
- Очень свежие посты (< 24 часов) могут не индексироваться — используй `livecrawl: "preferred"`
- Для исторических данных (> 1 года) — PullPush.io API лучше
- Максимальная глубина: ~1000 результатов на запрос через Exa

---

## Связанные скиллы

- `/hn-search` — то же самое для Hacker News
- `/twitter-search` — Twitter/X через Exa
- `/social-research` — комплексный поиск по всем платформам
- `/monitor-pipeline` — автоматический мониторинг с алертами
