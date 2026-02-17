# ChatManager

AI-first система управления рабочими чатами в Telegram (UserBot + Control Bot).

## Деплой и управление VPS

Креды VPS: `.env` → VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
Путь на сервере: /root/ChatManager
Запуск: process (без systemd)

### Деплой через `vps_connect.py`

```bash
python vps_connect.py status       # статус
python vps_connect.py logs [N]     # логи
python vps_connect.py restart      # перезапуск
python vps_connect.py deploy       # загрузить + перезапуск
python vps_connect.py shell <cmd>  # SSH команда
```

**НИКОГДА не создавай новые deploy_*.py, check_*.py, upload_*.py.**
Если vps_connect.py ещё не создан — создай по шаблону из FinanceBot или EnglishTutorBot, добавив VPS-креды в .env.

## Структура

```
bot.py              — Control Bot (управление)
userbot.py          — UserBot (Telethon, мониторинг чатов)
config.py           — конфигурация
handlers/           — обработчики команд
sheets.py           — Google Sheets интеграция
utils/              — утилиты
```

## Стек

- Python 3.10+ / python-telegram-bot + Telethon
- Google Sheets (gspread)
