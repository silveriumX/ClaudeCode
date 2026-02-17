#!/usr/bin/env python3
"""
Решение: Запуск Proxifier в активной пользовательской сессии
Используем PsExec или Task Scheduler с правильным пользователем
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

# Новые реквизиты прокси
PROXY_ADDRESS = os.getenv("PROXY_HOST")
PROXY_PORT = 10010
PROXY_USER = "1fb08611c4d557ac8f22_c_US_s_Hub62"
PROXY_PASS = "n2yhff6z7fC1VBBKi8QvoGeSr9LYm5Li"


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
print("✅ ПРАВИЛЬНЫЙ ЗАПУСК PROXIFIER В ПОЛЬЗОВАТЕЛЬСКОЙ СЕССИИ")
print("="*80)

# Шаг 1: Обновить профиль с новым портом
print("\n📝 Шаг 1: Обновление профиля прокси (порт 10010)")

update_profile_cmd = f'''
$profilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"
if (!(Test-Path $profilePath)) {{
    Write-Output "ERROR:Profile not found"
    exit 1
}}

# Бэкап
$backupPath = "$profilePath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $profilePath $backupPath -Force
Write-Output "BACKUP:$backupPath"

# Обновить прокси
$content = [IO.File]::ReadAllText($profilePath)
$newProxyList = '<ProxyList><Proxy id="100" type="SOCKS5"><Address>{PROXY_ADDRESS}</Address><Port>{PROXY_PORT}</Port><Options>0</Options><Authentication enabled="true"><Username>{PROXY_USER}</Username><Password>{PROXY_PASS}</Password></Authentication></Proxy></ProxyList>'

if ($content -match '<ProxyList>.*?</ProxyList>') {{
    $content = $content -replace '<ProxyList>.*?</ProxyList>', $newProxyList
    Write-Output "UPDATED:ProxyList replaced"
}} else {{
    $content = $content -replace '</ProxifierProfile>', "$newProxyList`n</ProxifierProfile>"
    Write-Output "ADDED:ProxyList added"
}}

$encoding = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($profilePath, $content, $encoding)

# Проверить
$newContent = [IO.File]::ReadAllText($profilePath)
if ($newContent -match '<Port>{PROXY_PORT}</Port>') {{
    Write-Output "VERIFIED:Port {PROXY_PORT} in profile"
}} else {{
    Write-Output "ERROR:Port not updated"
}}
'''

result = execute_ssh(update_profile_cmd)
print(result)

if "ERROR:" in result:
    print("\n❌ Не удалось обновить профиль!")
    sys.exit(1)

# Шаг 2: Остановить старый Proxifier
print("\n🛑 Шаг 2: Остановка Proxifier (если запущен)")

stop_cmd = r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Stop-Process -Name Proxifier -Force
    Write-Output "STOPPED:Proxifier terminated"
    Start-Sleep -Seconds 2
} else {
    Write-Output "NOT_RUNNING:No Proxifier process found"
}
'''

result = execute_ssh(stop_cmd)
print(result)

# Шаг 3: Запустить Proxifier в пользовательской сессии
print("\n🚀 Шаг 3: Запуск Proxifier в активной RDP-сессии")

start_in_session_cmd = r'''
# Найти ID активной сессии пользователя
$sessionId = (query user administrator | Select-String "Active" | ForEach-Object {$_ -split '\s+' | Select-Object -Index 2})

if ($sessionId) {
    Write-Output "SESSION_ID:$sessionId"

    $exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"

    # Метод 1: Task Scheduler с правильным пользователем
    $taskName = "LaunchProxifierUserSession"
    schtasks /Delete /TN $taskName /F 2>$null | Out-Null

    # Создать задачу от имени текущего пользователя
    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers></Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>administrator</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$exePath</Command>
    </Exec>
  </Actions>
</Task>
"@

    $xmlPath = "$env:TEMP\proxifier_task.xml"
    [IO.File]::WriteAllText($xmlPath, $xml)

    $createResult = schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1
    Write-Output "TASK_CREATE:$createResult"

    $runResult = schtasks /Run /TN $taskName 2>&1
    Write-Output "TASK_RUN:$runResult"

    Start-Sleep -Seconds 3

    # Проверить
    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "SUCCESS:Proxifier running (PID=$($proc.Id), Session=$($proc.SessionId))"
    } else {
        Write-Output "FAILED:Proxifier not in process list"
    }

    # Cleanup
    schtasks /Delete /TN $taskName /F 2>$null | Out-Null
    Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue

} else {
    Write-Output "ERROR:Could not find active user session"
}
'''

result = execute_ssh(start_in_session_cmd)
print(result)

# Шаг 4: Проверка через 5 секунд
print("\n⏱️ Ждём 5 секунд...")
time.sleep(5)

print("\n🔍 Шаг 4: Финальная проверка")

final_check_cmd = r'''
# Процесс
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:Running (PID=$($proc.Id), Session=$($proc.SessionId), Memory=$([math]::Round($proc.WorkingSet64/1MB,2))MB)"
} else {
    Write-Output "PROCESS:Not running"
}

# Профиль
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)
if ($content -match '<Port>(\d+)</Port>') {
    Write-Output "PROFILE_PORT:$($Matches[1])"
}

# IP (через прокси должен показать IP прокси, а не сервера)
try {
    $ip = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing -TimeoutSec 10).Content
    Write-Output "CURRENT_IP:$ip"
} catch {
    Write-Output "IP_CHECK:Failed - $($_.Exception.Message)"
}
'''

result = execute_ssh(final_check_cmd)
print(result)

print("\n" + "="*80)
print("✅ ПРОЦЕСС ЗАВЕРШЁН")
print("="*80)
