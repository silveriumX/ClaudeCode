# Skills Catalog / Каталог скиллов

Доступные скиллы для Claude Code. Вызывай через `/skill-name` или опиши задачу — Claude подберёт скилл автоматически.

---

## Деплой и серверы

| Скилл | Описание | Вызов |
|-------|----------|-------|
| deploy-linux-vps | Деплой на Linux VPS через SSH/SFTP | `/deploy-linux-vps` |
| telegram-bot-linux | Telegram-бот на Linux (Conflict fix) | `/telegram-bot-linux` |
| windows-vps-deploy | Деплой на Windows VPS через WinRM | `/windows-vps-deploy` |

## Конфигурация

| Скилл | Описание | Вызов |
|-------|----------|-------|
| config-env-portability | Секреты в .env, чеклист переноса | `/config-env-portability` |

## Google API

| Скилл | Описание | Вызов |
|-------|----------|-------|
| google-drive-sheets-auth | OAuth vs SA, 403 fix, scopes → если выбрал OAuth, см. `/google-drive-oauth-token` | `/google-drive-sheets-auth` |
| google-drive-oauth-token | Получение refresh_token для Drive (403 quota, invalid_grant) | `/google-drive-oauth-token` |
| tabular-schema-evolution | Эволюция схемы таблиц (архивация + новый лист) | `/tabular-schema-evolution` |

## AI / OCR

| Скилл | Описание | Вызов |
|-------|----------|-------|
| ocr-structured-text | OCR с сохранением структуры (Vision API) | `/ocr-structured-text` |
| openai-json-extraction | Надёжный JSON из OpenAI | `/openai-json-extraction` |

## Управление задачами

| Скилл | Описание | Вызов |
|-------|----------|-------|
| daily-plan | Ежедневные планы с переносами [→1]/[→2]/[→3] | `/daily-plan` |
| clickup-cursor-sync | Синхронизация с ClickUp | `/clickup-cursor-sync` |
| fireflies-meetings | Транскрипты встреч, саммари, action items | `/fireflies-meetings` |

## Исследования

| Скилл | Описание | Вызов |
|-------|----------|-------|
| research-system | Глубокий мульти-источниковый ресёрч (EXA) | `/research-system` |
| social-research | Ресёрч по соцсетям: Reddit, HN, Twitter, Telegram через Exa MCP | `/social-research` |

## Разработка (процесс и инфраструктура)

| Скилл | Описание | Вызов |
|-------|----------|-------|
| python-project-init | Bootstrap нового Python проекта: venv, tasks.py, Makefile, pytest, conftest.py | `/python-project-init` |
| handoff | Создание HANDOFF.md для передачи контекста между сессиями | `/handoff` |

## Визуализация

| Скилл | Описание | Вызов |
|-------|----------|-------|
| excalidraw-diagram | Диаграммы в Excalidraw: архитектура, схемы, флоу, майндмапы | `/excalidraw-diagram` |

## Утилиты

| Скилл | Описание | Вызов |
|-------|----------|-------|
| unicode-fixer | Фикс UTF-8/эмодзи кодировки (Python, PowerShell, Windows) | `/unicode-fixer` |
| pdf-tools | Операции с PDF (извлечение текста, объединение, OCR, генерация) | `/pdf-tools` |

---

## Правила (авто-применяются без вызова)

| Правило | Применяется к | Что делает |
|---------|---------------|------------|
| python-standards | `**/*.py` | Стандарты Python: pathlib, type hints, logging, **contract-first** |
| pdf-processing | При работе с PDF | Выбор библиотек, OCR, генерация PDF |
| vps-ssh-deployment | `**/deploy*.py` | Стандарты SSH деплоя через paramiko |
| finance-bot-vps | `**/FinanceBot/**` | FinanceBot VPS специфика |
| telegram-message-safety | `**/handlers/*.py`, `**/*bot*.py` | parse_mode, try/except scope, порядок уведомлений |
| task-management | Всегда | ADHD-friendly система задач |
| research-guide | При запросах на ресёрч | Правила проведения веб-ресёрчей |

> Contract-first (Side effects / Invariants docstring) — часть правила `python-standards`,
> применяется автоматически ко всем `.py` файлам.

---

## Проектные скиллы (не глобальные)

Скиллы конкретных проектов живут в `CLAUDE.md` соответствующего проекта:

- **Система аккаунтов (AccountingBot):** `bank-statement-parser`, `transaction-categorizer`,
  `financial-journal-schema`, `bank-import-bot`, `financial-dashboard`
