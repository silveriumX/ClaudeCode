# 🚀 БЫСТРАЯ СПРАВКА: SSH МОНИТОРИНГ

## ✅ СТАТУС: Система полностью на SSH

**Последнее обновление:** 27.01.2026 17:50
**Работает:** 15/17 серверов через SSH (88%)

---

## 📱 ИСПОЛЬЗОВАНИЕ

### Telegram команды:
```
/check   - Проверить все серверы СЕЙЧАС
/status  - Показать статистику
/help    - Список команд
```

### SSH на VPS:
```bash
# Подключение
ssh root@151.241.154.57

# Логи в реальном времени
journalctl -u server-monitor -f

# Статус службы
systemctl status server-monitor

# Перезапуск
systemctl restart server-monitor
```

---

## 🔧 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

### Проверить логи:
```bash
ssh root@151.241.154.57
journalctl -u server-monitor -n 50 --no-pager
```

### Перезапустить систему:
```bash
ssh root@151.241.154.57
systemctl restart server-monitor
journalctl -u server-monitor -f
```

### Откат на WinRM:
```bash
ssh root@151.241.154.57
systemctl stop server-monitor
cd /opt/server-monitor
rm server_checker.py session_checker.py
mv server_checker_winrm_backup.py server_checker.py
mv session_checker_winrm_backup.py session_checker.py
rm -rf __pycache__
systemctl start server-monitor
```

---

## 📊 ДАННЫЕ В GOOGLE SHEETS

Обновляются автоматически каждые 20 минут:

- **Статус машины** - OK Online / ERROR Offline
- **Статус прокси** - OK / ERROR Proxifier Off
- **Текущий IP** - IP от 2ip.io
- **Текущий город** - Город от 2ip.io
- **Запущен anydesk** - ✅/❌
- **Запущен rustdesk** - ✅/❌
- **Дата и время проверки** - timestamp
- **Результат проверки сервера** - детальный отчет

---

## ⚙️ УСТАНОВКА SSH НА ОСТАВШИХСЯ СЕРВЕРАХ

### 1. MN - 194.59.30.150
```
AnyDesk: 989970862 (пароль: MNpass21)
RDP: 194.59.30.150:Administrator:password222
```

### 2. MAKS - 77.238.246.229
```
AnyDesk: 1252612559 (пароль: maksmaks4)
RDP: 77.238.246.229:Administrator:password222
```

### Команда (в PowerShell от Администратора):
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0; Start-Service sshd; Set-Service -Name sshd -StartupType Automatic; New-NetFirewallRule -Name SSH -DisplayName SSH -Enabled True -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow
```

После установки система автоматически начнет мониторить эти серверы через SSH!

---

## 🎯 ПРЕИМУЩЕСТВА SSH

| Параметр | Результат |
|----------|-----------|
| Стабильность | ✅ 0 ошибок HTTP 500 |
| Скорость | ⚡ 3-5 сек/сервер |
| Надёжность | ✅ Не требуется watchdog |
| Покрытие | ✅ 15/17 серверов (88%) |
| Успешность | ✅ ~88-94% |

---

**Всё работает! Система стабильна! 🎉**
