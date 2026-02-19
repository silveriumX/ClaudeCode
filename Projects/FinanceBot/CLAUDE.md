# FinanceBot

Корпоративный Telegram-бот для управления финансовыми заявками с Google Sheets как БД.

## Деплой и управление VPS

Креды VPS: `.env` → VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
Путь на сервере: `.env` → VPS_REMOTE_DIR
Сервис: systemd `finance_bot`

### Единственный инструмент: `vps_connect.py`

```bash
python vps_connect.py status       # systemd статус, RAM, диск
python vps_connect.py logs [N]     # journalctl логи
python vps_connect.py errors [N]   # только ошибки
python vps_connect.py restart      # systemctl restart
python vps_connect.py deploy       # загрузить src/ + перезапуск
python vps_connect.py shell <cmd>  # SSH команда
```

**НИКОГДА не создавай новые deploy_*.py, check_*.py, upload_*.py.**

## Структура

```
src/
├── bot.py              — точка входа (python-telegram-bot 21.7)
├── config.py           — конфигурация
├── sheets.py           — Google Sheets CRUD (SheetsManager)
├── drive_manager.py    — Google Drive (OAuth, чеки, QR-коды)
├── handlers/
│   ├── start.py        — /start, /help
│   ├── menu.py         — навигация
│   ├── request.py      — создание заявок
│   ├── payment.py      — обработка платежей (исполнители)
│   ├── edit_handlers.py — редактирование заявок
│   └── fact_expense.py — фактические расходы
└── utils/
    ├── auth.py         — RBAC (@require_auth, @require_role)
    ├── categories.py   — авто-категоризация
    └── formatters.py   — форматирование сумм, валют
```

## Стек

- Python 3.10+ / python-telegram-bot 21.7
- Google Sheets (gspread) — БД
- Google Drive (OAuth) — хранение файлов
- Мульти-валюта: RUB, BYN, KZT, USDT, CNY

## Команды разработки

```bash
# Тесты (через invoke — работает на Windows)
.venv/Scripts/python -m invoke test-legacy   # все legacy тесты (block4 + usdt)
.venv/Scripts/python -m invoke test          # новые pytest тесты
.venv/Scripts/python -m invoke deploy        # задеплоить на VPS
.venv/Scripts/python -m invoke status        # статус бота
.venv/Scripts/python -m invoke logs          # последние 50 строк логов

# Список всех команд:
.venv/Scripts/python -m invoke --list
```

На Linux/Mac (VPS): `make test`, `make deploy` (Makefile в корне проекта).

## Правила сессии

**HANDOFF.md:** Перед закрытием браузера вызвать `/handoff`.
Файл создаётся в корне проекта. Следующая сессия начинается с его чтения.

**Contract-first:** Перед реализацией функций с побочными эффектами (пишут в Sheets,
меняют состояние) — ответить на 3 вопроса:
1. Что именно меняется? (какие ячейки/строки)
2. Что НЕ меняется? (инварианты)
3. Что возвращается при ошибке/отсутствии объекта?

Ответы идут в docstring в секцию `Side effects:` + `Invariants:` ДО написания кода.

**ADR:** Архитектурные решения фиксировать в `docs/decisions/ADR-NNN-название.md`.
Формат: Status / Context / Decision / Consequences (см. ADR-001).

## Тест-инфраструктура

- `tests/conftest.py` — fixtures: `offline_bot`, `app`, `mock_sheets`, factory functions
- `tests/test_user_management.py` — пример нового pytest-стиля
- Legacy тесты (`test_block4_users.py`, `test_usdt_fixes.py`) — кастомный runner, запускать напрямую
- `pyproject.toml` — конфиг pytest: asyncio_mode=auto, pythonpath=[".", "src"]
- pytest-asyncio **НЕ обновлять выше 0.21.x** (PTB PR #4607: 330 падений на 0.25)
