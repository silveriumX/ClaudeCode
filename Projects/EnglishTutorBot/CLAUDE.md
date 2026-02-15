# EnglishTutorBot

AI-репетитор английского/японского/испанского через голосовые сообщения в Telegram.

## Деплой и управление VPS

Креды VPS: `.env` → VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
Путь на сервере: `.env` → VPS_REMOTE_DIR
Запуск: nohup python3 bot.py (без systemd)

### Единственный инструмент: `vps_connect.py`

```bash
python vps_connect.py status       # статус бота, RAM, диск
python vps_connect.py logs [N]     # последние N строк лога
python vps_connect.py errors [N]   # ошибки
python vps_connect.py restart      # перезапуск через nohup
python vps_connect.py deploy       # загрузить файлы + перезапуск
python vps_connect.py shell <cmd>  # произвольная SSH команда
```

**НИКОГДА не создавай новые deploy_*.py, check_*.py, upload_*.py.**
Нужна новая функция — добавь в vps_connect.py.

## Структура

```
bot.py              — главный файл (aiogram 3.13, long polling)
user_profile.py     — профили пользователей (JSON в user_data/)
session_manager.py  — тайм-сессии практики
intent_detector.py  — распознавание голосовых команд (GPT-4o-mini)
prompts.py          — промпты тьютора по языкам (EN/JP/ES)
vps_connect.py      — управление VPS (SSH через paramiko)
```

## Стек

- Python 3.10+ / aiogram 3.13.1
- OpenAI API: GPT-4o (анализ), Whisper (STT), TTS-1-HD (озвучка)
- Хранение: JSON файлы в user_data/
