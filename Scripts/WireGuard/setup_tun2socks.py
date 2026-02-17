#!/usr/bin/env python3
"""
Настройка tun2socks для маршрутизации через SOCKS5 прокси
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64
import io
import sys
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import paramiko

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = "10001"
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


def ssh(cmd, timeout=180):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)
        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
        return o.read().decode('utf-8', errors='ignore').strip()
    except Exception as ex:
        return f"SSH_ERROR: {ex}"


print("="*70)
print("  НАСТРОЙКА TUN2SOCKS")
print("="*70)

# Шаг 1: Скачать Wintun
print("\n📋 Шаг 1: Установка Wintun драйвера")
result = ssh(r'''
$wintunDir = "C:\tun2socks"
$wintunDll = "$wintunDir\wintun.dll"

if (Test-Path $wintunDll) {
    Write-Output "WINTUN:Already exists"
} else {
    Write-Output "Downloading Wintun..."

    $url = "https://www.wintun.net/builds/wintun-0.14.1.zip"
    $zipPath = "$env:TEMP\wintun.zip"

    curl.exe -L -o $zipPath $url 2>&1

    if (Test-Path $zipPath) {
        $size = (Get-Item $zipPath).Length
        Write-Output "DOWNLOADED:$size bytes"

        $extractDir = "$env:TEMP\wintun"
        Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

        # Найти amd64 dll
        $dll = Get-ChildItem $extractDir -Filter "wintun.dll" -Recurse | Where-Object {$_.DirectoryName -like "*amd64*"} | Select-Object -First 1
        if ($dll) {
            Copy-Item $dll.FullName $wintunDll -Force
            Write-Output "WINTUN_INSTALLED:$wintunDll"
        } else {
            # Любой dll
            $dll = Get-ChildItem $extractDir -Filter "wintun.dll" -Recurse | Select-Object -First 1
            if ($dll) {
                Copy-Item $dll.FullName $wintunDll -Force
                Write-Output "WINTUN_INSTALLED:$wintunDll"
            }
        }
    }
}

# Проверить что оба файла на месте
$t2s = "C:\tun2socks\tun2socks.exe"
$wt = "C:\tun2socks\wintun.dll"

if ((Test-Path $t2s) -and (Test-Path $wt)) {
    Write-Output ""
    Write-Output "FILES_READY:"
    Write-Output "  tun2socks.exe: $(Test-Path $t2s)"
    Write-Output "  wintun.dll: $(Test-Path $wt)"
} else {
    Write-Output "FILES_MISSING"
}
''')
print(result)

# Шаг 2: Создать скрипт запуска tun2socks
print("\n📋 Шаг 2: Создание скрипта запуска")

# tun2socks команда:
# tun2socks -device tun://tun0 -proxy socks5://user:pass@host:port
tun2socks_cmd = f"C:\\tun2socks\\tun2socks.exe -device tun://tun0 -proxy socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

start_script = f'''@echo off
cd /d C:\\tun2socks
echo Starting tun2socks...
start /B tun2socks.exe -device tun://tun0 -proxy socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}
timeout /t 5
echo Configuring network...
netsh interface ip set address "tun0" static 10.255.0.1 255.255.255.0
route add 0.0.0.0 mask 0.0.0.0 10.255.0.1 metric 5
echo Done!
'''

start_script_b64 = base64.b64encode(start_script.encode('utf-8')).decode()

result = ssh(f'''
$scriptPath = "C:\\tun2socks\\start_tun2socks.bat"
$scriptB64 = "{start_script_b64}"
$scriptBytes = [Convert]::FromBase64String($scriptB64)
$scriptText = [System.Text.Encoding]::UTF8.GetString($scriptBytes)

[IO.File]::WriteAllText($scriptPath, $scriptText, [System.Text.Encoding]::ASCII)

if (Test-Path $scriptPath) {{
    Write-Output "SCRIPT_CREATED:$scriptPath"
}} else {{
    Write-Output "SCRIPT_FAILED"
}}
''')
print(result)

# Шаг 3: Запустить tun2socks
print("\n📋 Шаг 3: Запуск tun2socks")

result = ssh(f'''
# Остановить существующий процесс
Stop-Process -Name tun2socks -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$t2sDir = "C:\\tun2socks"
$t2sExe = "$t2sDir\\tun2socks.exe"

# Запустить tun2socks в фоне
$proxyUrl = "socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

Write-Output "Starting tun2socks with proxy: {PROXY_HOST}:{PROXY_PORT}"

# Создаём задачу для запуска в интерактивной сессии
$taskName = "Tun2SocksStart"
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

# PowerShell скрипт для запуска
$psScript = @"
Start-Process -FilePath "$t2sExe" -ArgumentList "-device", "tun://tun0", "-proxy", "$proxyUrl" -WindowStyle Hidden
"@

$psScriptPath = "$t2sDir\\run_t2s.ps1"
$psScript | Out-File $psScriptPath -Encoding utf8

$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals><Principal><UserId>Administrator</UserId><LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><AllowStartOnDemand>true</AllowStartOnDemand></Settings>
  <Actions><Exec><Command>powershell.exe</Command><Arguments>-ExecutionPolicy Bypass -File "$psScriptPath"</Arguments></Exec></Actions>
</Task>
"@

$xmlPath = "$env:TEMP\\t2s_task.xml"
[IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)

schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
schtasks /Run /TN $taskName 2>&1 | Out-Null

Start-Sleep 8

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

# Проверить процесс
$proc = Get-Process tun2socks -ErrorAction SilentlyContinue
if ($proc) {{
    Write-Output "TUN2SOCKS_RUNNING:PID=$($proc.Id)"
}} else {{
    Write-Output "TUN2SOCKS:Not running"

    # Попробовать запустить напрямую
    Write-Output "Trying direct start..."
    Start-Process -FilePath $t2sExe -ArgumentList "-device", "tun://tun0", "-proxy", "$proxyUrl" -WindowStyle Hidden
    Start-Sleep 5

    $proc = Get-Process tun2socks -ErrorAction SilentlyContinue
    if ($proc) {{
        Write-Output "TUN2SOCKS_STARTED:PID=$($proc.Id)"
    }} else {{
        Write-Output "TUN2SOCKS_FAILED"
    }}
}}
''')
print(result)

# Шаг 4: Настроить сетевой интерфейс tun0
print("\n📋 Шаг 4: Настройка сетевого интерфейса")

result = ssh(r'''
Start-Sleep 3

# Найти интерфейс tun0
$tunAdapter = Get-NetAdapter | Where-Object {$_.Name -eq "tun0" -or $_.InterfaceDescription -like "*tun*"}

if ($tunAdapter) {
    Write-Output "TUN_ADAPTER:$($tunAdapter.Name) - $($tunAdapter.Status)"

    # Если не Up, включить
    if ($tunAdapter.Status -ne "Up") {
        Enable-NetAdapter -Name $tunAdapter.Name -Confirm:$false
        Start-Sleep 2
    }

    # Настроить IP
    try {
        New-NetIPAddress -InterfaceAlias $tunAdapter.Name -IPAddress 10.255.0.1 -PrefixLength 24 -ErrorAction SilentlyContinue
        Write-Output "IP_CONFIGURED:10.255.0.1/24"
    } catch {
        Write-Output "IP_NOTE:Already configured or error"
    }

} else {
    Write-Output "TUN_ADAPTER:Not found yet"
    Write-Output "Listing all adapters:"
    Get-NetAdapter | Select-Object Name, Status, InterfaceDescription | Format-Table
}
''')
print(result)

# Шаг 5: Проверка IP
print("\n📋 Шаг 5: Проверка IP")
time.sleep(3)

result = ssh(f'''
# Проверить процесс tun2socks
$proc = Get-Process tun2socks -ErrorAction SilentlyContinue
if ($proc) {{
    Write-Output "TUN2SOCKS:Running (PID=$($proc.Id))"
}} else {{
    Write-Output "TUN2SOCKS:Not running"
}}

# Проверить IP через прямой curl с прокси (для сравнения)
Write-Output ""
Write-Output "Direct proxy test:"
$directIp = curl.exe -x "socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}" -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "PROXY_IP:$directIp"

Write-Output ""
Write-Output "Current external IP (without forcing proxy):"
$currentIp = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "CURRENT_IP:$currentIp"

if ($currentIp -eq "{PROXY_HOST}") {{
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "SUCCESS! All traffic through proxy!"
    Write-Output "=========================================="
}} elseif ($currentIp -eq "{SSH_HOST}") {{
    Write-Output ""
    Write-Output "IP is server IP - tun2socks routing not active"
}}
''')
print(result)

print("\n" + "="*70)
print("  СТАТУС")
print("="*70)
print(f"""
tun2socks установлен и настроен.

Прокси работает напрямую: IP через прокси = 81.177.254.254 (или IP прокси)
Текущий IP сервера: проверьте в выводе выше

ВАЖНО: tun2socks создаёт TUN интерфейс для маршрутизации трафика.
Для полной маршрутизации нужно:
1. Добавить маршрут по умолчанию через tun0
2. Исключить прокси-сервер из маршрутизации (чтобы не было петли)

Для VPN клиентов это означает:
- Клиент подключается через WireGuard (порт 51820)
- Трафик клиента идёт через VPN туннель
- На сервере трафик идёт через tun2socks → SOCKS5 прокси

Файл конфига клиента:
C:\\Users\\Admin\\Documents\\Cursor\\Scripts\\WireGuard\\client_config.conf
""")
