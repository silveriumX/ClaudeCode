# Windows Server Monitoring System

Автоматическая система мониторинга и управления Windows VPS серверами через Google Sheets.

## 📋 Компоненты системы

### Модули Python
- `config.py` - Конфигурация (загрузка из .env)
- `winrm_connector.py` - WinRM подключения к Windows серверам
- `server_checker.py` - Проверка статуса серверов
- `server_monitor.py` - Автоматический мониторинг каждые 20 минут
- `command_handler.py` - Обработка команд из Google Sheets (webhook)

### Сервисы Linux
- `server-monitor.service` - Автомониторинг
- `command-webhook.service` - Обработчик команд (Flask на порту 8080)

### Внешние интеграции
- Google Sheets - Интерфейс управления
- Telegram Bot - Уведомления об ошибках
- 2IP.io API - Проверка внешнего IP и геолокации

---

## 🚀 Быстрый старт

### Управление сервисами
```bash
# Проверка статуса
systemctl status server-monitor
systemctl status command-webhook

# Остановка/запуск
systemctl stop server-monitor
systemctl start server-monitor
systemctl restart command-webhook

# Просмотр логов
journalctl -u server-monitor -f
journalctl -u command-webhook -f
```

### Изменение конфигурации

Редактируй файл `/opt/server-monitor/.env`:
```bash
nano /opt/server-monitor/.env
```

После изменений перезапусти сервисы:
```bash
systemctl restart server-monitor
systemctl restart command-webhook
```

---

## 📝 Доступные команды (через Google Sheets)

### Мониторинг
- `check` - Полная проверка сервера (IP, город, процессы)

### Таймзона
- `get_timezone` - Показать таймзону и точное время
- `set_timezone_msk` - Установить Moscow Standard Time (UTC+3)
- `set_timezone_ekt` - Установить Ekaterinburg/Perm (UTC+5)

### Языки
- `get_languages` - Показать установленные языки
- `set_lang_russian` - Установить русский язык (требует перезагрузки)
- `set_lang_english` - Установить английский язык (требует перезагрузки)

### Программы
- `start_proxifier` - Запустить Proxifier
- `stop_proxifier` - Остановить Proxifier
- `restart_proxifier` - Перезапустить Proxifier
- `start_anydesk` - Запустить AnyDesk

### Система
- `reboot` - Перезагрузить сервер

---

## 🔧 Структура файлов
```
/opt/server-monitor/
├── .env                    # Секретные данные (токены, API keys)
├── config.example.env      # Пример конфигурации
├── config.py              # Загрузчик конфигурации
├── winrm_connector.py     # МОДУЛЬ: WinRM подключения
├── server_checker.py      # МОДУЛЬ: Проверка статуса
├── server_monitor.py      # МОДУЛЬ: Автомониторинг
├── command_handler.py     # МОДУЛЬ: Обработка команд
├── requirements.txt       # Python зависимости
└── README.md             # Эта документация
```

---

## 🛠️ Настройка нового сервера

### На Windows сервере:

1. **Включить WinRM:**
```powershell
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

2. **Создать папку для программ (опционально):**
```powershell
New-Item -Path "C:\ServerApps" -ItemType Directory
```

3. **Создать ярлыки в C:\ServerApps:**
```powershell
# Proxifier
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\ServerApps\Proxifier.lnk")
$Shortcut.TargetPath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$Shortcut.Save()

# AnyDesk
$Shortcut = $WshShell.CreateShortcut("C:\ServerApps\AnyDesk.lnk")
$Shortcut.TargetPath = "C:\Program Files (x86)\AnyDesk\AnyDesk.exe"
$Shortcut.Save()
```

4. **Добавить сервер в Google Sheets** в формате:
```
IP:Username:Password
```

---

## 📊 Мониторинг

### Автоматическая проверка
Система проверяет все сервера каждые **20 минут** (1200 секунд).

Изменить интервал можно в `config.py`:
```python
CHECK_INTERVAL = 30 * 60  # 30 минут
```

### Telegram уведомления
При обнаружении проблем отправляет уведомления в Telegram.

Добавить Chat ID в `config.py`:
```python
TELEGRAM_CHAT_IDS = [123456789, 987654321]
```

---

## 🐛 Диагностика проблем

### Сервис не запускается
```bash
# Проверить ошибки
journalctl -u server-monitor -n 50
journalctl -u command-webhook -n 50

# Проверить права на файлы
ls -la /opt/server-monitor/

# Переустановить зависимости
pip3 install -r /opt/server-monitor/requirements.txt
```

### Не работают команды из таблицы
```bash
# Проверить webhook логи
journalctl -u command-webhook -f

# Проверить доступность webhook
curl http://localhost:8080/health
```

### WinRM не подключается к серверу
На Windows сервере:
```powershell
# Проверить статус WinRM
Get-Service WinRM

# Перезапустить WinRM
Restart-Service WinRM

# Проверить файрволл
Test-NetConnection -ComputerName localhost -Port 5985
```

---

## 📦 Резервное копирование

### Важные файлы для бэкапа:
```bash
/opt/server-monitor/.env          # Секретные данные
/opt/server-monitor/config.py     # Конфигурация
```

### Создать бэкап:
```bash
tar -czf server-monitor-backup-$(date +%Y%m%d).tar.gz /opt/server-monitor/
```

---

## 🔄 Обновление системы
```bash
# 1. Остановить сервисы
systemctl stop server-monitor command-webhook

# 2. Скопировать новые файлы модулей
# (обновленные .py файлы)

# 3. Запустить сервисы
systemctl start server-monitor command-webhook

# 4. Проверить статус
systemctl status server-monitor command-webhook
```

---

## 📞 Контакты и поддержка

- Логи: `journalctl -u server-monitor -f`
- Конфигурация: `/opt/server-monitor/.env`
- Документация модулей: см. комментарии в .py файлах

---

**Версия системы:** 2.0 (модульная архитектура)
**Дата:** 2026-01-03
