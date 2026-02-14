---
name: telegram-bot-linux
description: Run Telegram bot on Linux (polling, webhook, restart). Avoid Conflict errors by pkill with full path, deleteWebhook before start, drop_pending_updates, and 25-30s wait. Use when deploying Telegram bot to Linux VPS, fixing "Conflict" or "terminated by other getUpdates".
disable-model-invocation: true
---

# Telegram-бот на Linux VPS

Вызывай `/telegram-bot-linux` для деплоя Telegram-бота.

---

## Избежание ошибки Conflict (terminated by other getUpdates)

### 1. Остановка старого процесса

- Убивать процесс по **полному пути** к скрипту бота: `pkill -9 -f '/root/my_bot/bot.py'`.
- Запуск бота на сервере — всегда с **полным путём**: `nohup python3 /root/my_bot/bot.py ...`, а не `cd /root/my_bot && python3 bot.py`.
- Если процесс всё равно остаётся: найти PID через `pgrep -f 'bot.py'`, проверить `readlink /proc/$pid/cwd` — если равен каталогу бота, выполнить `kill -9 $pid`.

### 2. Пауза перед новым запуском

- После остановки процесса подождать **25–30 секунд**, чтобы Telegram успел освободить сессию getUpdates. Иначе новый процесс получит Conflict.

### 3. Webhook перед polling

- Если бот переключается с webhook на polling (или неизвестно, что было раньше), перед запуском вызвать **deleteWebhook** (GET или POST `https://api.telegram.org/bot<TOKEN>/deleteWebhook`). Иначе Telegram может продолжать слать обновления на старый URL и конфликтовать с polling.

### 4. В коде бота

- При запуске polling использовать `app.run_polling(..., drop_pending_updates=True)`, чтобы не обрабатывать старые обновления после перезапуска.
- Токен брать из окружения (`os.getenv("TELEGRAM_BOT_TOKEN")`); не хардкодить в коде.

---

## Чеклист деплоя Telegram-бота на Linux

1. Остановить процесс: `pkill -9 -f 'REMOTE_DIR/bot.py'`; при необходимости добить по cwd.
2. Подождать 3–5 с.
3. Вызвать deleteWebhook (скриптом или `curl`).
4. Подождать ещё 25–30 с.
5. Запустить: `nohup python3 REMOTE_DIR/bot.py >> bot.log 2>> bot_error.log &`.
6. Проверить: `pgrep -af bot.py`, `tail` логов.

---

## Типичные ошибки

- **Conflict** — два процесса получают getUpdates или webhook не сброшен; применить пункты выше.
- **Бот не реагирует** — проверить логи (`tail bot_error.log`), наличие токена в `.env`, доступность API Telegram с сервера.
