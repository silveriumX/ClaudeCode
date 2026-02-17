#!/usr/bin/env python3
"""
Проверка профиля и перезапуск для применения изменений
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

PROXY_PORT = 10010


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
print("🔍 ПРОВЕРКА И ПЕРЕЗАПУСК PROXIFIER С НОВЫМ ПОРТОМ")
print("="*80)

# 1. Проверить текущий профиль
print("\n📋 Шаг 1: Чтение текущего профиля")

check_profile_cmd = r'''
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)

# Найти все порты в файле
$ports = [regex]::Matches($content, '<Port>(\d+)</Port>') | ForEach-Object { $_.Groups[1].Value }
Write-Output "PORTS_IN_FILE:$($ports -join ', ')"

# Показать фрагмент ProxyList
if ($content -match '<ProxyList>(.*?)</ProxyList>') {
    $proxyListContent = $Matches[1]
    Write-Output "PROXYLIST_FRAGMENT:$($proxyListContent.Substring(0, [Math]::Min(300, $proxyListContent.Length)))"
}
'''

result = execute_ssh(check_profile_cmd)
print(result)

# 2. Принудительно обновить профиль (полная перезапись нужной секции)
print(f"\n📝 Шаг 2: Принудительное обновление на порт {PROXY_PORT}")

force_update_cmd = f'''
$profilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)

# Найти и удалить все ProxyList
$content = $content -replace '<ProxyList>.*?</ProxyList>', ''
$content = $content -replace '<ProxyList\\s*/>', ''

# Вставить новый ProxyList с правильным портом
$newProxyList = '<ProxyList><Proxy id="100" type="SOCKS5"><Address>{os.getenv("PROXY_HOST")}</Address><Port>{PROXY_PORT}</Port><Options>0</Options><Authentication enabled="true"><Username>1fb08611c4d557ac8f22_c_US_s_Hub62</Username><Password>n2yhff6z7fC1VBBKi8QvoGeSr9LYm5Li</Password></Authentication></Proxy></ProxyList>'

$content = $content -replace '</ProxifierProfile>', "$newProxyList`n</ProxifierProfile>"

$encoding = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($profilePath, $content, $encoding)

# Проверить
$newContent = [IO.File]::ReadAllText($profilePath)
if ($newContent -match '<Port>{PROXY_PORT}</Port>') {{
    Write-Output "SUCCESS:Port {PROXY_PORT} confirmed in profile"
}} else {{
    Write-Output "ERROR:Port {PROXY_PORT} not found after update"
}}

# Показать все порты
$ports = [regex]::Matches($newContent, '<Port>(\d+)</Port>') | ForEach-Object {{ $_.Groups[1].Value }}
Write-Output "ALL_PORTS:$($ports -join ', ')"
'''

result = execute_ssh(force_update_cmd)
print(result)

# 3. Перезапустить Proxifier
print("\n🔄 Шаг 3: Перезапуск Proxifier для применения изменений")

restart_cmd = r'''
# Остановить
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Output "STOPPED:Proxifier terminated"

# Найти активную сессию
$sessionId = (query user administrator | Select-String "Active" | ForEach-Object {$_ -split '\s+' | Select-Object -Index 2})

# Запустить
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$taskName = "RestartProxifier_$(Get-Date -Format 'HHmmss')"
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
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
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
Start-Sleep -Seconds 3

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STARTED:PID=$($proc.Id), Session=$($proc.SessionId)"
} else {
    Write-Output "ERROR:Proxifier not started"
}

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''

result = execute_ssh(restart_cmd)
print(result)

# 4. Проверка через 3 секунды
print("\n⏱️ Ждём 3 секунды для инициализации...")
time.sleep(3)

print("\n🔍 Шаг 4: Финальная проверка статуса")

final_cmd = r'''
# Процесс
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:Running (PID=$($proc.Id), Session=$($proc.SessionId))"
} else {
    Write-Output "PROCESS:Not running"
}

# Профиль
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)
if ($content -match '<Port>(\d+)</Port>') {
    Write-Output "PROFILE_PORT:$($Matches[1])"
}

# IP (чуть больше таймаут)
try {
    $ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
    if ($ip) {
        Write-Output "EXTERNAL_IP:$ip"
    } else {
        Write-Output "IP_CHECK:No response from api.ipify.org"
    }
} catch {
    Write-Output "IP_CHECK:Error - $($_.Exception.Message)"
}
'''

result = execute_ssh(final_cmd)
print(result)

print("\n" + "="*80)
print(f"✅ Proxifier перезапущен с портом {PROXY_PORT}")
print("="*80)
