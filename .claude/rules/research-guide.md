# Research Guide

> Правила проведения веб-ресёрчей. Применяется при запросах: "проведи ресёрч", "узнай как делается X", "исследуй", "найди информацию", "дип-ресёрч".

---

## Принципы

1. **Максимум контекста.** Перед формулировкой промпта — собрать контекст из файлов проекта (vault, memory, конфиги, текущие задачи). Чем больше реального контекста — тем лучше результат.

2. **Живые промпты.** Писать как умному человеку. Формальные структурированные запросы дают формальные generic-ответы. Живой контекст + живой вопрос → интересные находки.

3. **Если непонятно намерение — спросить.** Если после сбора контекста не до конца ясна мета-цель, лучше уточнить у пользователя, чем отправлять размытый запрос.

4. **Показывать промпты.** При КАЖДОМ запуске ресёрча — показать пользователю полный промпт, который отправляется в инструмент. Без сокращений.

---

## Дефолтный фрейм: "как делается X"

Когда пользователь просит узнать, как что-то делается или решается:

> Искать в первую очередь **кейсы живых пользователей** — их истории, как именно они решали подобную задачу, что сработало, что не сработало, плюсы, минусы, подводные камни. Что реально сработало на практике и что важно учесть.

Этот фрейм применяется при: "проведи ресёрч", "проведи дип-ресёрч", "узнай как делается X" — любой запрос на глубокое исследование, а не бытовой вопрос.

---

## Структура промпта для ресёрча

Каждый промпт строить по структуре:

- **Намерение:** ради чего делаем ресёрч, какое решение принимаем
- **Желаемый результат:** что конкретно хотим получить
- **Контекст:** наша ситуация, что уже есть, что пробовали (без чувствительных данных)
- **Почему важно:** чтобы агент мог копнуть глубже, увидев связи

---

## Алгоритм выполнения

### 1. Сбор контекста (перед ресёрчем)

```
- Прочитать релевантные файлы проекта
- Посмотреть текущие задачи (если связано)
- Понять, какое решение будет приниматься на основе ресёрча
```

### 2. Формулировка промпта

```
- Составить промпт по структуре выше
- Показать пользователю полный промпт
- Дождаться подтверждения (или скорректировать)
```

### 3. Выполнение

```
- Запустить ресёрч подходящим инструментом
- Для глубоких ресёрчей — параллельные Task-агенты с разными запросами
- Для быстрых вопросов — WebSearch + WebFetch
```

### 4. Результат

```
- Структурированный отчёт с findings
- Конкретные примеры, цитаты, ссылки
- Практические выводы и рекомендации
```

---

## Инструменты

### ПРИОРИТЕТ: Exa MCP > WebSearch

Если доступен Exa MCP (`mcp__exa__web_search_exa`) — **использовать его вместо WebSearch** для всех ресёрчей. Exa даёт семантический поиск с фильтрами по домену и дате, что критически важно для качества.

| Инструмент | Приоритет | Когда использовать |
|------------|-----------|-------------------|
| `mcp__exa__web_search_exa` | **1 (предпочтительный)** | Любой ресёрч — семантический поиск с domain filter и date filter |
| `mcp__exa__get_code_context_exa` | **1** | Поиск кода, API документации, примеров |
| `WebSearch` | 2 (fallback) | Только если Exa недоступен |
| `WebFetch` | 2 | Прочитать конкретную страницу по URL |
| `/social-research` | 1 | Ресёрч в Reddit/HN/Telegram/Twitter через Exa MCP |
| Task-агенты (parallel) | 3 | Только если нужно несколько независимых глубоких направлений |

### Выбор инструмента:

- **Простой вопрос** (цена, версия, дата) → `mcp__exa__web_search_exa` или `WebSearch`
- **Изучить страницу** (документация, статья) → `WebFetch`
- **Ресёрч в соцсетях** (Reddit, HN, Twitter, Telegram) → `mcp__exa__web_search_exa` с параметром `include_domains` + `/social-research` скилл
- **Глубокий ресёрч в главной сессии** → Exa MCP напрямую, параллельные вызовы по разным аспектам
- **Multi-angle ресёрч** (несколько тяжёлых направлений) → параллельные Task-агенты (они используют WebSearch, Exa им недоступен)

