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
| google-drive-sheets-auth | OAuth vs SA, 403 fix, scopes | `/google-drive-sheets-auth` |
| tabular-schema-evolution | Эволюция схемы таблиц | `/tabular-schema-evolution` |

## AI / OCR

| Скилл | Описание | Вызов |
|-------|----------|-------|
| ocr-structured-text | OCR с сохранением структуры | `/ocr-structured-text` |
| openai-json-extraction | Надёжный JSON из OpenAI | `/openai-json-extraction` |

## Управление задачами

| Скилл | Описание | Вызов |
|-------|----------|-------|
| daily-plan | Ежедневные планы с переносами | `/daily-plan` |
| clickup-cursor-sync | Синхронизация с ClickUp | `/clickup-cursor-sync` |
| fireflies-meetings | Транскрипты встреч | `/fireflies-meetings` |

## Исследования

| Скилл | Описание | Вызов |
|-------|----------|-------|
| research-system | Мульти-источниковый ресерч | `/research-system` |

## Утилиты

| Скилл | Описание | Вызов |
|-------|----------|-------|
| unicode-fixer | Фикс UTF-8/эмодзи кодировки | `/unicode-fixer` |

---

## Правила (авто-применяются)

| Правило | Применяется к | Описание |
|---------|---------------|----------|
| python-standards | `**/*.py` | Стандарты Python: pathlib, type hints, logging |
| vps-ssh-deployment | `**/deploy*.py` | Стандарты SSH деплоя через paramiko |
| finance-bot-vps | `**/FinanceBot/**` | FinanceBot VPS специфика |
| task-management | Всегда | ADHD-friendly система задач |
