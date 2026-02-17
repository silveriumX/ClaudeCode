#!/usr/bin/env python3
"""
Исправленный агент с InteractiveToken
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64
import io
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = "10001"
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


def ssh(ps_command, timeout=90):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False, allow_agent=False)

        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)

        return stdout.read().decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"ERROR:{e}"
    finally:
        if client:
            client.close()


print("="*80)
print("🔧 ИСПРАВЛЕННЫЙ SET_PROXY С INTERACTIVETOKEN")
print("="*80)
print(f"\nПрокси: {PROXY_HOST}:{PROXY_PORT}")

# Шаг 1: Остановить Proxifier
print("\n📋 Шаг 1: Остановка Proxifier")
result = ssh(r'''
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
Start-Sleep 2
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "WARNING:Still running"
} else {
    Write-Output "STOPPED:OK"
}
''')
print(result)

# Шаг 2: Создать профиль
print("\n📋 Шаг 2: Создание профиля")
profile_cmd = f'''
$ProfilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"

# Бэкап
if (Test-Path $ProfilePath) {{
    Copy-Item $ProfilePath "$ProfilePath.bak" -Force
}}

# Новый профиль
$xml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxifierProfile version="102" platform="Windows" product_id="0" product_minver="400">
    <Options>
        <Resolve>
            <AutoModeDetection enabled="true"/>
            <ViaProxy enabled="false"/>
        </Resolve>
        <HttpProxiesSupport enabled="false"/>
    </Options>
    <ProxyList>
        <Proxy id="100" type="SOCKS5">
            <Address>{PROXY_HOST}</Address>
            <Port>{PROXY_PORT}</Port>
            <Options>0</Options>
            <Authentication enabled="true">
                <Username>{PROXY_USER}</Username>
                <Password>{PROXY_PASS}</Password>
            </Authentication>
        </Proxy>
    </ProxyList>
    <ChainList/>
    <RuleList>
        <Rule enabled="true">
            <Name>Localhost</Name>
            <Targets>localhost; 127.0.0.1; %ComputerName%</Targets>
            <Action type="Direct"/>
        </Rule>
        <Rule enabled="true">
            <Name>Default</Name>
            <Action type="Proxy">100</Action>
        </Rule>
    </RuleList>
</ProxifierProfile>
"@

$enc = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($ProfilePath, $xml, $enc)

if (Test-Path $ProfilePath) {{
    $size = (Get-Item $ProfilePath).Length
    Write-Output "PROFILE_CREATED:$size bytes"
}} else {{
    Write-Output "ERROR:Profile not created"
}}
'''
result = ssh(profile_cmd)
print(result)

# Шаг 3: Запустить с InteractiveToken
print("\n📋 Шаг 3: Запуск Proxifier в интерактивной сессии")
start_cmd = r'''
$ProxifierPath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$taskName = "ProxifierInteractive"

# Удалить старую задачу
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

# XML задачи с InteractiveToken
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers></Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>Administrator</UserId>
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
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$ProxifierPath</Command>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\ProxifierTask.xml"
[IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)

Write-Output "Creating task..."
$createResult = schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1
Write-Output "CREATE:$createResult"

Write-Output "Running task..."
$runResult = schtasks /Run /TN $taskName 2>&1
Write-Output "RUN:$runResult"

Start-Sleep -Seconds 6

# Проверить
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROXIFIER:RUNNING (PID=$($proc.Id), Session=$($proc.SessionId))"
} else {
    Write-Output "PROXIFIER:NOT_RUNNING"
}

# Cleanup
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''
result = ssh(start_cmd)
print(result)

# Шаг 4: Ждём и проверяем
print("\n⏱️  Ждём 10 секунд для инициализации...")
time.sleep(10)

# Шаг 5: Проверка IP
print("\n📋 Шаг 4: Проверка IP")
check_cmd = r'''
$serverIp = "62.84.101.97"

# Статус процесса
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:Running (PID=$($proc.Id), Session=$($proc.SessionId), Uptime=$([int]((Get-Date)-$proc.StartTime).TotalSeconds)s)"
} else {
    Write-Output "PROCESS:NOT_RUNNING"
}

# IP проверка
Write-Output ""
Write-Output "Checking IP..."
$ip = curl.exe -s --max-time 20 https://api.ipify.org 2>$null

if ($ip) {
    if ($ip -eq $serverIp) {
        Write-Output "EXTERNAL_IP:$ip"
        Write-Output "RESULT:PROXY_NOT_WORKING (still server IP)"
    } else {
        Write-Output "EXTERNAL_IP:$ip"
        Write-Output "RESULT:SUCCESS! Proxy is working!"
    }
} else {
    Write-Output "EXTERNAL_IP:No response"
    Write-Output "RESULT:UNKNOWN"
}

# Соединения к прокси
Write-Output ""
$conn = Get-NetTCPConnection -RemoteAddress {os.getenv("PROXY_HOST")} -ErrorAction SilentlyContinue | Where-Object {$_.State -eq 'Established'}
if ($conn) {
    Write-Output "PROXY_CONNECTIONS:$($conn.Count) established"
} else {
    Write-Output "PROXY_CONNECTIONS:None"
}
'''
result = ssh(check_cmd, timeout=60)
print(result)

print("\n" + "="*80)
print("📊 ИТОГ")
print("="*80)
