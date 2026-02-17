# OpenClaw Deployment Tools

Инструменты для развертывания и управления [OpenClaw](https://github.com/openclaw/openclaw) на VPS.

## Что такое OpenClaw?

OpenClaw - это AI-агент с самомодифицирующимися инструкциями, который может:
- Работать через Telegram бота
- Самостоятельно обновлять свои промпты и конфигурацию
- Использовать различные AI модели (Anthropic Claude, GLM-4.7 через Z.AI)
- Интегрироваться с различными сервисами

## Структура проекта

```
OpenClaw/
├── scripts/              # Скрипты управления
│   ├── deploy.py        # Основной скрипт деплоя
│   ├── config/          # Конфигурация
│   ├── setup/           # Установка
│   └── monitoring/      # Мониторинг
├── CLAUDE.md            # Инструкции для Claude
├── README.md            # Этот файл
├── requirements.txt     # Python зависимости
└── .env.example         # Пример переменных окружения
```

## Быстрый старт

### 1. Настройка окружения

Создайте `.env` файл:

```bash
cp .env.example .env
```

Заполните переменные:

```env
# SSH доступ к VPS
VPS_HOST=your-vps-ip
VPS_USER=root
VPS_PASSWORD=your_password

# API ключи
ANTHROPIC_API_KEY=sk-ant-api...
ZAI_API_KEY=sk-zai-api...     # Опционально, для GLM-4.7
TELEGRAM_BOT_TOKEN=1234567890:ABC-your-bot-token
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Деплой на VPS

```bash
# Проверка статуса
python scripts/deploy.py status

# Полный деплой
python scripts/deploy.py deploy

# Просмотр логов
python scripts/deploy.py logs
```

## Доступные скрипты

### Управление

| Скрипт | Описание |
|--------|----------|
| `deploy.py` | Основной скрипт управления (status, deploy, logs, restart) |
| `vps_connect.py` | Универсальный SSH клиент для VPS |

### Конфигурация

| Скрипт | Описание |
|--------|----------|
| `config/set_env.py` | Установка ANTHROPIC_API_KEY на VPS |
| `config/set_glm.py` | Настройка модели GLM-4.7 через Z.AI |
| `config/fix_telegram.py` | Настройка Telegram бота |
| `config/verify_token.py` | Проверка токена на VPS |

### Мониторинг

| Скрипт | Описание |
|--------|----------|
| `monitoring/logs.py` | Просмотр последних логов |
| `monitoring/watch.py` | Мониторинг в реальном времени |

### Установка/Переустановка

| Скрипт | Описание |
|--------|----------|
| `setup/install.py` | Чистая установка OpenClaw |
| `setup/remove.py` | Полное удаление OpenClaw |
| `setup/reinstall.py` | Переустановка (удаление + установка) |

## Архитектура VPS

### Расположение на сервере

- **Установка:** `/usr/lib/node_modules/openclaw` (npm global package)
- **Binary:** `/usr/bin/openclaw`
- **Конфиг:** `/root/.openclaw/openclaw.json`
- **Env файл:** `/root/.openclaw/.env`
- **Systemd сервис:** `openclaw.service`
- **Логи:** `journalctl -u openclaw`

### Конфигурация OpenClaw

`/root/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "zai/glm-4.7"
      }
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "dmPolicy": "pairing",
      "botToken": "..."
    }
  }
}
```

## Устранение проблем

### Бот не отвечает

1. Проверьте статус сервиса:
   ```bash
   python scripts/deploy.py status
   ```

2. Проверьте логи:
   ```bash
   python scripts/deploy.py logs 50
   ```

3. Перезапустите:
   ```bash
   python scripts/deploy.py restart
   ```

### Конфликт токенов

Если бот отвечает "Conflict: terminated by other getUpdates":

```bash
python scripts/config/fix_telegram.py
```

### Смена модели AI

Для переключения на GLM-4.7:

```bash
python scripts/config/set_glm.py
```

## Связанные проекты

- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [VoiceBot](../VoiceBot) - голосовой Telegram бот

## License

MIT
