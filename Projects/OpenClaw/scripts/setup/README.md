# Setup Scripts

Legacy скрипты для установки и удаления OpenClaw.

## Доступные скрипты

### install_step1.py
Удаляет старую установку OpenClaw (если есть).

### install_step2.py
Устанавливает OpenClaw через npm.

### install_step2b.py
Установка с увеличенным таймаутом (для медленных соединений).

### remove.ps1
PowerShell скрипт для полного удаления ClawdBot (старое название).

## Использование

**Полная переустановка:**
```bash
# Шаг 1: Удаление
python scripts/setup/install_step1.py

# Шаг 2: Установка
python scripts/setup/install_step2.py
```

## Важно

Эти скрипты устаревшие. Для новых установок рекомендуется:
1. Следовать официальной документации OpenClaw
2. Использовать `vps_connect.py deploy` (когда будет реализовано)
