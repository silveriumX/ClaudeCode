# Monitoring Scripts

Legacy скрипты для мониторинга OpenClaw.

## Доступные скрипты

### logs.py
Показывает последние строки логов OpenClaw.

**Использование:**
```bash
python scripts/monitoring/logs.py
```

**Альтернатива через vps_connect.py:**
```bash
python vps_connect.py logs 50
```

### watch.py
Мониторинг логов OpenClaw в реальном времени.

**Использование:**
```bash
python scripts/monitoring/watch.py
```

## Миграция

Используйте `vps_connect.py logs` вместо этих скриптов.
