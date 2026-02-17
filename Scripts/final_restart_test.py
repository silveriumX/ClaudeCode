#!/usr/bin/env python3
"""
Финальный тест: полный перезапуск Proxifier и проверка
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

def ssh(cmd, timeout=60):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(os.getenv("VPS_WIN_HOST"), username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=10, look_for_keys=False)
        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
        return o.read().decode('utf-8', errors='ignore').strip()
    except Exception as e:
        return f"ERROR: {e}"


print("="*70)
print("🔄 ФИНАЛЬНЫЙ ТЕСТ PROXIFIER")
print("="*70)

# 1. Убить Proxifier
print("\n📋 Шаг 1: Полная остановка")
print(ssh(r'''
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
taskkill /IM Proxifier.exe /F 2>$null | Out-Null
Start-Sleep 2
Write-Output "DONE"
'''))

# 2. Запустить и подождать
print("\n📋 Шаг 2: Запуск через InteractiveToken")
print(ssh(r'''
$exe = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$taskName = "StartProxFinal"

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals><Principal><UserId>Administrator</UserId><LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><AllowStartOnDemand>true</AllowStartOnDemand><ExecutionTimeLimit>PT0S</ExecutionTimeLimit></Settings>
  <Actions><Exec><Command>$exe</Command></Exec></Actions>
</Task>
"@

[IO.File]::WriteAllText("$env:TEMP\proxfinal.xml", $xml, [System.Text.Encoding]::Unicode)
schtasks /Create /TN $taskName /XML "$env:TEMP\proxfinal.xml" /F 2>&1 | Out-Null
schtasks /Run /TN $taskName 2>&1 | Out-Null

Start-Sleep 8

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STARTED: PID=$($proc.Id) Session=$($proc.SessionId) Handle=$($proc.MainWindowHandle)"
} else {
    Write-Output "FAILED: Not running"
}
'''))

# 3. Ждём полной инициализации
print("\n⏱️  Ожидание 15 секунд для инициализации...")
time.sleep(15)

# 4. Проверка
print("\n📋 Шаг 3: Комплексная проверка")
result = ssh(r'''
Write-Output "=== Process Status ==="
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PID: $($proc.Id)"
    Write-Output "Session: $($proc.SessionId)"
    Write-Output "Handle: $($proc.MainWindowHandle)"
    Write-Output "Title: $($proc.MainWindowTitle)"
} else {
    Write-Output "NOT RUNNING"
}

Write-Output ""
Write-Output "=== IP Check (SSH session) ==="
$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "IP: $ip"

Write-Output ""
Write-Output "=== Connections to Proxy ==="
$conn = Get-NetTCPConnection -RemoteAddress {os.getenv("PROXY_HOST")} -ErrorAction SilentlyContinue | Where-Object {$_.State -eq 'Established'}
Write-Output "Established: $($conn.Count)"

Write-Output ""
Write-Output "=== Profile Check ==="
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
if (Test-Path $profilePath) {
    $content = Get-Content $profilePath -Raw
    if ($content -match '<Port>(\d+)</Port>') {
        Write-Output "Profile Port: $($Matches[1])"
    }
}
''')
print(result)

# 5. Тест в интерактивной сессии
print("\n📋 Шаг 4: Тест IP в интерактивной сессии")

# Создаём скрипт
ssh(r'''
$s = '$ip = curl.exe -s --max-time 10 https://api.ipify.org; $ip | Out-File C:\ProxifierAgent\ip.txt -Force'
$s | Out-File C:\ProxifierAgent\testip.ps1 -Encoding utf8 -Force
Remove-Item C:\ProxifierAgent\ip.txt -Force -ErrorAction SilentlyContinue
''')

# Запускаем
ssh(r'''
$tn = "IPTest"
schtasks /Delete /TN $tn /F 2>&1 | Out-Null
$x = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals><Principal><UserId>Administrator</UserId><LogonType>InteractiveToken</LogonType></Principal></Principals>
  <Settings><AllowStartOnDemand>true</AllowStartOnDemand></Settings>
  <Actions><Exec><Command>powershell.exe</Command><Arguments>-ExecutionPolicy Bypass -File C:\ProxifierAgent\testip.ps1</Arguments></Exec></Actions>
</Task>
"@
[IO.File]::WriteAllText("$env:TEMP\iptest.xml", $x, [System.Text.Encoding]::Unicode)
schtasks /Create /TN $tn /XML "$env:TEMP\iptest.xml" /F 2>&1 | Out-Null
schtasks /Run /TN $tn 2>&1 | Out-Null
''')

time.sleep(12)

result = ssh(r'''
schtasks /Delete /TN "IPTest" /F 2>&1 | Out-Null
$f = "C:\ProxifierAgent\ip.txt"
if (Test-Path $f) {
    $ip = Get-Content $f
    Write-Output "IP in interactive session: $ip"

    if ($ip -and $ip -ne "62.84.101.97") {
        Write-Output ""
        Write-Output "========================================"
        Write-Output "SUCCESS! PROXY IS WORKING!"
        Write-Output "========================================"
    } else {
        Write-Output ""
        Write-Output "========================================"
        Write-Output "PROXY NOT WORKING"
        Write-Output "========================================"
    }
} else {
    Write-Output "ERROR: No result file"
}
''')
print(result)

print("\n" + "="*70)
print("""
📊 ИТОГОВЫЙ АНАЛИЗ:

Если IP = 62.84.101.97 в обоих случаях:
→ Proxifier не перехватывает трафик

Возможные причины:
1. Proxifier минимизирован и не активен
2. Нужно вручную загрузить профиль через GUI
3. Есть какое-то модальное окно блокирующее работу

РЕКОМЕНДАЦИЯ:
Подключиться по RDP к серверу и проверить состояние Proxifier визуально.
""")
