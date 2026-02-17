# Контексты AI-first воркспейса

Папка с профилями контекста для переключения по фразе: **«Use X context»** / **«Контекст: X»**.

## Доступные контексты

| Файл | Команда | Назначение |
|------|--------|------------|
| `tasks.md` | Use **tasks** context | Задачи, планы на день, переносы, АКТУАЛЬНЫЕ_ЗАДАЧИ, ClickUp |
| `financebot.md` | Use **financebot** context | FinanceBot, VPS, деплой, Google Sheets |
| `documentation.md` | Use **documentation** context | Документация, API, Cursor, canonical/REF |
| `projects.md` | Use **projects** context | Projects/, боты, общий деплой |
| `scripts.md` | Use **scripts** context | Scripts/, ProxyMA, Hub, утилиты |

Сброс: **«Use general context»** или **«Контекст: general»** — только общие правила.

## Как переключать

В чате Cursor написать, например:
- `Use tasks context`
- `Контекст: financebot`
- `Переключись на контекст documentation`

Правило переключения: `.cursor/rules/ai-first-context-switching.mdc`.
