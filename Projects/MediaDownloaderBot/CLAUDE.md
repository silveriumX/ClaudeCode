# MediaDownloaderBot

Telegram-бот для скачивания медиа через yt-dlp.

## Деплой и управление VPS

Креды VPS: `.env` → VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
Путь на сервере: /root/media_downloader_bot
Запуск: process + venv

### Деплой через `vps_connect.py`

```bash
python vps_connect.py status
python vps_connect.py logs [N]
python vps_connect.py restart
python vps_connect.py deploy
python vps_connect.py shell <cmd>
```

**НИКОГДА не создавай новые deploy_*.py, check_*.py.**
Если vps_connect.py ещё не создан — создай по шаблону из EnglishTutorBot, добавив VPS-креды в .env.

## Стек

- Python 3.10+ / python-telegram-bot
- yt-dlp для скачивания медиа
- Все креды через .env
