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

## Context Management

- IMPORTANT: When compacting, always preserve the full list of modified files and any test commands
- Use `/clear` between unrelated tasks
- For multi-session features, create HANDOFF.md before ending session (use `/handoff` skill)

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
- **PDF Processing** — pdfplumber, pypdf, pytesseract, pdf2image, reportlab, weasyprint

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
- `/google-drive-oauth-token` — Получение refresh_token для Drive (403 storageQuotaExceeded, invalid_grant)
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
- `/pdf-tools` — Операции с PDF (извлечение текста, объединение, OCR, генерация)

Полный каталог: @.claude/skills/README.md

## Global Components (~/.claude/)

### Agents (субагенты, авто-делегирование)
- **planner** — Декомпозиция фич в пошаговые планы с файлами и рисками
- **architect** — Системный дизайн, компоненты, data flow
- **code-reviewer** — Ревью кода по severity (CRITICAL/HIGH/MEDIUM/LOW)
- **python-reviewer** — Python-специфичный ревью (ruff, mypy, black, bandit)
- **security-reviewer** — OWASP Top 10, секреты, авторизация

### Global Skills (~/.claude/skills/)
- **handoff** — Создание HANDOFF.md для передачи контекста между сессиями
- **review-claudemd** — Аудит CLAUDE.md по последним 15-20 разговорам
- **gha** — Диагностика GitHub Actions failures
- **python-patterns** — Python best practices и anti-patterns
- **python-testing** — pytest, TDD, coverage
- **deployment-patterns** — Rolling/blue-green/canary деплой
- **docker-patterns** — Контейнеризация, multi-stage builds
- **security-scan** — AgentShield аудит конфигурации
- **continuous-learning-v2** — Автоматическое обучение из сессий

### Global Commands (~/.claude/commands/)
- `/plan` — Планирование через planner-агента
- `/code-review` — Ревью через code-reviewer
- `/python-review` — Python ревью (ruff+mypy+black+bandit)
- `/build-fix` — Авто-фикс build failures
- `/orchestrate` — Цепочка агентов (planner→tdd→reviewer→security)
- `/smart-debug` — Умный дебаг: quick fix / proper fix / prevention
- `/security-scan` — OWASP + dependency audit
- `/full-review` — 6-перспективный code review
- `/smart-fix` — Динамический выбор агента по типу проблемы
- `/context-save` / `/context-restore` — Сохранение состояния между сессиями
- `/deploy-checklist` — Pre-flight checks для деплоя
- `/deps-audit` — Аудит зависимостей (security + license)
- `/config-validate` — Валидация env variables и конфигов

## Rules (авто-применяются)

- **python-standards** — Стандарты Python кода (pathlib, type hints, logging) → `**/*.py`
- **pdf-processing** — Стандарты работы с PDF (выбор библиотек, OCR, генерация) → при работе с PDF
- **vps-ssh-deployment** — Стандарты SSH деплоя через paramiko → `**/deploy*.py`
- **finance-bot-vps** — FinanceBot VPS специфика → `**/FinanceBot/**`
- **task-management** — ADHD-friendly система задач (всегда активно)
- **research-guide** — Правила проведения веб-ресёрчей (при запросах на ресёрч)
