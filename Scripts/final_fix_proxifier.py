#!/usr/bin/env python3
"""
Финальное исправление: обновить реквизиты прокси на рабочий порт 10004
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

# Используем РАБОЧИЙ порт 10004 (не 10010!)
PROXY_ADDRESS = os.getenv("PROXY_HOST")
PROXY_PORT = 10004
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
print("✅ ОБНОВЛЕНИЕ PROXIFIER С РАБОЧИМ ПОРТОМ 10004")
print("="*80)

# 1. Проверка доступности порта 10004
print(f"\n📋 Проверка доступности {PROXY_ADDRESS}:{PROXY_PORT}")

check_cmd = f'''
$result = Test-NetConnection -ComputerName {PROXY_ADDRESS} -Port {PROXY_PORT} -WarningAction SilentlyContinue
Write-Output "TCP_TEST:$($result.TcpTestSucceeded)"
'''

result = execute_ssh(check_cmd)
print(result)

if "TCP_TEST:False" in result:
    print("⚠️ Порт 10004 тоже недоступен! Прокси может не работать.")

# 2. Обновить профиль
print(f"\n📝 Обновление профиля с портом {PROXY_PORT}")

update_cmd = f'''
$profilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"
$backupPath = "$profilePath.backup_final_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $profilePath $backupPath -Force
Write-Output "BACKUP:$backupPath"

$content = [IO.File]::ReadAllText($profilePath)

# Найти существующий Proxy с id="101" и обновить его
if ($content -match '<Proxy id="101".*?</Proxy>') {{
    # Заменить весь блок прокси
    $newProxy = @"
<Proxy id="101" type="SOCKS5">
			<Authentication enabled="true">
				<Username>{PROXY_USER}</Username>
				<Password>{PROXY_PASS}</Password>
			</Authentication>
			<Options>16</Options>
			<Port>{PROXY_PORT}</Port>
			<Address>{PROXY_ADDRESS}</Address>
		</Proxy>
"@
    $content = $content -replace '<Proxy id="101".*?</Proxy>', $newProxy
    Write-Output "UPDATED:Proxy id=101 updated"
}} else {{
    Write-Output "WARNING:Proxy id=101 not found, adding new"
    $newProxy = '<Proxy id="101" type="SOCKS5"><Authentication enabled="true"><Username>{PROXY_USER}</Username><Password>{PROXY_PASS}</Password></Authentication><Options>16</Options><Port>{PROXY_PORT}</Port><Address>{PROXY_ADDRESS}</Address></Proxy>'
    $content = $content -replace '</ProxyList>', "$newProxy</ProxyList>"
}}

$encoding = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($profilePath, $content, $encoding)
Write-Output "FILE_WRITTEN:Profile updated"

# Проверка
$newContent = [IO.File]::ReadAllText($profilePath)
if ($newContent -match '<Port>{PROXY_PORT}</Port>' -and $newContent -match '<Username>{PROXY_USER}</Username>') {{
    Write-Output "VERIFIED:Profile contains correct port and username"
}} else {{
    Write-Output "ERROR:Verification failed"
}}
'''

result = execute_ssh(update_cmd)
print(result)

# 3. Перезапустить Proxifier
print("\n🔄 Перезапуск Proxifier")

restart_cmd = r'''
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$taskName = "RestartProx_$(Get-Date -Format 'HHmmss')"
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
    Write-Output "STARTED:PID=$($proc.Id)"
} else {
    Write-Output "ERROR:Not started"
}

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''

result = execute_ssh(restart_cmd)
print(result)

# 4. Проверка через 5 секунд
print("\n⏱️ Ждём 5 секунд...")
time.sleep(5)

print("\n🔍 Финальная проверка")

final_cmd = r'''
# Процесс
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:Running (PID=$($proc.Id), Session=$($proc.SessionId))"
} else {
    Write-Output "PROCESS:Not running"
}

# IP через curl (с прокси должен отличаться от 62.84.101.97)
try {
    $directIp = "62.84.101.97"
    $ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
    if ($ip) {
        if ($ip -eq $directIp) {
            Write-Output "EXTERNAL_IP:$ip (WARNING: Same as server IP - proxy not working?)"
        } else {
            Write-Output "EXTERNAL_IP:$ip (SUCCESS: Different from server IP)"
        }
    } else {
        Write-Output "IP_CHECK:No response"
    }
} catch {
    Write-Output "IP_CHECK:Error"
}

# Профиль
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)
if ($content -match '<Username>(.*?)</Username>') {
    Write-Output "PROFILE_USER:$($Matches[1])"
}
if ($content -match '<Port>(\d+)</Port>') {
    Write-Output "PROFILE_PORT:$($Matches[1])"
}
'''

result = execute_ssh(final_cmd)
print(result)

print("\n" + "="*80)
print(f"✅ Профиль обновлён на {PROXY_ADDRESS}:{PROXY_PORT}")
print("="*80)
