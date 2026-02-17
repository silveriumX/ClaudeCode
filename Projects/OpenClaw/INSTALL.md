# Installation Guide

Руководство по установке OpenClaw Management Tools.

## Требования

- Python 3.10+
- SSH доступ к VPS с Linux
- Node.js на VPS (для OpenClaw)

## Установка

### 1. Клонирование (если через git)

```bash
cd Projects/OpenClaw
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка окружения

Создайте `.env` файл из примера:

```bash
cp .env.example .env
```

Отредактируйте `.env` и заполните:

- `VPS_HOST` - IP адрес или домен вашего VPS
- `VPS_USER` - SSH пользователь (обычно root)
- `VPS_PASSWORD` - SSH пароль
- `ANTHROPIC_API_KEY` - ваш Anthropic API ключ
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота

### 4. Проверка подключения

```bash
python vps_connect.py status
```

Если всё настроено правильно, вы увидите статус OpenClaw на VPS.

## Установка OpenClaw на VPS

OpenClaw устанавливается на VPS через npm:

### Вариант 1: Вручную через SSH

```bash
ssh root@your-vps-ip

# Установка Node.js (если не установлен)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Установка OpenClaw
npm install -g openclaw

# Создание конфигурации
mkdir -p ~/.openclaw
openclaw init
```

### Вариант 2: Через скрипты (legacy)

```bash
# Шаг 1: Удаление старой версии (если есть)
python scripts/setup/install_step1.py

# Шаг 2: Установка новой версии
python scripts/setup/install_step2.py
```

## Настройка OpenClaw

### Установка API ключей

```bash
# Anthropic API Key
python scripts/config/set_env.py

# GLM-4.7 через Z.AI (опционально)
python scripts/config/set_glm.py

# Telegram Bot
python scripts/config/fix_telegram.py
```

### Проверка конфигурации

```bash
python vps_connect.py shell "cat /root/.openclaw/openclaw.json"
```

## Запуск сервиса

### Создание systemd сервиса

Создайте файл `/etc/systemd/system/openclaw.service` на VPS:

```ini
[Unit]
Description=OpenClaw AI Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=/root/.openclaw/.env
ExecStart=/usr/bin/openclaw gateway
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Запуск

```bash
python vps_connect.py shell "systemctl daemon-reload"
python vps_connect.py shell "systemctl enable openclaw"
python vps_connect.py shell "systemctl start openclaw"
python vps_connect.py status
```

## Устранение проблем

См. [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
