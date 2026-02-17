#!/usr/bin/env python3
"""
Полный сброс Proxifier: удаление всех настроек, создание чистого профиля
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
PROXY_PORT = "10001"
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


def ssh(cmd, timeout=60):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=10, look_for_keys=False)
        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
        return o.read().decode('utf-8', errors='ignore').strip()
    except Exception as e:
        return f"ERROR: {e}"


print("="*70)
print("🔄 ПОЛНЫЙ СБРОС PROXIFIER")
print("="*70)

# 1. Остановить Proxifier
print("\n📋 Шаг 1: Остановка Proxifier")
print(ssh(r'''
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
taskkill /IM Proxifier.exe /F 2>$null
Start-Sleep 2
Write-Output "STOPPED"
'''))

# 2. Удалить настройки из реестра
print("\n📋 Шаг 2: Очистка реестра")
print(ssh(r'''
$paths = @(
    "HKCU:\Software\Initex\Proxifier",
    "HKCU:\Software\Initex\ProxyChecker"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Remove-Item $p -Recurse -Force
        Write-Output "DELETED:$p"
    }
}
Write-Output "REGISTRY_CLEARED"
'''))

# 3. Удалить все профили Proxifier
print("\n📋 Шаг 3: Удаление профилей")
print(ssh(r'''
$profileDir = "$env:APPDATA\Proxifier4\Profiles"
if (Test-Path $profileDir) {
    Get-ChildItem $profileDir -Filter "*.ppx" | ForEach-Object {
        Write-Output "REMOVING:$($_.Name)"
        Remove-Item $_.FullName -Force
    }
}

# Удалить также .bak файлы
Get-ChildItem $profileDir -Filter "*.bak" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Output "PROFILES_CLEARED"
'''))

# 4. Создать чистый профиль
print("\n📋 Шаг 4: Создание нового профиля")
profile_cmd = f'''
$profileDir = "$env:APPDATA\\Proxifier4\\Profiles"
if (!(Test-Path $profileDir)) {{
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}}

$profilePath = "$profileDir\\Default.ppx"

$xml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxifierProfile version="102" platform="Windows" product_id="0" product_minver="400">
    <Options>
        <Resolve>
            <AutoModeDetection enabled="true"/>
            <ViaProxy enabled="false"/>
            <ExclusionList OnlyFromListMode="false">%ComputerName%; localhost; *.local</ExclusionList>
        </Resolve>
        <Encryption mode="basic"/>
        <ConnectionLoopDetection enabled="true" resolve="true"/>
        <HandleDirectConnections enabled="false"/>
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
            <Targets>localhost; 127.0.0.1; %ComputerName%; ::1</Targets>
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
[IO.File]::WriteAllText($profilePath, $xml, $enc)

Write-Output "PROFILE_CREATED:$profilePath"
Write-Output "SIZE:$((Get-Item $profilePath).Length) bytes"
'''
print(ssh(profile_cmd))

# 5. Запустить Proxifier
print("\n📋 Шаг 5: Запуск Proxifier")
print(ssh(r'''
$ProxifierPath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$taskName = "ProxifierCleanStart"

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
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec>
      <Command>$ProxifierPath</Command>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\ProxCleanStart.xml"
[IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)

schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
schtasks /Run /TN $taskName 2>&1 | Out-Null

Start-Sleep 5

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STARTED:PID=$($proc.Id) Session=$($proc.SessionId)"
} else {
    Write-Output "FAILED:Not started"
}

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''))

# 6. Ждём инициализации
print("\n⏱️  Ожидание 15 секунд для полной инициализации...")
time.sleep(15)

# 7. Проверка
print("\n📋 Шаг 6: ФИНАЛЬНАЯ ПРОВЕРКА")
print(ssh(r'''
$serverIp = "62.84.101.97"

# Процесс
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
Write-Output "PROCESS:$(if($proc){'Running PID='+$proc.Id+' Session='+$proc.SessionId}else{'Not running'})"

# IP
$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "EXTERNAL_IP:$ip"

if ($ip -and $ip -ne $serverIp) {
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "SUCCESS! PROXY IS WORKING!"
    Write-Output "IP changed from $serverIp to $ip"
    Write-Output "=========================================="
} else {
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "FAILED: Proxy not working"
    Write-Output "IP is still $ip"
    Write-Output "=========================================="
}

# Соединения
$conn = Get-NetTCPConnection -RemoteAddress {os.getenv("PROXY_HOST")} -ErrorAction SilentlyContinue | Where-Object {$_.State -ne 'TimeWait'}
Write-Output "PROXY_CONNECTIONS:$($conn.Count)"
'''))

print("\n" + "="*70)
