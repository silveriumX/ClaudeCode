#!/usr/bin/env python3
"""
Полная настройка Proxifier с правильным прокси и перезапуск в GUI
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = "10000"
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


def ssh(cmd, timeout=120):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)
    enc = base64.b64encode(cmd.encode('utf-16le')).decode()
    _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
    return o.read().decode('utf-8', errors='ignore').strip()


print("="*70)
print("  НАСТРОЙКА PROXIFIER")
print("="*70)

# Шаг 1: Остановить Proxifier
print("\n1. Остановка Proxifier...")
result = ssh(r'''
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
Start-Sleep 2
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "Still running, force kill..."
    taskkill /F /IM Proxifier.exe 2>&1
}
Write-Output "Proxifier stopped"
''')
print(result)

# Шаг 2: Создать профиль с прокси
print("\n2. Создание профиля...")

profile_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxifierProfile version="101" platform="Windows" product_id="0" product_minver="400">
    <Options>
        <Resolve>
            <AutoModeDetection enabled="false"/>
            <ViaProxy enabled="true"/>
            <ExcludeList>
                <Exclude>*.local</Exclude>
            </ExcludeList>
        </Resolve>
        <SystemProxySettings>SPECIFIED</SystemProxySettings>
        <HandleDirectConnections>true</HandleDirectConnections>
        <ConnectionLoopDetection>true</ConnectionLoopDetection>
        <ProcessServices>true</ProcessServices>
        <ProcessOtherUsers>true</ProcessOtherUsers>
    </Options>
    <ProxyList>
        <Proxy id="100" type="SOCKS5">
            <Address>{PROXY_HOST}</Address>
            <Port>{PROXY_PORT}</Port>
            <Options>21</Options>
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
            <Targets>localhost; 127.0.0.1; ::1; {PROXY_HOST}</Targets>
            <Action type="Direct"/>
        </Rule>
        <Rule enabled="true">
            <Name>Default</Name>
            <Action type="Proxy">100</Action>
        </Rule>
    </RuleList>
</ProxifierProfile>'''

profile_b64 = base64.b64encode(profile_xml.encode('utf-8')).decode()

result = ssh(f'''
# Создать директорию для профилей
$profileDir = "C:\\Users\\Administrator\\AppData\\Roaming\\Proxifier\\Profiles"
if (!(Test-Path $profileDir)) {{
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}}

$profilePath = "$profileDir\\Default.ppx"
$profileB64 = "{profile_b64}"
$profileBytes = [Convert]::FromBase64String($profileB64)
$profileText = [System.Text.Encoding]::UTF8.GetString($profileBytes)

[IO.File]::WriteAllText($profilePath, $profileText, [System.Text.Encoding]::UTF8)

if (Test-Path $profilePath) {{
    Write-Output "PROFILE_CREATED:$profilePath"
    Write-Output "SIZE:$((Get-Item $profilePath).Length) bytes"
}} else {{
    Write-Output "PROFILE_FAILED"
}}
''')
print(result)

# Шаг 3: Запустить Proxifier в интерактивной сессии
print("\n3. Запуск Proxifier в GUI сессии...")

result = ssh(r'''
$proxifierExe = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$profilePath = "C:\Users\Administrator\AppData\Roaming\Proxifier\Profiles\Default.ppx"

# Создать задачу для запуска в интерактивной сессии
$taskName = "ProxifierStart"
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

# XML для задачи с InteractiveToken
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals>
    <Principal id="Author">
      <UserId>Administrator</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$proxifierExe</Command>
      <Arguments>"$profilePath"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\proxifier_task.xml"
[IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)

# Создать и запустить задачу
schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1
schtasks /Run /TN $taskName 2>&1

Start-Sleep 8

# Проверить
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output ""
    Write-Output "PROXIFIER:RUNNING (PID=$($proc.Id))"
    Write-Output "MainWindowHandle:$($proc.MainWindowHandle)"
} else {
    Write-Output "PROXIFIER:NOT STARTED"
}

# Удалить задачу
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
''')
print(result)

# Шаг 4: Проверить IP
print("\n4. Проверка IP...")
time.sleep(5)

result = ssh(r'''
Write-Output "=== External IP Check ==="
$ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
Write-Output "IP: $ip"

if ($ip -eq "83.239.242.138") {
    Write-Output ""
    Write-Output "=============================================="
    Write-Output "SUCCESS! Traffic through proxy!"
    Write-Output "=============================================="
} elseif ($ip -eq "62.84.101.97") {
    Write-Output ""
    Write-Output "IP is server IP"
    Write-Output ""
    Write-Output "Checking Proxifier window..."
    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "Proxifier running but MainWindowHandle=$($proc.MainWindowHandle)"
        if ($proc.MainWindowHandle -eq 0) {
            Write-Output "Window not visible - may need interactive login"
        }
    }
}
''')
print(result)

print("\n" + "="*70)
print("  СТАТУС")
print("="*70)
