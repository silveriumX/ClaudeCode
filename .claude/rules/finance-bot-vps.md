---
description: Finance Bot VPS deployment - SSH, systemd, file structure, operations
paths:
  - "**/deploy*.py"
  - "**/deploy*.ps1"
  - "**/deploy*.sh"
  - "**/FinanceBot/**/*"
---

# Finance Bot VPS Deployment Rules

Правила для работы с VPS сервером Finance Bot.

## VPS Server Information

- **IP:** 195.177.94.189
- **User:** root
- **OS:** Linux (Ubuntu/Debian)
- **SSH Port:** 22
- **Путь к проекту:** `/root/finance_bot/`
- **systemd Service:** `finance_bot`

**ВАЖНО:** Не указывай пароли/токены в коде деплоя. Используй переменные окружения.

---

## Файловая структура на VPS

```
/root/finance_bot/
├── bot.py                    # Main bot file
├── config.py                 # Configuration
├── sheets.py                 # Google Sheets (встроенный GoogleApiManager)
├── handlers/
│   ├── start.py              # /start, /help
│   ├── request.py            # Создание заявок
│   ├── payment.py            # Регистрация выплат
│   ├── edit_handlers.py      # Редактирование заявок
│   └── menu.py               # Главное меню
├── utils/
│   ├── auth.py               # Authorization helpers
│   └── categories.py         # Category keyboards
├── .env                      # BOT_TOKEN, GOOGLE_SHEETS_ID
├── service_account.json      # Google Sheets credentials
└── requirements.txt
```

## Команды деплоя

### Перезапуск бота
```bash
systemctl restart finance_bot
systemctl status finance_bot
```

### Просмотр логов
```bash
journalctl -u finance_bot -f              # реальное время
journalctl -u finance_bot -n 50           # последние 50 строк
journalctl -u finance_bot --since "10 minutes ago"
journalctl -u finance_bot -p err          # только ошибки
```

### Полный деплой (с backup)
```bash
# 1. Backup
BACKUP_DIR="/root/finance_bot_backup_$(date +%Y%m%d_%H%M%S)"
cp -r /root/finance_bot "$BACKUP_DIR"

# 2. Обновить код
cd /root/finance_bot && git pull origin main

# 3. Зависимости (если изменились)
pip install -r requirements.txt --upgrade

# 4. Перезапуск
systemctl restart finance_bot

# 5. Проверка
systemctl status finance_bot
journalctl -u finance_bot -n 20
```

### Быстрый деплой (только код)
```bash
cd /root/finance_bot && git pull origin main
systemctl restart finance_bot
journalctl -u finance_bot -n 10
```

### Деплой конкретных файлов (через SCP)
```bash
scp Projects/FinanceBot/sheets.py root@195.177.94.189:/root/finance_bot/
scp Projects/FinanceBot/handlers/request.py root@195.177.94.189:/root/finance_bot/handlers/
ssh root@195.177.94.189 "systemctl restart finance_bot"
```

## Troubleshooting

### Бот не запускается
```bash
journalctl -u finance_bot -n 100
journalctl -u finance_bot -p err
```

Типичные ошибки:
- `ModuleNotFoundError` → `pip install -r requirements.txt`
- `FileNotFoundError: .env` → создать .env с BOT_TOKEN и GOOGLE_SHEETS_ID
- `FileNotFoundError: service_account.json` → загрузить credentials
- `Unauthorized` (Telegram) → проверить BOT_TOKEN
- `gspread.exceptions.APIError` → проверить service_account.json

### Бот не реагирует
```bash
# Проверить Google Sheets
cd /root/finance_bot
python3 -c "from sheets import GoogleSheetsManager; s = GoogleSheetsManager(); print(s.get_all_users())"
```

### Бот падает/перезагружается
```bash
htop               # CPU/memory
free -h             # RAM
journalctl -u finance_bot --since "1 hour ago"
```

## Правила безопасности

```bash
chmod 600 /root/finance_bot/.env
chmod 600 /root/finance_bot/service_account.json
```

## Checklist перед деплоем

- [ ] Нет хардкоженных паролей/токенов
- [ ] Нет импортов из `Utils/` (VPS автономность)
- [ ] Git changes committed и pushed
- [ ] Backup создан на VPS
- [ ] requirements.txt актуален

**После деплоя:**
- [ ] `systemctl status finance_bot` — OK
- [ ] `journalctl -u finance_bot -n 20` — нет ошибок
- [ ] Тест `/start` в Telegram
- [ ] Тест создания заявки (если изменения в handlers)

## Связанные правила

- `.claude/rules/vps-ssh-deployment.md` — общие стандарты SSH деплоя
- `.claude/rules/python-standards.md` — стандарты Python кода
