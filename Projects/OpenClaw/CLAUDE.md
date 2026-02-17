# OpenClaw Project

Инструменты для развертывания и управления OpenClaw AI-агента на VPS.

## Automation Preferences

- **Автономный режим:** Максимальная автономия
- **Не требуется подтверждение** для:
  - Создания/редактирования скриптов
  - Чтения логов
  - Проверки статуса

- **Спрашивать только для:**
  - Выполнения команд на VPS (deploy, restart, remove)
  - Изменения конфигурации на сервере
  - Удаления данных

## Development Guidelines

- Все креды через `.env` файл
- Использовать `vps_connect.py` для управления
- **НИКОГДА** не создавать новые `deploy_*.py`, `check_*.py`, `fix_*.py` - использовать единый `vps_connect.py`
- Следовать стандартам из `@.claude/rules/python-standards.md`
- Все скрипты с UTF-8 encoding support для Windows

## Структура проекта

```
OpenClaw/
├── vps_connect.py          # Единственный скрипт управления VPS
├── scripts/
│   ├── config/             # Конфигурация (legacy, постепенно мигрируем в vps_connect)
│   ├── setup/              # Установка (legacy)
│   └── monitoring/         # Мониторинг (legacy)
├── CLAUDE.md               # Этот файл
├── README.md               # Документация
├── requirements.txt        # Python зависимости
└── .env.example            # Пример переменных окружения
```

## VPS Environment

- **OS:** Linux (Ubuntu/Debian)
- **Node.js:** Required for OpenClaw
- **Systemd:** Used for service management
- **Locations:**
  - Binary: `/usr/bin/openclaw`
  - Module: `/usr/lib/node_modules/openclaw` (npm global install)
  - Config: `/root/.openclaw/openclaw.json`
  - Env file: `/root/.openclaw/.env`
  - Service: `openclaw.service`

## Commands

Все через единый `vps_connect.py`:

```bash
# Статус
python vps_connect.py status

# Логи
python vps_connect.py logs [N]

# Перезапуск
python vps_connect.py restart

# Деплой
python vps_connect.py deploy

# Shell команда
python vps_connect.py shell "systemctl status openclaw"
```

## Environment Variables

Используются следующие переменные (см. `.env.example`):

### SSH подключение
- `VPS_HOST` - IP или домен VPS
- `VPS_PORT` - SSH порт (по умолчанию 22)
- `VPS_USER` - SSH пользователь
- `VPS_PASSWORD` - SSH пароль

### Legacy (для совместимости со старыми скриптами)
- `VOICEBOT_SSH_PASS` → `VPS_PASSWORD`
- `VOICEBOT_HOST` → `VPS_HOST`
- `VOICEBOT_USER` → `VPS_USER`

### API Keys
- `ANTHROPIC_API_KEY` - Anthropic Claude API
- `OPENCLAW_ANTHROPIC_KEY` - альтернативное имя
- `ZAI_API_KEY` - Z.AI для GLM-4.7
- `OPENCLAW_ZAI_API_KEY` - альтернативное имя
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `OPENCLAW_TELEGRAM_BOT_TOKEN` - альтернативное имя

## Security

- **НЕ КОММИТИТЬ** `.env` файл
- **НЕ ХАРДКОДИТЬ** креды в скриптах
- **НЕ ЛОГИРОВАТЬ** пароли и токены
- Использовать `.gitignore` для `.env`

## Migration Plan

Постепенно мигрируем legacy скрипты в единый `vps_connect.py`:

- [x] Создать структуру проекта
- [ ] Создать `vps_connect.py` (по образцу EnglishTutorBot)
- [ ] Мигрировать функции из `scripts/config/*`
- [ ] Мигрировать функции из `scripts/monitoring/*`
- [ ] Мигрировать функции из `scripts/setup/*`
- [ ] Удалить legacy скрипты

## Related

- См. также: `@.claude/skills/deploy-linux-vps` для паттернов деплоя
