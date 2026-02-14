---
name: deploy-linux-vps
description: Deploy application to Linux VPS via SSH/SFTP. Stops process by full path, uploads files, restarts with nohup. Includes --logs mode. Use when user wants to deploy to Linux VPS, roll out bot/script to server, or fetch remote logs.
disable-model-invocation: true
---

# Deploy on Linux VPS via SSH

Вызывай `/deploy-linux-vps` для деплоя на Linux VPS.

---

## Обязательные правила

### 1. Остановка процесса

- Убивать процесс по **полному пути** к главному файлу (например `/root/my_bot/bot.py`), иначе `pkill -f bot.py` может не найти процесс или убить чужой.
- Если процесс запускался как `python3 bot.py` (без полного пути), pkill по пути не сработает. Дополнительно: найти PID через `pgrep -f 'bot.py'`, проверить `readlink /proc/$pid/cwd` — если равен `REMOTE_DIR`, выполнить `kill -9 $pid`.
- После остановки — **пауза 3–5 с**, затем при необходимости (см. ниже) — ожидание освобождения внешнего API (Telegram и т.д.) **25–30 с**.

### 2. Запуск процесса

- Запускать через **полный путь**: `nohup python3 /root/my_bot/bot.py >> bot.log 2>> bot_error.log &` (или аналог для Node/другого рантайма). Так следующий деплой сможет надёжно убить процесс по этому же пути.
- Не запускать как `python3 bot.py` из `cd REMOTE_DIR` — иначе pkill по полному пути не найдёт процесс.

### 3. Режим «только логи»

- В деплой-скрипте должен быть режим (например `--logs`): подключение по SSH, вывод `tail` логов (и при необходимости `pgrep -af` по имени процесса) **без** загрузки файлов и перезапуска. Так после деплоя можно сразу смотреть ошибки без ручного входа по SSH.

### 4. Что делает скрипт деплоя (по шагам)

1. Читать конфиг и секреты из `.env` (или одного места); не хардкодить пароли в репозитории.
2. SSH: создать `REMOTE_DIR`, загрузить файлы по SFTP (код, при необходимости `requirements.txt` и т.д.).
3. Записать на сервер `.env` (и при необходимости отдельные ключи, например SA JSON).
4. Установить зависимости (например `pip install -r requirements.txt`) при необходимости.
5. Остановить старый процесс (по полному пути + при необходимости по cwd).
6. Подождать 3–5 с; если есть Telegram/другие long-polling — подождать ещё 25–30 с; при использовании webhook — вызвать deleteWebhook перед запуском.
7. Запустить новый процесс через nohup с **полным путём** к исполняемому файлу.
8. Опционально: проверить, что процесс запустился, и вывести последние строки логов.

### 5. Windows / PowerShell

- Не использовать `cd PROJECT && python deploy.py` — в PowerShell `&&` не поддерживается. Использовать отдельные команды через `;`.
- В скрипте деплоя при выводе в консоль на Windows задавать UTF-8 для stdout/stderr (`sys.stdout.reconfigure(encoding='utf-8', errors='replace')` или аналог).

---

## Параметры (задаются в коде скрипта или .env)

- `VPS_HOST`, `VPS_USER`, `VPS_PASS` (или ключ) — подключение SSH.
- `REMOTE_DIR` — каталог на сервере (например `/root/my_bot`).
- Список файлов для загрузки (например `bot.py`, `config.py`, `requirements.txt`).
- Путь к Service Account JSON (если нужен) — из переменной или workspace root, не хардкод в коде.

---

## Пример структуры деплой-скрипта

```python
# Псевдокод
if "--logs" in sys.argv:
    ssh = connect()
    run(ssh, f"tail -80 {REMOTE_DIR}/bot_error.log; tail -40 {REMOTE_DIR}/bot.log")
    exit(0)
# иначе: upload, pip install, pkill по полному пути, sleep 30, deleteWebhook (если бот), nohup с полным путём
```
