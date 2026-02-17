# VoiceBot

AI голосовой бот — транскрибация голосовых сообщений через Whisper + ответы через OpenAI.

## Деплой и управление VPS

Креды VPS: `.env` → VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
На сервере два бота:
- /root/voice_bot (основной) — bot.py, bot_server.py
- /root/voice_bot_public (публичный) — bot_public.py
Запуск: process + venv

### Деплой через `vps_connect.py`

```bash
python vps_connect.py status
python vps_connect.py logs [N]
python vps_connect.py restart
python vps_connect.py deploy
python vps_connect.py shell <cmd>
```

**НИКОГДА не создавай новые deploy_*.py, check_*.py, fix_*.py, install_*.py.**
Если vps_connect.py ещё не создан — создай по шаблону из EnglishTutorBot, добавив VPS-креды в .env.

## Структура

```
bot.py              — основной бот (aiogram, Whisper + OpenAI)
bot_public.py       — публичная версия
bot_server.py       — серверная версия с доп. функциями
```

## Стек

- Python 3.10+ / aiogram
- OpenAI API: Whisper (STT), GPT-4o (ответы)
- Все креды через .env (TELEGRAM_TOKEN, OPENAI_API_KEY)
