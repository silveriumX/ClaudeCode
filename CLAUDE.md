# Claude Code Project Instructions

## Automation Preferences

- **Autonomous Mode**: Operate with maximum autonomy
- **No confirmation needed** for:
  - Creating/editing/deleting files
  - Installing dependencies (npm, pip, etc.)
  - Running tests
  - Running build commands
  - Git operations (add, commit) - but ASK before push
  - Creating directories and project structure

- **Ask only for**:
  - Git push operations
  - Deleting entire directories
  - Major architectural changes
  - Changes to production configurations

## Development Guidelines

- Use modern best practices
- Write clean, maintainable code
- Include error handling
- Add comments where logic isn't obvious
- Run tests after changes
- See @.claude/rules/python-standards.md for Python-specific standards

## Preferred Stack

- **Python 3.10+** — основной язык (боты, скрипты, автоматизация)
- **paramiko** — SSH подключения к Linux VPS
- **WinRM** (PowerShell Remoting) — подключения к Windows VPS
- **python-telegram-bot** — Telegram боты
- **gspread + google-auth** — Google Sheets интеграция
- **google-api-python-client** — Google Drive, YouTube APIs
- **python-dotenv** — конфигурация через .env
- **requests** — HTTP клиент
- **Node.js / TypeScript** — Google Apps Script, утилиты

## Skills Catalog

Доступные скиллы (вызов через `/skill-name`):

### Деплой и серверы
- `/deploy-linux-vps` — Деплой на Linux VPS через SSH/SFTP (paramiko, nohup, pkill)
- `/telegram-bot-linux` — Telegram-бот на Linux (fix Conflict, deleteWebhook, 25-30s wait)
- `/windows-vps-deploy` — Деплой на Windows VPS через WinRM (DETACHED_PROCESS, без BOM)

### Конфигурация
- `/config-env-portability` — Все секреты в .env, чеклист переноса на новый сервер

### Google API
- `/google-drive-sheets-auth` — OAuth vs Service Account, 403 quota fix, scopes
- `/tabular-schema-evolution` — Эволюция схемы таблиц (архивация + новый лист)

### AI / OCR
- `/ocr-structured-text` — Vision API OCR с сохранением структуры документа
- `/openai-json-extraction` — Надёжный JSON из OpenAI (chat models, temperature, response_format)

### Управление задачами
- `/daily-plan` — Ежедневные планы с переносами [→1]/[→2]/[→3] (ADHD-friendly)
- `/clickup-cursor-sync` — Двусторонняя синхронизация с ClickUp
- `/fireflies-meetings` — Транскрипты встреч, саммари, action items

### Исследования
- `/research-system` — Мульти-источниковый ресерч (EXA, Firecrawl) со структурированными отчётами

### Утилиты
- `/unicode-fixer` — Фикс UTF-8/эмодзи кодировки (Python, PowerShell, Windows)

Полный каталог: @.claude/skills/README.md

## Rules (авто-применяются)

- **python-standards** — Стандарты Python кода (pathlib, type hints, logging) → `**/*.py`
- **vps-ssh-deployment** — Стандарты SSH деплоя через paramiko → `**/deploy*.py`
- **finance-bot-vps** — FinanceBot VPS специфика → `**/FinanceBot/**`
- **task-management** — ADHD-friendly система задач (всегда активно)
- **research-guide** — Правила проведения веб-ресёрчей (при запросах на ресёрч)
