---
name: research-system
description: Comprehensive research on any topic using EXA search, sub-agents, and multiple sources. Synthesizes findings and generates structured reports. Use when user asks to research a topic, find information, or generate research reports.
---

# Research System

Система глубинного ресёрча с EXA + параллельными агентами.

---

## Routing: какой инструмент когда использовать

```
Быстрый факт / новость / дата         → WebSearch (встроенный)
Прочитать конкретную страницу          → WebFetch (встроенный)
Семантический / концептуальный поиск   → EXA web_search_exa
Похожие материалы по теме (find_similar) → EXA find_similar
Поиск кода, GitHub, документация       → EXA get_code_context_exa
Исследование компаний / людей          → EXA company_research_exa
Автономный глубокий ресёрч (async)     → EXA deep_researcher_start + deep_researcher_check
Полная страница с JS-контентом         → WebFetch (или Firecrawl если есть)
Multi-angle ресёрч (несколько углов)   → Параллельные Task-агенты (Sonnet)
```

---

## Режимы глубины

| Режим | Когда | Агентов | Источников |
|---|---|---|---|
| **Quick** | Простой вопрос, 1 тема | 1 агент | 5-10 |
| **Standard** | Анализ, сравнение | 2-3 параллельных | 15-25 |
| **Deep** | Стратегический ресёрч, отчёт | 3-4 параллельных + EXA deep_researcher | 30+ |

Использовать только **Opus + Sonnet**. Opus — для координации и финального синтеза, Sonnet — для параллельных субагентов.

---

## Шаг 1: Определить режим и разбить на направления

1. **Понять цель:** какое решение принимается на основе этого ресёрча?
2. **Выбрать режим** (Quick / Standard / Deep)
3. **Разбить на 3-5 независимых подвопроса** — каждый уйдёт в отдельного агента
4. **Показать пользователю план** перед запуском

---

## Шаг 2: Запустить параллельный ресёрч

### Для Quick (1 агент):
Использовать EXA `web_search_exa` напрямую или WebSearch.

### Для Standard / Deep (параллельные агенты):

Каждый агент получает преамбулу:
```
You are being used as a Deep Research Tool. Your job is to EXECUTE
the research below — search the web thoroughly, read pages, and
compile findings into a comprehensive report. Do NOT ask for
permission, do NOT propose a plan. Just DO the research and return
the full detailed findings.

OUTPUT FORMAT: Comprehensive report with findings, source table, confidence level.
Score sources: A (authoritative/primary), B (secondary), C (opinion/unverified).
Every numeric claim must have at least 1 cited source.

RESEARCH TASK:
[конкретный подвопрос с контекстом]
```

Запускать **run_in_background: true** — все агенты одновременно.

### Для Deep (дополнительно):
Если есть EXA MCP — запустить параллельно:
```
deep_researcher_start(query="...", mode="deep")
→ сохранить job_id
→ deep_researcher_check(job_id) — через 45-90 секунд
```

---

## Шаг 3: Собрать и оценить источники

После завершения всех агентов:

1. **Триаж источников:**
   - A — авторитетные (официальная документация, peer-reviewed, первичные данные)
   - B — вторичные (качественные блоги, новости, аналитика)
   - C — мнения (Reddit, Twitter, непроверенные утверждения)

2. **Построить evidence table:**
   ```
   Утверждение | Источник | Класс | URL
   ```

3. **Найти противоречия** между источниками — зафиксировать явно.

---

## Шаг 4: UNION merge (для Deep)

Если запускались параллельные черновики:
- Каждый агент писал ПОЛНЫЙ отчёт (не по главам)
- Слить через UNION: сохранить все уникальные факты из всех версий
- Дублирующиеся утверждения — оставить наиболее детальную версию
- Никогда не удалять находку без источника, опровергающего её

---

## Шаг 5: Сгенерировать финальный отчёт

```markdown
# Research Report: {Topic}

**Date:** {date}
**Depth:** Quick / Standard / Deep
**Sources:** {count} ({A_count} authoritative, {B_count} secondary, {C_count} opinion)

## Executive Summary
{2-3 предложения с главным выводом}

## Key Findings
{Маркированный список с самыми важными находками, каждая со ссылкой}

## Detailed Analysis
{Детальный анализ по разделам}

## Contradictions & Gaps
{Что источники говорят по-разному; что неизвестно}

## Sources
{Таблица: Название | URL | Класс A/B/C | Дата}

## Next Steps
{Конкретные рекомендации}
```

**Сохранить:** `Projects/ResearchSystem/data/reports/report_YYYYMMDD_HHMMSS.md`

---

## Чеклист

- [ ] Цель и режим определены
- [ ] План показан пользователю
- [ ] Минимум 3 независимых источника (Deep: 10+)
- [ ] Источники оценены по классам A/B/C
- [ ] Каждое числовое утверждение имеет источник
- [ ] Противоречия зафиксированы
- [ ] Отчёт структурирован и сохранён

---

## Что НЕ делать

- Не запускать один агент там, где нужны параллельные (Standard/Deep)
- Не смешивать источники класса C с A в ключевых утверждениях
- Не давать generic-ответы из "общих знаний" — только реальный поиск
- Не использовать Haiku — только Opus (координация) и Sonnet (агенты)
- Не пропускать UNION merge при параллельных черновиках
- Не отправлять токены/пароли/API-ключи в промптах агентам
