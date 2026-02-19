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
| google-drive-oauth-token | Получение refresh_token для Drive (403 quota, invalid_grant) | `/google-drive-oauth-token` |
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

## Финансовая система (AccountingBot)

| Скилл | Описание | Вызов |
|-------|----------|-------|
| bank-statement-parser | Парсинг банковских выписок → нормализованные транзакции (Модульбанк, расширяемый) | `/bank-statement-parser` |
| transaction-categorizer | Категоризация транзакций: ИНН-правила → паттерны → GPT + обучение | `/transaction-categorizer` |
| financial-journal-schema | Схема единого журнала транзакций в Google Sheets (все банки + FinanceBot) | `/financial-journal-schema` |
| bank-import-bot | AccountingBot: загрузка выписок через Telegram → Sheets с AI разметкой | `/bank-import-bot` |
| financial-dashboard | Dashboard: P&L, Cash Flow, расходы по категориям в Google Sheets | `/financial-dashboard` |

## Утилиты

| Скилл | Описание | Вызов |
|-------|----------|-------|
| unicode-fixer | Фикс UTF-8/эмодзи кодировки | `/unicode-fixer` |
| pdf-tools | Операции с PDF (извлечение, OCR, генерация) | `/pdf-tools` |

---

## Правила (авто-применяются)

| Правило | Применяется к | Описание |
|---------|---------------|----------|
| python-standards | `**/*.py` | Стандарты Python: pathlib, type hints, logging |
| pdf-processing | При работе с PDF | Выбор библиотек, OCR, генерация PDF |
| vps-ssh-deployment | `**/deploy*.py` | Стандарты SSH деплоя через paramiko |
| finance-bot-vps | `**/FinanceBot/**` | FinanceBot VPS специфика |
| task-management | Всегда | ADHD-friendly система задач |
| research-guide | При запросах на ресёрч | Правила проведения веб-ресёрчей |
