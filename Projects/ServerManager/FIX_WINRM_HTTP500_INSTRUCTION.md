# Исправление HTTP 500 ошибок WinRM

**Проблема:** 5 серверов возвращают HTTP 500 при попытке подключения через WinRM
**Причина:** Внутренняя конфигурация WinRM на Windows серверах

---

## Проблемные серверы:

1. **89.124.71.240** - Магазин ALEX
2. **89.124.72.242** - Магазин ALEX
3. **91.201.113.127** - Магазин HUB
4. **62.84.101.97** - Магазин HUB
5. **5.35.32.68** - Магазин HUB

---

## ШАГ 1: Подключение к серверу

Подключитесь к **ЛЮБОМУ** проблемному серверу через RDP или AnyDesk.

**Например:** `89.124.71.240` (ALEX)
- RDP: `89.124.71.240:Administrator:password222`
- AnyDesk: (есть в таблице)

---

## ШАГ 2: Диагностика

Откройте **PowerShell от администратора** на сервере и выполните:

### 2.1. Проверка статуса WinRM

```powershell
Get-Service WinRM
```

**Ожидается:** Status = Running

Если не запущен:
```powershell
Start-Service WinRM
Set-Service WinRM -StartupType Automatic
```

---

### 2.2. Проверка текущих лимитов

```powershell
winrm get winrm/config/winrs
```

**Обратите внимание на:**
- `MaxMemoryPerShellMB` - сколько памяти может использовать один shell
- `MaxShellsPerUser` - сколько одновременных shell'ов для одного пользователя
- `MaxConcurrentOperationsPerUser` - максимум операций

**Проблемные значения:**
- MaxMemoryPerShellMB < 1024 (мало памяти)
- MaxShellsPerUser < 25 (мало shells)

---

### 2.3. Проверка логов ошибок WinRM

```powershell
Get-WinEvent -LogName Microsoft-Windows-WinRM/Operational -MaxEvents 20 |
  Where-Object {$_.LevelDisplayName -eq "Error"} |
  Format-Table TimeCreated, Message -AutoSize
```

Это покажет последние ошибки WinRM. Ищите:
- "Quota violation" - превышены лимиты
- "Access denied" - проблема с правами
- "The WS-Management service cannot process the request" - проблема конфигурации

---

### 2.4. Тест локального подключения

```powershell
Test-WSMan -ComputerName localhost
```

**Ожидается:** Должно вернуть информацию о WinRM без ошибок

Если ошибка:
```powershell
# Включить WinRM заново
Enable-PSRemoting -Force
winrm quickconfig -q
```

---

## ШАГ 3: Исправление

### 3.1. Увеличить лимиты WinRM

```powershell
# Увеличить память на shell
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="2048"}'

# Увеличить количество shells
winrm set winrm/config/winrs '@{MaxShellsPerUser="50"}'

# Увеличить concurrent операции
winrm set winrm/config/winrs '@{MaxConcurrentOperationsPerUser="1500"}'
```

---

### 3.2. Очистить активные shells (если есть)

```powershell
# Посмотреть активные сессии
Get-PSSession

# Удалить все
Get-PSSession | Remove-PSSession

# Или удалить зависшие WinRM процессы
Get-Process -Name wsmprovhost -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

### 3.3. Проверить Execution Policy

```powershell
Get-ExecutionPolicy
```

**Должно быть:** `RemoteSigned` или `Unrestricted`

Если `Restricted`:
```powershell
Set-ExecutionPolicy RemoteSigned -Force
```

---

### 3.4. Проверить AllowUnencrypted

```powershell
winrm get winrm/config/service
```

Найдите строку `AllowUnencrypted`. **Должно быть:** `true`

Если `false`:
```powershell
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
```

---

### 3.5. Перезапустить WinRM

```powershell
Restart-Service WinRM
```

---

## ШАГ 4: Проверка результата

### 4.1. Тест на самом сервере

```powershell
Test-WSMan -ComputerName localhost
```

Должно работать без ошибок.

---

### 4.2. Тест с другого Windows сервера

С любого работающего сервера выполните:

```powershell
Test-WSMan -ComputerName 89.124.71.240
```

Должно вернуть информацию о WinRM без ошибок.

---

### 4.3. Подождать проверки системы мониторинга

- Система проверяет серверы каждые **20 минут**
- Подождите следующий цикл
- Проверьте результат:

```bash
# На вашем компьютере
cd C:\Users\Admin\Documents\Cursor\Projects\ServerManager
python final_check.py
```

**Ожидается:** Ошибок должно стать меньше (было 10, станет 5 после исправления одного сервера)

---

## Типичные ошибки и решения

### Ошибка: "Quota violation"

**Причина:** Превышены лимиты MaxMemoryPerShellMB или MaxShellsPerUser

**Решение:**
```powershell
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="2048"}'
winrm set winrm/config/winrs '@{MaxShellsPerUser="50"}'
Restart-Service WinRM
```

---

### Ошибка: "Access is denied"

**Причина:** Недостаточно прав для удаленного управления

**Решение:**
```powershell
# Добавить Administrator в группу Remote Management Users
net localgroup "Remote Management Users" Administrator /add

