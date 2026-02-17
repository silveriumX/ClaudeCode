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
