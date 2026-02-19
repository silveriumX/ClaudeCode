# Twitter Search

> Поиск обсуждений в Twitter/X через Exa MCP с domain filter.
> Работает без официального X API ($100+/мес) — через семантическую индексацию Exa.

---

## Когда использовать

- "Что пишут в Twitter о X?"
- "Найди твиты про [тема]"
- "Какой сентимент по теме Y в X?"
- "Кто из известных людей высказывался о Z?"
- "/twitter-search"

---

## Важные ограничения (реальность)

Twitter/X **ограничивает** индексацию своего контента. Exa покрывает X частично:
- ✅ Твиты публичных аккаунтов (обычно доступны)
- ✅ Вирусные и широко расшаренные твиты
- ⚠️ Свежие твиты (< 1-2 часов) — могут не проиндексироваться
- ❌ Твиты из приватных аккаунтов
- ❌ Полные треды с ответами

**Альтернатива для лучшего охвата:** SociaVault API ($29/мес) или Xpoz.ai (100K/мес бесплатно).

---

## Алгоритм (через Exa MCP)

### Основной поиск

```
mcp__exa__web_search_exa(
  query="[тема] opinion thoughts 2025",
  include_domains=["twitter.com", "x.com"],
  start_published_date="2025-01-01",
  livecrawl="preferred"
)
```

### Поиск конкретных типов контента

```
# Мнения и дискуссии
query="[тема] thread discussion"

# Критика
query="[тема] bad problems issue"

# Позитив / хайп
query="[тема] amazing launch released"

# Конкретный аккаунт
query="from:[username] [тема]"

# Нативный X search (через WebFetch)
"https://x.com/search?q=[тема]&f=live"
```

### Дополнение через Bluesky (если тема tech/academic)

Bluesky **полностью открытый** API — там часто больше качественных обсуждений в tech-среде:

```
mcp__exa__web_search_exa(
  query="[тема]",
  include_domains=["bsky.app"]
)
```

---

## Формат отчёта

```markdown
## Twitter/X: [тема] — [период]

**Охват:** частичный (Exa индексирует ~40-60% публичных твитов)

### Ключевые голоса
- @[username] — [суть позиции]

### Сентимент
- Позитив: [что хвалят]
- Критика: [что критикуют]

### Топ твиты/треды
- [текст](URL)

### Пробел: для полного охвата
→ Xpoz.ai (бесплатно: 100K результатов/мес)
→ X Pro (TweetDeck) для ручного мониторинга
```

---

## Когда Exa не справляется

Если по запросу мало результатов из Twitter — использовать:

1. **Xpoz.ai** — `mcp__exa__web_search_exa` с `include_domains=["xpoz.ai"]` → там агрегированные данные
2. **WebFetch** на `https://nitter.privacydev.net/search?q=[тема]` — если инстанс жив
3. **Perplexity Sonar** через WebFetch — "What's being said on X about [тема]?"

---

## Связанные скиллы

- `/reddit-search` — Reddit через Exa
- `/hn-search` — Hacker News через Exa
- `/social-research` — комплексный поиск по всем платформам
