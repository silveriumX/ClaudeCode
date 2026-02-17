#!/usr/bin/env python3
"""
Перезапуск Proxifier с явным профилем
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

def ssh(cmd, timeout=30):
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
print("🔄 ПЕРЕЗАПУСК PROXIFIER С ПРОФИЛЕМ")
print("="*70)

# 1. Убить все процессы Proxifier
print("\n📋 Шаг 1: Полная остановка Proxifier")
print(ssh(r'''
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
taskkill /IM Proxifier.exe /F 2>$null
Start-Sleep 3

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "WARNING:Still running"
} else {
    Write-Output "STOPPED:OK"
}
'''))

# 2. Запустить с профилем как аргументом
print("\n📋 Шаг 2: Запуск с профилем как аргументом")
result = ssh(r'''
$exe = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$profile = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"

$taskName = "ProxWithProfile"
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

# Задача запуска Proxifier с профилем
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals>
    <Principal>
      <UserId>Administrator</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec>
      <Command>$exe</Command>
      <Arguments>"$profile"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\ProxWithProfile.xml"
[IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)

schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
$result = schtasks /Run /TN $taskName 2>&1
Write-Output "RUN:$result"

Start-Sleep 6

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STARTED:PID=$($proc.Id)"
    Write-Output "MainWindowHandle:$($proc.MainWindowHandle)"
} else {
    Write-Output "FAILED"
}

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
''')
print(result)

# 3. Ждём
print("\n⏱️  Ожидание 10 секунд...")
time.sleep(10)

# 4. Проверка
print("\n📋 Шаг 3: Проверка состояния")
print(ssh(r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS: PID=$($proc.Id), HasWindow=$($proc.MainWindowHandle -ne 0)"
} else {
    Write-Output "PROCESS: Not running"
}

# IP через SSH сессию
$ip = curl.exe -s --max-time 5 https://api.ipify.org 2>$null
Write-Output "IP_SSH: $ip"
'''))

# 5. Тест в интерактивной сессии
print("\n📋 Шаг 4: Тест IP в интерактивной сессии")

# Создаём скрипт
ssh(r'''
$script = '$ip = curl.exe -s --max-time 10 https://api.ipify.org; $ip | Out-File C:\ProxifierAgent\ip_result.txt -Force'
$script | Out-File C:\ProxifierAgent\test_ip.ps1 -Encoding utf8 -Force
Remove-Item C:\ProxifierAgent\ip_result.txt -Force -ErrorAction SilentlyContinue
''')

# Запускаем в интерактивной сессии
ssh(r'''
$taskName = "TestIPSession"
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals><Principal><UserId>Administrator</UserId><LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><AllowStartOnDemand>true</AllowStartOnDemand></Settings>
  <Actions><Exec><Command>powershell.exe</Command><Arguments>-ExecutionPolicy Bypass -File C:\ProxifierAgent\test_ip.ps1</Arguments></Exec></Actions>
</Task>
"@
$xmlPath = "$env:TEMP\TestIPSess.xml"
[IO.File]::WriteAllText($xmlPath, $xml, [System.Text.Encoding]::Unicode)
schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
schtasks /Run /TN $taskName 2>&1 | Out-Null
''')

time.sleep(8)

result = ssh(r'''
schtasks /Delete /TN "TestIPSession" /F 2>&1 | Out-Null
$file = "C:\ProxifierAgent\ip_result.txt"
if (Test-Path $file) {
    $ip = Get-Content $file
    Write-Output "IP_INTERACTIVE: $ip"

    if ($ip -and $ip -ne "62.84.101.97") {
        Write-Output "============================================"
        Write-Output "SUCCESS! PROXY WORKING!"
        Write-Output "============================================"
    } else {
        Write-Output "============================================"
        Write-Output "FAILED: Proxy not working"
        Write-Output "============================================"
    }
} else {
    Write-Output "ERROR: Result file not created"
}
''')
print(result)

print("\n" + "="*70)
