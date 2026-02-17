# 📦 Server Monitor Package

Полный пакет системы мониторинга Windows серверов.

## 📁 Содержимое пакета:

### Python модули:
- `server_monitor.py` - Автомониторинг серверов (каждые 20 минут)
- `command_handler.py` - Обработка команд через webhook
- `proxyma_monitor.py` - Мониторинг Proxyma пакетов (каждые 3 часа)
- `server_checker.py` - Проверка статуса серверов
- `winrm_connector.py` - WinRM подключения
- `proxyma_api.py` - Proxyma API клиент
- `config.py` - Конфигурация системы

### Конфигурация:
- `config.example.env` - Пример .env файла
- `requirements.txt` - Python зависимости

### Systemd сервисы:
- `systemd/server-monitor.service`
- `systemd/command-webhook.service`
- `systemd/proxyma-monitor.service`
- `systemd/proxyma-monitor.timer`

### Google Apps Script:
- `google-apps-script.js` - Код для Google Sheets

### Документация:
- `README.md` - Основная документация
- `INSTALLATION.md` - Пошаговая установка
- `QUICK_START.md` - Быстрый старт

## 🚀 Установка:

См. `INSTALLATION.md` для подробной инструкции.

## 📞 Поддержка:

- Логи: `journalctl -u server-monitor -f`
- Конфигурация: `/opt/server-monitor/.env`
