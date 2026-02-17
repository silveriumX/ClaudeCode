# Scripts Directory

Legacy скрипты для управления OpenClaw.

**ВАЖНО:** Эти скрипты постепенно мигрируются в единый `vps_connect.py` в корне проекта.

Для новых задач используйте `vps_connect.py` вместо создания новых скриптов здесь.

## Структура

```
scripts/
├── config/         # Конфигурация OpenClaw на VPS
├── monitoring/     # Мониторинг логов и статуса
└── setup/          # Установка и переустановка
```

## Config

Скрипты для настройки OpenClaw:

- `set_env.py` - Установка ANTHROPIC_API_KEY
- `set_glm.py` - Настройка модели GLM-4.7
- `fix_telegram.py` - Настройка Telegram бота
- `verify_token.py` - Проверка токена

**Использование:**

1. Настройте `.env` файл в корне проекта (см. `.env.example`)
2. Запустите нужный скрипт:
```bash
python scripts/config/set_env.py
```

## Monitoring

Скрипты для мониторинга:

- `logs.py` - Просмотр последних логов
- `watch.py` - Мониторинг в реальном времени

## Setup

Скрипты установки (legacy):

- `install_step1.py` - Удаление старой версии
- `install_step2.py` - Установка через npm
- `install_step2b.py` - Установка с длинным таймаутом
- `remove.ps1` - PowerShell скрипт удаления

**ВНИМАНИЕ:** Эти скрипты устарели. Для установки используйте официальную документацию OpenClaw.
