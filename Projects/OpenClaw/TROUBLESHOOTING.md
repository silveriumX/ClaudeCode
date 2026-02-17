# Troubleshooting

Решение типичных проблем с OpenClaw.

## Проблемы с подключением

### SSH connection failed

**Причины:**
- Неверный пароль
- Неверный хост/порт
- Firewall блокирует подключение

**Решение:**
1. Проверьте `.env` файл
2. Попробуйте подключиться вручную: `ssh root@your-vps-ip`
3. Проверьте firewall: `ufw status`

### paramiko not installed

**Решение:**
```bash
pip install -r requirements.txt
```

## Проблемы с OpenClaw

### Service: inactive (dead)

Сервис не запущен.

**Решение:**
```bash
python vps_connect.py shell "systemctl start openclaw"
python vps_connect.py status
```

### Processes: 0

OpenClaw не запущен, хотя сервис active.

**Причины:**
- Ошибка при запуске
- Неверная конфигурация
- Отсутствует .env файл

**Решение:**
```bash
# Проверить логи
python vps_connect.py logs 100

# Проверить .env
python vps_connect.py shell "cat /root/.openclaw/.env"

# Перезапустить
python vps_connect.py restart
```

### Installation: missing

OpenClaw не установлен.

**Решение:**
```bash
# Установить через npm на VPS
python vps_connect.py shell "npm install -g openclaw"
```

## Проблемы с Telegram ботом

### Conflict: terminated by other getUpdates

Бот запущен в нескольких местах одновременно.

**Причины:**
- Старый процесс всё ещё работает
- Бот запущен локально и на VPS
- Несколько VPS с одним токеном

**Решение:**
```bash
# 1. Остановить все процессы бота
python vps_connect.py shell "pkill -f openclaw"

# 2. Удалить webhook (если был)
python vps_connect.py shell "curl https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# 3. Подождать 25-30 секунд

# 4. Перезапустить
python vps_connect.py restart
```

### Bot not responding

**Причины:**
- Неверный токен
- Бот не запущен
- Ошибка в конфигурации

**Решение:**
```bash
# 1. Проверить токен
python scripts/config/verify_token.py

# 2. Проверить конфигурацию
python vps_connect.py shell "cat /root/.openclaw/openclaw.json"

# 3. Исправить токен
python scripts/config/fix_telegram.py

# 4. Проверить логи
python vps_connect.py logs 50 | grep -i telegram
```

## Проблемы с API

### API Key not found

**Решение:**
```bash
# Установить ключ
python scripts/config/set_env.py
```

### Rate limit exceeded

Превышен лимит запросов к API.

**Решение:**
- Подождите несколько минут
- Проверьте лимиты на странице API провайдера
- Рассмотрите повышение лимитов

### Invalid API Key

**Решение:**
1. Проверьте правильность ключа в `.env`
2. Убедитесь, что ключ не содержит лишних пробелов
3. Обновите ключ на VPS: `python scripts/config/set_env.py`

## Проблемы с логами

### No logs available

**Причины:**
- Сервис никогда не запускался
- Логи были очищены

**Решение:**
```bash
# Запустить сервис
python vps_connect.py restart

# Проверить логи напрямую
python vps_connect.py shell "journalctl -u openclaw --no-pager"
```

## Диагностика

### Полная проверка системы

```bash
# 1. Статус сервиса
python vps_connect.py status

# 2. Логи
python vps_connect.py logs 100

# 3. Процессы
python vps_connect.py shell "ps aux | grep openclaw"

# 4. Конфигурация
python vps_connect.py shell "cat /root/.openclaw/openclaw.json"

# 5. Environment
python vps_connect.py shell "cat /root/.openclaw/.env"

# 6. Systemd статус
python vps_connect.py shell "systemctl status openclaw"
```

## Переустановка

Если ничего не помогает, попробуйте чистую переустановку:

```bash
# 1. Удалить OpenClaw
python scripts/setup/install_step1.py

# 2. Установить заново
python scripts/setup/install_step2.py

# 3. Настроить
python scripts/config/set_env.py
python scripts/config/fix_telegram.py

# 4. Запустить
python vps_connect.py restart
```

## Получение помощи

Если проблема не решена:

1. Соберите информацию:
   - Вывод `python vps_connect.py status`
   - Последние 100 строк логов: `python vps_connect.py logs 100`
   - Версия OpenClaw: `python vps_connect.py shell "openclaw --version"`

2. Проверьте issues в репозитории OpenClaw: https://github.com/openclaw/openclaw/issues

3. Создайте новый issue с собранной информацией