# Перезапустить WinRM
Restart-Service WinRM
```

---

### Ошибка: "The client cannot connect"

**Причина:** TrustedHosts не настроен

**Решение:**
```powershell
winrm set winrm/config/client '@{TrustedHosts="*"}'
Restart-Service WinRM
```

---

## Если ничего не помогло

### Полная переустановка WinRM:

```powershell
# 1. Остановить WinRM
Stop-Service WinRM

# 2. Сбросить конфигурацию
winrm delete winrm/config/listener?Address=*+Transport=HTTP

# 3. Заново настроить
Enable-PSRemoting -Force
winrm quickconfig -force

# 4. Установить лимиты
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="2048"}'
winrm set winrm/config/winrs '@{MaxShellsPerUser="50"}'

# 5. Разрешить HTTP
winrm set winrm/config/service '@{AllowUnencrypted="true"}'

# 6. Запустить
Start-Service WinRM
```

---

## Массовое исправление (для всех 5 серверов)

После того как исправите ОДИН сервер и убедитесь что работает, можно исправить остальные:

### Вариант А: Вручную на каждом
Повторите ШАГ 1-4 для каждого из 5 серверов

### Вариант Б: Скриптом с одного сервера

Создайте на работающем сервере скрипт:

```powershell
# fix_all_servers.ps1
$servers = @(
    @{IP='89.124.71.240'; User='Administrator'; Pass='password222'},
    @{IP='89.124.72.242'; User='Administrator'; Pass='password222'},
    @{IP='91.201.113.127'; User='Administrator'; Pass='password222'},
    @{IP='62.84.101.97'; User='Administrator'; Pass='password222'},
    @{IP='5.35.32.68'; User='Administrator'; Pass='password222'}
)

foreach ($server in $servers) {
    Write-Host "Fixing $($server.IP)..." -ForegroundColor Yellow

    $cred = New-Object System.Management.Automation.PSCredential(
        "$($server.IP)\$($server.User)",
        (ConvertTo-SecureString $server.Pass -AsPlainText -Force)
    )

    try {
        Invoke-Command -ComputerName $server.IP -Credential $cred -ScriptBlock {
            # Увеличить лимиты
            winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="2048"}'
            winrm set winrm/config/winrs '@{MaxShellsPerUser="50"}'

            # Разрешить HTTP
            winrm set winrm/config/service '@{AllowUnencrypted="true"}'

            # Перезапустить
            Restart-Service WinRM

            Write-Host "OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "Failed: $_" -ForegroundColor Red
    }
}
```

**НО**: Это сработает только если WinRM хотя бы частично работает!

---

## Checklist

- [ ] Подключиться к проблемному серверу (RDP/AnyDesk)
- [ ] Открыть PowerShell от администратора
- [ ] Проверить `Get-Service WinRM`
- [ ] Выполнить `winrm get winrm/config/winrs`
- [ ] Увеличить MaxMemoryPerShellMB до 2048
- [ ] Увеличить MaxShellsPerUser до 50
- [ ] Проверить AllowUnencrypted = true
- [ ] Выполнить `Restart-Service WinRM`
- [ ] Протестировать `Test-WSMan -ComputerName localhost`
- [ ] Подождать 20 минут
- [ ] Проверить `python final_check.py`

---

**Время на исправление:** 5-10 минут на один сервер
**Ожидаемый результат:** HTTP 500 исчезнет, сервер вернется в работу