### Как использовать Exa MCP для соцсетей:

```
# Reddit
mcp__exa__web_search_exa(
  query="[тема] community discussion experience",
  include_domains=["reddit.com"],
  start_published_date="2025-01-01"
)

# Hacker News
mcp__exa__web_search_exa(
  query="[тема]",
  include_domains=["news.ycombinator.com"]
)

# Twitter/X
mcp__exa__web_search_exa(
  query="[тема]",
  include_domains=["twitter.com", "x.com"]
)
```

### ВАЖНО: Task-агенты НЕ используют Exa MCP

MCP-инструменты доступны только в главной сессии. Когда запускаются Task sub-агенты — они используют WebSearch. Поэтому для ресёрчей с акцентом на соцсети предпочтительнее работать в главной сессии через Exa MCP напрямую.

---

## Формат Task-агента для ресёрча

### Sub-агенты лучше для параллельного ресёрча

Sub-агенты (Task tool) — лучший выбор когда нужно исследовать несколько платформ параллельно. Они не засоряют основной контекст и работают одновременно. Единственная особенность: им недоступен MCP, но у них есть Bash — через него они вызывают Exa и TGStat напрямую.

### Инструменты поиска для sub-агентов

Sub-агент использует Bash для вызова скриптов из папки `scripts/`:

```bash
# Поиск по Reddit через Exa API
python scripts/exa_search.py "Claude Code discussion" --domains reddit.com --days 30 --num 20

# Поиск по Hacker News
python scripts/exa_search.py "Claude Code" --domains news.ycombinator.com --days 14

# Поиск по Twitter/X
python scripts/exa_search.py "topic opinion" --domains twitter.com,x.com --days 7 --livecrawl

# Поиск по Telegram (нужен TGSTAT_TOKEN в .env)
python scripts/tgstat_search.py "тема" --mode posts --days 14
python scripts/tgstat_search.py "тема" --mode channels --lang ru

# Поиск по нескольким доменам сразу
python scripts/exa_search.py "topic" --domains reddit.com,news.ycombinator.com,bsky.app --days 30
```

### Преамбула для Task-агента (ресёрч в соцсетях)

```
You are being used as a Deep Research Tool with direct access to Exa search API.

SEARCH TOOLS AVAILABLE (use via Bash):
- Exa semantic search: python scripts/exa_search.py "query" --domains DOMAIN --days N --num 20
  Domains: reddit.com | news.ycombinator.com | twitter.com | t.me | bsky.app
- TGStat (Telegram): python scripts/tgstat_search.py "query" --mode posts --days N
- WebFetch: read any URL fully
- WebSearch: fallback if scripts fail

YOUR JOB: EXECUTE the research — run multiple searches, read results, compile findings.
Do NOT ask for permission. Do NOT propose a plan. Just DO the research and return findings.

OUTPUT FORMAT: Comprehensive report with specific quotes, URLs, and concrete examples.

RESEARCH TASK:
[промпт с контекстом]
```

### Преамбула для Task-агента (общий веб-ресёрч)

```
You are being used as a Deep Research Tool. Your job is to EXECUTE
the research below — search the web thoroughly, read pages, and
compile findings into a comprehensive report. Do NOT ask for
permission, do NOT propose a plan. Just DO the research and return
the full detailed findings.

SEARCH: Use Exa when available: python scripts/exa_search.py "query" --num 20
Fallback: WebSearch + WebFetch

OUTPUT FORMAT: Return a comprehensive research report with all
findings, organized by topic. Include specific quotes, links,
and concrete examples.

RESEARCH TASK:
[промпт с контекстом]
```

---

## Запрещено

- Отправлять размытые запросы без контекста
- Давать generic-ответы из "общих знаний" вместо реального поиска
- Скрывать промпты от пользователя
- Игнорировать фрейм "кейсы живых пользователей" при глубоких ресёрчах
- Отправлять чувствительные данные (токены, пароли, API-ключи) в промптах
