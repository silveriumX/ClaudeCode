#!/usr/bin/env python3
"""
Тест: запустить curl в той же сессии что и Proxifier (через Task Scheduler)
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
print("🔬 ТЕСТ: CURL В ТОЙ ЖЕ СЕССИИ ЧТО И PROXIFIER")
print("="*70)

# Создаём скрипт который запустится в интерактивной сессии
print("\n📋 Создаём тестовый скрипт...")

create_script = r'''
$scriptPath = "C:\ProxifierAgent\test_ip.ps1"
$script = @"
`$ip = curl.exe -s --max-time 10 https://api.ipify.org
`$ip | Out-File -FilePath "C:\ProxifierAgent\result.txt" -Force
"@

$script | Out-File -FilePath $scriptPath -Encoding utf8 -Force
Write-Output "SCRIPT_CREATED:$scriptPath"
'''
print(ssh(create_script))

# Удалим старый результат
print("\n📋 Удаляем старый результат...")
print(ssh(r'Remove-Item "C:\ProxifierAgent\result.txt" -Force -ErrorAction SilentlyContinue; Write-Output "OK"'))

# Запускаем скрипт в интерактивной сессии
print("\n📋 Запускаем curl в интерактивной сессии (Session 2)...")

run_in_session = r'''
$taskName = "TestIPInSession"
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

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
  </Settings>
  <Actions>
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -File "C:\ProxifierAgent\test_ip.ps1"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\TestIP.xml"
[IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)

schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
$runResult = schtasks /Run /TN $taskName 2>&1
Write-Output "RUN:$runResult"

# Ждём выполнения
Start-Sleep 8

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue

Write-Output "TASK_COMPLETED"
'''
print(ssh(run_in_session))

# Читаем результат
print("\n📋 Читаем результат...")
time.sleep(2)

result = ssh(r'''
$resultFile = "C:\ProxifierAgent\result.txt"
if (Test-Path $resultFile) {
    $ip = Get-Content $resultFile
    Write-Output "IP_IN_SESSION:$ip"

    if ($ip -eq "62.84.101.97") {
        Write-Output "CONCLUSION:Proxifier NOT working even in same session"
    } else {
        Write-Output "CONCLUSION:SUCCESS! Proxifier works in interactive session!"
    }
} else {
    Write-Output "ERROR:Result file not found"
}
''')
print(result)

# Сравнение
print("\n📋 Для сравнения - curl через SSH (другая сессия):")
print(ssh('$ip = curl.exe -s --max-time 5 https://api.ipify.org; Write-Output "IP_SSH_SESSION:$ip"'))

print("\n" + "="*70)
print("📊 ВЫВОДЫ:")
print("="*70)
print("""
Если IP_IN_SESSION отличается от 62.84.101.97 → Proxifier работает!
Проблема: SSH сессия не перехватывается Proxifier.

Если IP_IN_SESSION = 62.84.101.97 → Proxifier не работает даже в своей сессии.
""")
