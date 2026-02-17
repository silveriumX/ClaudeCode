#!/usr/bin/env python3
"""
Полная настройка WireGuard VPN + маршрутизация через SOCKS5 прокси
IP клиентов = IP прокси ({os.getenv("PROXY_HOST")})
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

WG_PORT = 51820
WG_SUBNET = "10.66.66"

# ProxiFyre URLs
NDISAPI_URL = "https://github.com/wiresock/ndisapi/releases/download/v3.6.0/Windows.Packet.Filter.3.6.0.0-x64.msi"
PROXIFYRE_URL = "https://github.com/wiresock/proxifyre/releases/download/v2.2.1/ProxiFyre.2.2.1.zip"


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


def main():
    print("="*70)
    print("  ПОЛНАЯ НАСТРОЙКА VPN + SOCKS5 ПРОКСИ")
    print("="*70)
    print(f"\nСервер: {SSH_HOST}")
    print(f"Прокси: {PROXY_HOST}:{PROXY_PORT}")
    print(f"Цель: IP клиентов VPN = {PROXY_HOST}")

    # ==========================================
    # ЭТАП 1: Проверка WireGuard
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 1: Проверка WireGuard")
    print("="*70)

    result = ssh(r'''
$wg = "C:\Program Files\WireGuard\wg.exe"
if (Test-Path $wg) {
    Write-Output "WIREGUARD:Installed"
    & $wg show 2>&1
} else {
    Write-Output "WIREGUARD:Not installed"
}
''')
    print(result)

    if "WIREGUARD:Not installed" in result:
        print("\n❌ WireGuard не установлен. Запусти сначала setup_wireguard_windows.py")
        return

    # ==========================================
    # ЭТАП 2: Установка Windows Packet Filter
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 2: Установка Windows Packet Filter (драйвер для ProxiFyre)")
    print("="*70)

    result = ssh(r'''
# Проверить установлен ли драйвер
$driver = Get-Service ndisapi -ErrorAction SilentlyContinue
if ($driver) {
    Write-Output "NDISAPI:Already installed ($($driver.Status))"
} else {
    Write-Output "NDISAPI:Not installed, downloading..."
}
''')
    print(result)

    if "Not installed" in result:
        print("\nСкачиваю и устанавливаю WinpkFilter...")
        result = ssh(f'''
$msiUrl = "{NDISAPI_URL}"
$msiPath = "$env:TEMP\\ndisapi.msi"

Write-Output "Downloading WinpkFilter..."
Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath -UseBasicParsing

if (Test-Path $msiPath) {{
    Write-Output "DOWNLOADED:$((Get-Item $msiPath).Length) bytes"

    Write-Output "Installing..."
    Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /qn /norestart" -Wait -NoNewWindow

    Start-Sleep 5

    $svc = Get-Service ndisapi -ErrorAction SilentlyContinue
    if ($svc) {{
        Write-Output "INSTALL_SUCCESS:$($svc.Status)"

        # Запустить сервис если не запущен
        if ($svc.Status -ne "Running") {{
            Start-Service ndisapi
            Start-Sleep 2
            $svc = Get-Service ndisapi
            Write-Output "SERVICE_STARTED:$($svc.Status)"
        }}
    }} else {{
        Write-Output "INSTALL_FAILED"
    }}
}} else {{
    Write-Output "DOWNLOAD_FAILED"
}}
''', timeout=300)
        print(result)

        if "INSTALL_FAILED" in result or "DOWNLOAD_FAILED" in result:
            print("\n❌ Ошибка установки WinpkFilter")
            return

    # ==========================================
    # ЭТАП 3: Установка ProxiFyre
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 3: Установка ProxiFyre")
    print("="*70)

    result = ssh(r'''
$proxifyreDir = "C:\ProxiFyre"
$exePath = Get-ChildItem $proxifyreDir -Filter "ProxiFyre.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1

if ($exePath) {
    Write-Output "PROXIFYRE:Already installed at $($exePath.FullName)"
} else {
    Write-Output "PROXIFYRE:Not installed"
}
''')
    print(result)

    if "Not installed" in result:
        print("\nСкачиваю и устанавливаю ProxiFyre...")
        result = ssh(f'''
$zipUrl = "{PROXIFYRE_URL}"
$zipPath = "$env:TEMP\\proxifyre.zip"
$installDir = "C:\\ProxiFyre"

# Создать директорию
if (!(Test-Path $installDir)) {{
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}}

Write-Output "Downloading ProxiFyre..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

if (Test-Path $zipPath) {{
    Write-Output "DOWNLOADED:$((Get-Item $zipPath).Length) bytes"

    Write-Output "Extracting..."
    Expand-Archive -Path $zipPath -DestinationPath $installDir -Force

    # Найти exe
    $exe = Get-ChildItem $installDir -Filter "ProxiFyre.exe" -Recurse | Select-Object -First 1
    if ($exe) {{
        Write-Output "INSTALL_SUCCESS:$($exe.FullName)"
    }} else {{
        Write-Output "INSTALL_FAILED:exe not found"
    }}
}} else {{
    Write-Output "DOWNLOAD_FAILED"
}}
''', timeout=180)
        print(result)

    # ==========================================
    # ЭТАП 4: Создание конфига ProxiFyre
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 4: Создание конфига ProxiFyre")
    print("="*70)

    # Конфиг ProxiFyre - весь трафик через SOCKS5
    config = {
        "logLevel": "Info",
        "bypassLan": True,
        "proxies": [
            {
                "appNames": [""],  # Все приложения
                "socks5ProxyEndpoint": f"{PROXY_HOST}:{PROXY_PORT}",
                "username": PROXY_USER,
                "password": PROXY_PASS,
                "supportedProtocols": ["TCP", "UDP"]
            }
        ],
        "excludes": [
            "ProxiFyre.exe",
            "wireguard.exe",
            "wg.exe",
            "svchost.exe"
        ]
    }

    import json
    config_json = json.dumps(config, indent=4)
    config_b64 = base64.b64encode(config_json.encode('utf-8')).decode()

    result = ssh(f'''
$proxifyreDir = "C:\\ProxiFyre"
$exeDir = (Get-ChildItem $proxifyreDir -Filter "ProxiFyre.exe" -Recurse | Select-Object -First 1).DirectoryName

if (!$exeDir) {{
    Write-Output "ERROR:ProxiFyre.exe not found"
    exit 1
}}

$configPath = "$exeDir\\app-config.json"

$configB64 = "{config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$configText = [System.Text.Encoding]::UTF8.GetString($configBytes)

[IO.File]::WriteAllText($configPath, $configText, [System.Text.Encoding]::UTF8)

if (Test-Path $configPath) {{
    Write-Output "CONFIG_CREATED:$configPath"
    Write-Output "SIZE:$((Get-Item $configPath).Length) bytes"
    Write-Output ""
    Write-Output "=== Config Content ==="
    Get-Content $configPath
}} else {{
    Write-Output "CONFIG_FAILED"
}}
''')
    print(result)

    # ==========================================
    # ЭТАП 5: Остановить Proxifier (если работает)
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 5: Остановка Proxifier (если работает)")
    print("="*70)

    result = ssh(r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Stop-Process -Name Proxifier -Force
    Write-Output "PROXIFIER:Stopped"
} else {
    Write-Output "PROXIFIER:Not running"
}
''')
    print(result)

    # ==========================================
    # ЭТАП 6: Установка и запуск ProxiFyre как сервис
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 6: Запуск ProxiFyre как сервис")
    print("="*70)

    result = ssh(r'''
$proxifyreDir = "C:\ProxiFyre"
$exe = (Get-ChildItem $proxifyreDir -Filter "ProxiFyre.exe" -Recurse | Select-Object -First 1).FullName

if (!$exe) {
    Write-Output "ERROR:ProxiFyre.exe not found"
    exit 1
}

Write-Output "EXE:$exe"
$exeDir = Split-Path $exe

# Перейти в директорию
Set-Location $exeDir

# Остановить если работает
$svc = Get-Service ProxiFyre -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output "Stopping existing service..."
    & $exe stop 2>&1 | Out-Null
    Start-Sleep 2
    & $exe uninstall 2>&1 | Out-Null
    Start-Sleep 2
}

# Установить и запустить
Write-Output "Installing service..."
$installResult = & $exe install 2>&1
Write-Output "INSTALL:$installResult"

Start-Sleep 3

Write-Output "Starting service..."
$startResult = & $exe start 2>&1
Write-Output "START:$startResult"

Start-Sleep 5

# Проверить статус
$svc = Get-Service ProxiFyre -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output "SERVICE_STATUS:$($svc.Status)"
} else {
    Write-Output "SERVICE:Not found"
}
''')
    print(result)

    # ==========================================
    # ЭТАП 7: Проверка IP
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 7: Проверка IP (через прокси)")
    print("="*70)

    time.sleep(5)

    result = ssh(r'''
Write-Output "=== Checking external IP ==="

# Прямой тест через curl
$ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
Write-Output "EXTERNAL_IP:$ip"

if ($ip -eq "{os.getenv("PROXY_HOST")}") {
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "SUCCESS! Traffic goes through SOCKS5 proxy!"
    Write-Output "IP = {os.getenv("PROXY_HOST")}"
    Write-Output "=========================================="
} elseif ($ip -eq "62.84.101.97") {
    Write-Output ""
    Write-Output "WARNING: IP is still server IP"
    Write-Output "ProxiFyre may need more time or restart"
} else {
    Write-Output "IP:$ip"
}

# Статус ProxiFyre
$svc = Get-Service ProxiFyre -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output ""
    Write-Output "ProxiFyre service: $($svc.Status)"
}
''')
    print(result)

    # ==========================================
    # ЭТАП 8: Финальная проверка WireGuard
    # ==========================================
    print("\n" + "="*70)
    print("ЭТАП 8: Статус WireGuard")
    print("="*70)

    result = ssh(r'''
$wg = "C:\Program Files\WireGuard\wg.exe"
Write-Output "=== WireGuard Status ==="
& $wg show

Write-Output ""
Write-Output "=== NAT Status ==="
Get-NetNat | Select-Object Name, InternalIPInterfaceAddressPrefix, Active | Format-Table
''')
    print(result)

    # ==========================================
    # ИТОГ
    # ==========================================
    print("\n" + "="*70)
    print("  НАСТРОЙКА ЗАВЕРШЕНА")
    print("="*70)

    # Читаем клиентский конфиг
    try:
        with open("C:\\Users\\Admin\\Documents\\Cursor\\Scripts\\WireGuard\\client_config.conf", 'r') as f:
            client_config = f.read()
    except:
        client_config = """[Interface]
