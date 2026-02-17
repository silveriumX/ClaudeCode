# TelegramHub

Универсальный CRM для управления Telegram аккаунтами + AI помощники (Claude, GPT, Gemini).

## Деплой и управление VPS

Креды VPS: `.env` → VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
Путь на сервере: /root/universal_cursor_bot
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
Если vps_connect.py ещё не создан — создай по шаблону из FinanceBot, добавив VPS-креды в .env.

## Структура

```
server/
├── main.py                 — точка входа
├── config.py               — конфигурация (AI провайдер, модель)
├── telegram_manager.py     — управление аккаунтами
├── universal_cursor_bot.py — AI бот (Claude/GPT/Gemini)
└── mobile_cursor_bot.py    — мобильный пульт для Cursor
ai_overlay_ayugram.py       — AI оверлей для AyuGram (локальный)
```

## Стек

- Python 3.10+ / telebot + Telethon
- Claude API, OpenAI API, Google Gemini (через .env)
- Все креды через .env (TELEGRAM_TOKEN, AI_API_KEY, OPENAI_API_KEY)
