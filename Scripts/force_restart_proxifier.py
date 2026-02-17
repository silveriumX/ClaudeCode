#!/usr/bin/env python3
"""
Принудительный перезапуск Proxifier с перезагрузкой профиля
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
print("🔄 ПРИНУДИТЕЛЬНЫЙ ПЕРЕЗАПУСК PROXIFIER")
print("="*80)

# Шаг 1: Полностью остановить Proxifier
print("\n📋 Шаг 1: Остановка Proxifier")

stop_cmd = r'''
$procs = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($procs) {
    Write-Output "STOPPING:Найдено процессов: $($procs.Count)"
    Stop-Process -Name Proxifier -Force
    Start-Sleep -Seconds 3

    # Проверить что остановился
    $stillRunning = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($stillRunning) {
        Write-Output "WARNING:Всё ещё работает, принудительное завершение"
        taskkill /IM Proxifier.exe /F 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }

    Write-Output "STOPPED:✅ Остановлен"
} else {
    Write-Output "NOT_RUNNING:Уже остановлен"
}
'''

result = execute_ssh(stop_cmd)
print(result)

# Шаг 2: Проверить и очистить кеш/temp файлы Proxifier
print("\n📋 Шаг 2: Очистка временных файлов Proxifier")

clean_cmd = r'''
$tempPaths = @(
    "$env:TEMP\Proxifier*",
    "$env:APPDATA\Proxifier4\*.tmp",
    "$env:LOCALAPPDATA\Proxifier\*.tmp"
)

$cleaned = 0
foreach ($path in $tempPaths) {
    $files = Get-ChildItem $path -ErrorAction SilentlyContinue
    if ($files) {
        $files | Remove-Item -Force -ErrorAction SilentlyContinue
        $cleaned += $files.Count
    }
}

if ($cleaned -gt 0) {
    Write-Output "CLEANED:Удалено файлов: $cleaned"
} else {
    Write-Output "CLEANED:Временных файлов не найдено"
}
'''

result = execute_ssh(clean_cmd)
print(result)

# Шаг 3: Запустить Proxifier заново
print("\n📋 Шаг 3: Запуск Proxifier с чистого листа")

start_cmd = r'''
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"

# Создать задачу
$taskName = "RestartProxifierClean_$(Get-Date -Format 'HHmmss')"
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals>
    <Principal>
      <UserId>administrator</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
  </Settings>
  <Actions>
    <Exec>
      <Command>$exePath</Command>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\$taskName.xml"
[IO.File]::WriteAllText($xmlPath, $xml)

schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
schtasks /Run /TN $taskName 2>&1 | Out-Null

Write-Output "STARTING:Запуск Proxifier..."
Start-Sleep -Seconds 5

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STARTED:✅ PID=$($proc.Id), Session=$($proc.SessionId)"
} else {
    Write-Output "ERROR:Не запустился"
}

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''

result = execute_ssh(start_cmd)
print(result)

if "ERROR:" in result:
    print("\n❌ Не удалось запустить!")
    sys.exit(1)

# Шаг 4: Подождать инициализации
print("\n⏱️  Ждём 10 секунд для полной инициализации Proxifier...")
time.sleep(10)

# Шаг 5: Проверка IP
print("\n📋 Шаг 4: Проверка IP после перезапуска")

check_cmd = r'''
Write-Output "Проверка статуса..."
Write-Output ""

# 1. Процесс
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:✅ Работает (PID=$($proc.Id), Uptime=$([math]::Round(((Get-Date) - $proc.StartTime).TotalSeconds))s)"
} else {
    Write-Output "PROCESS:❌ Остановлен"
}

# 2. IP
Write-Output ""
Write-Output "Проверка внешнего IP..."
$ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null

if ($ip) {
    if ($ip -eq "62.84.101.97") {
        Write-Output "EXTERNAL_IP:$ip ❌ ПРОКСИ НЕ РАБОТАЕТ (IP сервера)"
    } else {
        Write-Output "EXTERNAL_IP:$ip ✅✅✅ ПРОКСИ РАБОТАЕТ!"
    }
} else {
    Write-Output "EXTERNAL_IP:Нет ответа"
}

# 3. Соединения к прокси
Write-Output ""
$connections = Get-NetTCPConnection -RemoteAddress {os.getenv("PROXY_HOST")} -ErrorAction SilentlyContinue | Where-Object {$_.State -eq 'Established'}
if ($connections) {
    Write-Output "CONNECTIONS:✅ $($connections.Count) активных к прокси-серверу"
} else {
    Write-Output "CONNECTIONS:❌ Нет активных соединений к {os.getenv("PROXY_HOST")}"
}

# 4. Профиль
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)
if ($content -match '<Port>(\d+)</Port>') {
    Write-Output "PROFILE_PORT:$($Matches[1])"
}
'''

result = execute_ssh(check_cmd)
print(result)

print("\n" + "="*80)
print("📊 РЕЗУЛЬТАТ")
print("="*80)

if "✅✅✅ ПРОКСИ РАБОТАЕТ!" in result:
    print("\n🎉 УСПЕХ! Proxifier теперь использует прокси!")
    print("IP изменился, трафик идёт через прокси-сервер")
elif "❌ ПРОКСИ НЕ РАБОТАЕТ" in result:
    print("\n⚠️ Proxifier всё ещё не применяет прокси")
    print("\nВозможные причины:")
    print("1. Proxifier не может подключиться к прокси (хотя curl может)")
    print("2. Rules в профиле настроены неправильно")
    print("3. Нужно настроить Proxifier вручную через GUI")
    print("\nРекомендация: подключиться по RDP и открыть Proxifier GUI,")
    print("проверить что прокси активен и правило Default использует его")