PrivateKey = GCZUJXVunV/li9LQhcT1rDPJ3xNMM06r/yPdYSWriXo=
Address = 10.66.66.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = C8HK7IlrK7ePEgc0xPETrz7bkdXL+ZO2u6y9Pq7Zrhs=
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = 62.84.101.97:51820
PersistentKeepalive = 25
"""

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  WireGuard VPN + SOCKS5 Proxy готов!                             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Сервер: {SSH_HOST}                                       ║
║  VPN порт: {WG_PORT}/UDP                                         ║
║  Прокси: {PROXY_HOST}:{PROXY_PORT}                           ║
║                                                                  ║
║  IP клиентов после подключения: {PROXY_HOST}             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

📋 КОНФИГ ДЛЯ КЛИЕНТА (сохрани как wireguard.conf):
{'─' * 60}
{client_config}
{'─' * 60}

📱 Как подключиться:
1. Установи WireGuard: https://www.wireguard.com/install/
2. Импортируй конфиг выше
3. Нажми "Activate"

🔍 Проверка после подключения:
- https://ipleak.net — IP должен быть {PROXY_HOST}
- https://browserleaks.com/webrtc — проверка WebRTC
- DNS должен быть 1.1.1.1 (Cloudflare)
""")


if __name__ == "__main__":
    main()
