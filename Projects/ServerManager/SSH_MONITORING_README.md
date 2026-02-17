# SSH Мониторинг v5.0

## Архитектура

```
┌─────────────────┐         SSH          ┌─────────────────┐
│                 │ ◄─────────────────   │                 │
│  VPS (Linux)    │                      │ Windows Server  │
│                 │ ──────────────────►  │                 │
│  Python         │   PowerShell cmd     │  SSH Server     │
│  ssh_connector  │                      │  (openssh)      │
└─────────────────┘                      └─────────────────┘
```

## Компоненты

### 1. `ssh_connector.py`
- Подключается к Windows через SSH
- Выполняет PowerShell команды (через -EncodedCommand)
- Возвращает результат
- **Стабильный** - не ломается как WinRM

### 2. `server_checker_ssh.py`
- Использует `SSHConnector` вместо `WinRMConnector`
- Та же логика проверки:
  - Процессы (Proxifier, AnyDesk, RustDesk)
  - IP через 2ip.io (HTTP)
  - RDP/AnyDesk сессии
  - Client IP
- Тот же формат результата

### 3. `server_monitor_ssh.py`
- Основной скрипт мониторинга
- Использует `ServerChecker` с SSH
- Telegram бот
- Обновление Google Sheets

## Деплой

```bash
python deploy_ssh_monitoring.py
```

Скрипт автоматически:
1. Останавливает WinRM мониторинг
2. Создаёт бэкап WinRM файлов
3. Загружает SSH файлы
4. Создаёт symlink `server_checker.py` → `server_checker_ssh.py`
5. Устанавливает `paramiko`
6. Запускает SSH мониторинг

## Преимущества SSH

| Критерий | WinRM | SSH |
|----------|-------|-----|
| **Стабильность** | ❌ HTTP 500 ошибки | ✅ Не ломается |
| **Скорость** | 8-12 сек/сервер | 3-5 сек/сервер |
| **Надёжность** | Требует watchdog | Работает стабильно |
| **Сложность** | SOAP/XML протокол | Простой протокол |
| **Output** | Теряется при timeout | Всегда получаем |

## Откат на WinRM

Если нужно вернуться:

```bash
cd /opt/server-monitor
systemctl stop server-monitor
rm server_checker.py
mv server_checker_winrm_backup.py server_checker.py
mv server_monitor_winrm_backup.py server_monitor.py
rm -rf __pycache__
systemctl start server-monitor
```

## Требования

### На Windows серверах:
- ✅ OpenSSH Server установлен
- ✅ Служба sshd запущена (автозапуск)
- ✅ Firewall разрешает порт 22
- ✅ Credentials те же что и для WinRM

### На VPS:
- ✅ Python 3.x
- ✅ paramiko (установится автоматически)
- ✅ requests, requests_ntlm (уже есть)
- ✅ telebot, gspread (уже есть)

## Мониторинг после миграции

- Проверка каждые 20 минут
- Telegram уведомления
- Google Sheets обновление
- WinRM Watchdog **больше не нужен** (SSH стабильнее)

## Дополнительные возможности SSH

### 1. Установка AnyDesk:

```python
connector.execute_command(ip, user, pwd, '''
Invoke-WebRequest "https://download.anydesk.com/AnyDesk.exe" -OutFile C:\\AnyDesk.exe
Start-Process C:\\AnyDesk.exe -ArgumentList "--install C:\\AnyDesk --silent" -Wait
''')
```

### 2. Управление Proxifier:

```python
# Остановить
connector.execute_command(ip, user, pwd, "Stop-Process -Name Proxifier -Force -EA 0")

# Запустить
connector.execute_command(ip, user, pwd, "Start-Process 'C:\\Program Files (x86)\\Proxifier\\Proxifier.exe'")

# Изменить профиль (редактировать XML)
connector.execute_command(ip, user, pwd, '''
$xml = [xml](Get-Content "C:\\ProgramData\\Proxifier\\Profiles\\Default.ppx")
# Изменить proxy settings
$xml.Save("C:\\ProgramData\\Proxifier\\Profiles\\Default.ppx")
''')
```

### 3. Файловые операции:

```python
# Скачать файл
sftp = paramiko.SFTPClient.from_transport(client.get_transport())
sftp.get("C:\\remote_file.txt", "local_file.txt")

# Загрузить файл
sftp.put("local_file.exe", "C:\\remote_file.exe")
```

## Логи

```bash
# На VPS
journalctl -u server-monitor -f

# Фильтр для SSH
journalctl -u server-monitor | grep "SSH"
```

## Статус

```bash
systemctl status server-monitor
```

## Версия

v5.0 (SSH) - 26.01.2026
