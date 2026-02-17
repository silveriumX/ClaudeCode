# План миграции с Proxifier на ProxiFyre

**Дата:** 02.02.2026
**Цель:** Заменить Proxifier на ProxiFyre для полного CLI управления через SSH

---

## Почему ProxiFyre?

| Функция | Proxifier | ProxiFyre |
|---------|-----------|-----------|
| CLI управление | ❌ | ✅ |
| Windows Service | ❌ | ✅ |
| Конфиг файл | XML + GUI | JSON |
| Per-app routing | ✅ | ✅ |
| SOCKS5 + Auth | ✅ | ✅ |
| UDP/QUIC | ✅ | ✅ |
| Exclusions | ~ | ✅ |
| LAN bypass | ~ | ✅ |
| Управление через SSH | ❌ | ✅ |

---

## ProxiFyre: Быстрый старт

### Установка

1. **Скачать WinpkFilter драйвер:**
   - https://github.com/wiresock/ndisapi/releases
   - Установить драйвер (требует перезагрузку)

2. **Скачать ProxiFyre:**
   - https://github.com/wiresock/proxifyre/releases
   - Распаковать в `C:\ProxiFyre\`

3. **Установить Visual C++ Runtime:**
   - https://aka.ms/vs/17/release/vc_redist.x64.exe

### Конфигурация

Создать `C:\ProxiFyre\app-config.json`:

```json
{
    "logLevel": "Info",
    "bypassLan": true,
    "proxies": [
        {
            "appNames": [""],
            "socks5ProxyEndpoint": "185.162.130.86:10001",
            "username": "0tQfV66IulPiKVJRG6gm",
            "password": "0zOrPGFjDQcrqMT0Dq3Et5T8kz6jhseA",
            "supportedProtocols": ["TCP", "UDP"]
        }
    ],
    "excludes": [
        "ProxiFyre.exe",
        "svchost.exe"
    ]
}
```

**Параметры:**
- `appNames: [""]` — пустая строка = все приложения
- `bypassLan: true` — локальный трафик не через прокси
- `excludes` — приложения которые НЕ идут через прокси

### Управление через CLI

```powershell
# Установить как Windows Service
ProxiFyre.exe install

# Запустить сервис
ProxiFyre.exe start

# Остановить
ProxiFyre.exe stop

# Удалить сервис
ProxiFyre.exe uninstall

# Запустить в консоли (для отладки)
ProxiFyre.exe
```

### Управление через SSH

```powershell
# Проверить статус сервиса
Get-Service ProxiFyre

# Остановить
Stop-Service ProxiFyre

# Запустить
Start-Service ProxiFyre

# Перезапустить
Restart-Service ProxiFyre
```

---

## Скрипт для управления через SSH

### ProxiFyreAgent.ps1

```powershell
param(
    [string]$Action = "status",
    [string]$ProxyHost = "",
    [string]$ProxyPort = "",
    [string]$ProxyUser = "",
    [string]$ProxyPass = ""
)

$ProxiFyreDir = "C:\ProxiFyre"
$ConfigPath = "$ProxiFyreDir\app-config.json"
$ExePath = "$ProxiFyreDir\ProxiFyre.exe"

switch ($Action) {
    "status" {
        $svc = Get-Service ProxiFyre -ErrorAction SilentlyContinue
        if ($svc) {
            Write-Output "SERVICE:$($svc.Status)"
        } else {
            Write-Output "SERVICE:NotInstalled"
        }

        $ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
        Write-Output "IP:$ip"
    }

    "set_proxy" {
        # Создать новый конфиг
        $config = @{
            logLevel = "Info"
            bypassLan = $true
            proxies = @(
                @{
                    appNames = @("")
                    socks5ProxyEndpoint = "${ProxyHost}:${ProxyPort}"
                    username = $ProxyUser
                    password = $ProxyPass
                    supportedProtocols = @("TCP", "UDP")
                }
            )
            excludes = @("ProxiFyre.exe", "svchost.exe")
        }

        $config | ConvertTo-Json -Depth 5 | Out-File $ConfigPath -Encoding utf8

        # Перезапустить сервис
        Restart-Service ProxiFyre -ErrorAction SilentlyContinue
        Start-Sleep 3

        $ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
        Write-Output "CONFIG:Updated"
        Write-Output "IP:$ip"
    }

    "start" {
        Start-Service ProxiFyre
        Write-Output "STARTED"
    }

    "stop" {
        Stop-Service ProxiFyre
        Write-Output "STOPPED"
    }

    "restart" {
        Restart-Service ProxiFyre
        Start-Sleep 3
        $svc = Get-Service ProxiFyre
        Write-Output "STATUS:$($svc.Status)"
    }

    "install" {
        & $ExePath install
        & $ExePath start
        Write-Output "INSTALLED"
    }
}
```

---

## План миграции

### Этап 1: Установка ProxiFyre (на сервере)

1. Скачать и установить WinpkFilter:
```powershell
# Через SSH
Invoke-WebRequest -Uri "https://github.com/wiresock/ndisapi/releases/download/v3.6.0/ndisapi-3.6.0-x64.zip" -OutFile "$env:TEMP\ndisapi.zip"
Expand-Archive "$env:TEMP\ndisapi.zip" -DestinationPath "$env:TEMP\ndisapi"
Start-Process "$env:TEMP\ndisapi\ndisapi_setup.exe" -ArgumentList "/S" -Wait
```

2. Скачать ProxiFyre:
```powershell
Invoke-WebRequest -Uri "https://github.com/wiresock/proxifyre/releases/latest/download/ProxiFyre-x64.zip" -OutFile "$env:TEMP\proxifyre.zip"
Expand-Archive "$env:TEMP\proxifyre.zip" -DestinationPath "C:\ProxiFyre"
```

3. Создать конфиг и установить сервис:
```powershell
# Конфиг создаётся скриптом
C:\ProxiFyre\ProxiFyre.exe install
C:\ProxiFyre\ProxiFyre.exe start
```

### Этап 2: Удаление Proxifier

1. Остановить и удалить Proxifier:
```powershell
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
# Удалить через Control Panel или:
& "C:\Program Files (x86)\Proxifier\unins000.exe" /S
```

### Этап 3: Интеграция с ServerManager

Добавить команды в `command_handler.py`:
```python
elif command == 'proxifyre_status':
    return ssh_exec('Get-Service ProxiFyre | Select Status')

elif command == 'proxifyre_set_proxy':
    # Обновить конфиг и перезапустить
    ...
```

---

## Преимущества после миграции

| Операция | До (Proxifier) | После (ProxiFyre) |
|----------|----------------|-------------------|
| Сменить прокси | Требует RDP | 1 команда SSH |
| Перезапуск | Task Scheduler hack | `Restart-Service` |
| Статус | Не определить | `Get-Service` |
| Автозапуск | Ненадёжно | Windows Service |
| Конфигурация | GUI only | JSON файл |

---

## Следующие шаги

1. **Скачать и протестировать ProxiFyre** локально
2. **Установить на сервер** через SSH
3. **Удалить Proxifier**
4. **Интегрировать с системой управления серверами**
