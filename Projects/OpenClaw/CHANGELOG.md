# Changelog

История изменений проекта OpenClaw Management Tools.

## [1.0.0] - 2026-02-15

### Added
- Создана структура проекта OpenClaw
- Добавлен основной `vps_connect.py` для управления VPS
- Организованы legacy скрипты в подпапки:
  - `scripts/config/` - конфигурация
  - `scripts/monitoring/` - мониторинг
  - `scripts/setup/` - установка
- Создана документация:
  - `README.md` - основное описание
  - `CLAUDE.md` - инструкции для Claude
  - `INSTALL.md` - руководство по установке
  - `TROUBLESHOOTING.md` - решение проблем
- Добавлены конфигурационные файлы:
  - `.env.example` - пример переменных окружения
  - `.gitignore` - исключения для git
  - `requirements.txt` - Python зависимости

### Changed
- Переименованы legacy скрипты для улучшения читаемости:
  - `openclaw_set_env.py` → `config/set_env.py`
  - `openclaw_set_glm.py` → `config/set_glm.py`
  - `openclaw_fix_telegram_bot.py` → `config/fix_telegram.py`
  - `openclaw_verify_token_on_vps.py` → `config/verify_token.py`
  - `openclaw_recent_logs.py` → `monitoring/logs.py`
  - `watch_openclaw_logs.py` → `monitoring/watch.py`
  - `reinstall_step*.py` → `setup/install_step*.py`
  - `REMOVE_CLAWDBOT.ps1` → `setup/remove.ps1`

### Migrated
- Перенесены все файлы OpenClaw из проекта VoiceBot
- Файлы очищены от хардкода креденшелов

### Security
- Все креденшелы перенесены в `.env` файл
- Добавлен `.gitignore` для защиты `.env`
- Удалены примеры с реальными IP адресами из документации

## Roadmap

### Planned for 2.0.0
- [ ] Полная миграция функциональности legacy скриптов в `vps_connect.py`
- [ ] Добавить команду `deploy` в `vps_connect.py`
- [ ] Добавить команду `config` для управления конфигурацией
- [ ] Добавить тесты
- [ ] CI/CD pipeline

### Future
- [ ] Web UI для управления
- [ ] Docker контейнер для development
- [ ] Ansible playbook для автоматического деплоя
