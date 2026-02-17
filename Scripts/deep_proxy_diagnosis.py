#!/usr/bin/env python3
"""
Дополнительная диагностика: включить логирование Proxifier и проверить подключения
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64
import io
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

try:
    import paramiko
except ImportError:
    print("❌ Установите paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")


def execute_ssh(ps_command):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False, allow_agent=False)

        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=60)

        output = stdout.read().decode("utf-8", errors="ignore").strip()
        return output
    except Exception as e:
        return f"ERROR:{e}"
    finally:
        if client:
            client.close()


print("="*80)
print("🔍 УГЛУБЛЁННАЯ ДИАГНОСТИКА ПРОКСИ")
print("="*80)

# 1. Включить логирование в профиле
print("\n📋 Шаг 1: Включение логирования в Proxifier")

enable_logging_cmd = r'''
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)

# Добавить секцию Log если её нет
if ($content -notmatch '<Log>') {
    $logSection = @"
	<Log enabled="true">
		<LogFormat>2</LogFormat>
		<Filename></Filename>
		<DetectHttps>false</DetectHttps>
	</Log>
"@
    $content = $content -replace '</ProxifierProfile>', "$logSection`n</ProxifierProfile>"

    $encoding = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($profilePath, $content, $encoding)
    Write-Output "LOGGING_ENABLED:✅ Логирование включено"
} else {
    Write-Output "LOGGING:Уже включено или присутствует"
}
'''

result = execute_ssh(enable_logging_cmd)
print(result)

# 2. Перезапустить Proxifier для применения логирования
print("\n📋 Шаг 2: Перезапуск Proxifier")

restart_cmd = r'''
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$taskName = "RestartProxLog_$(Get-Date -Format 'HHmmss')"
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals><Principal><UserId>administrator</UserId><LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><AllowStartOnDemand>true</AllowStartOnDemand></Settings>
  <Actions><Exec><Command>$exePath</Command></Exec></Actions>
</Task>
"@
$xmlPath = "$env:TEMP\$taskName.xml"
[IO.File]::WriteAllText($xmlPath, $xml)
schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
schtasks /Run /TN $taskName 2>&1 | Out-Null
Start-Sleep -Seconds 3

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "RESTARTED:PID=$($proc.Id)"
} else {
    Write-Output "ERROR:Не запустился"
}

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''

result = execute_ssh(restart_cmd)
print(result)

time.sleep(3)

# 3. Тест подключения
print("\n📋 Шаг 3: Тест подключения к нескольким сайтам")

test_connections_cmd = r'''
Write-Output "Тестирование подключений..."
Write-Output ""

# 1. Google
try {
    $result = Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    Write-Output "GOOGLE:✅ Успех (код $($result.StatusCode))"
} catch {
    Write-Output "GOOGLE:❌ Ошибка - $($_.Exception.Message)"
}

# 2. IPify
try {
    $ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
    if ($ip) {
        Write-Output "IPIFY:✅ IP=$ip"
    } else {
        Write-Output "IPIFY:❌ Нет ответа"
    }
} catch {
    Write-Output "IPIFY:❌ Ошибка"
}

# 3. HTTPBin (для проверки прокси)
try {
    $result = Invoke-WebRequest -Uri "http://httpbin.org/ip" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    Write-Output "HTTPBIN:✅ Ответ: $($result.Content)"
} catch {
    Write-Output "HTTPBIN:❌ Ошибка"
}
'''

result = execute_ssh(test_connections_cmd)
print(result)

# 4. Проверить логи
print("\n📋 Шаг 4: Проверка логов Proxifier")

check_logs_cmd = r'''
Write-Output "Поиск и чтение логов..."
Write-Output ""

$logPaths = @(
    "$env:APPDATA\Proxifier4\Logs",
    "$env:APPDATA\Proxifier4",
    "$env:ProgramData\Proxifier\Logs",
    "C:\Program Files (x86)\Proxifier\Logs"
)

$found = $false
foreach ($path in $logPaths) {
    if (Test-Path $path) {
        $logs = Get-ChildItem $path -Filter "*.log" -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($logs) {
            Write-Output "LOG_FOUND:$($logs.FullName)"
            Write-Output "LOG_SIZE:$([math]::Round($logs.Length/1KB,2)) KB"
            Write-Output "LOG_MODIFIED:$($logs.LastWriteTime)"
            Write-Output ""
            Write-Output "=== ПОСЛЕДНИЕ 20 СТРОК ЛОГА ==="
            $content = Get-Content $logs.FullName -Tail 20 -ErrorAction SilentlyContinue
            if ($content) {
                $content | ForEach-Object { Write-Output $_ }
            }
            $found = $true
            break
        }
    }
}

if (-not $found) {
    Write-Output "LOG_STATUS:❌ Логи не найдены"
    Write-Output ""
    Write-Output "Возможные причины:"
    Write-Output "1. Логирование не активировано в GUI Proxifier"
    Write-Output "2. Нужно вручную включить через меню Profile -> Advanced -> Logging"
}
'''

result = execute_ssh(check_logs_cmd)
print(result)

# 5. Проверить активные соединения
print("\n📋 Шаг 5: Проверка активных сетевых соединений")

check_connections_cmd = r'''
Write-Output "Проверка соединений к прокси-серверу..."
$connections = Get-NetTCPConnection -RemoteAddress {os.getenv("PROXY_HOST")} -ErrorAction SilentlyContinue

if ($connections) {
    Write-Output "CONNECTIONS_FOUND:$($connections.Count) активных соединений к {os.getenv("PROXY_HOST")}"
    $connections | ForEach-Object {
        Write-Output "  RemotePort=$($_.RemotePort), State=$($_.State), OwningProcess=$($_.OwningProcess)"
    }
} else {
    Write-Output "CONNECTIONS:❌ Нет активных соединений к прокси-серверу"
    Write-Output "Это означает что Proxifier не использует прокси"
}
'''

result = execute_ssh(check_connections_cmd)
print(result)

print("\n" + "="*80)
print("📊 ЗАКЛЮЧЕНИЕ")
print("="*80)
print("\nЕсли нет соединений к {os.getenv("PROXY_HOST")} и IP не изменился:")
print("1. Возможно неправильные реквизиты (логин/пароль)")
print("2. Или прокси требует другой тип аутентификации")
print("3. Или нужно настроить Proxifier через GUI (Rules могут игнорироваться)")
