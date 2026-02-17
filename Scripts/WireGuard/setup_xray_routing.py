#!/usr/bin/env python3
"""
Настройка Xray для маршрутизации VPN трафика через SOCKS5
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64, io, sys, json, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = 10000
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


def ssh(cmd, timeout=180):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)
    enc = base64.b64encode(cmd.encode('utf-16le')).decode()
    _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
    return o.read().decode('utf-8', errors='ignore').strip()


print("="*70)
print("  WIREGUARD + XRAY ROUTING")
print("="*70)

# Шаг 1: Проверить что прокси работает
print("\n1. Проверка прокси...")
result = ssh(f'''
$ip = curl.exe -x "socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}" -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "PROXY_IP:$ip"
''')
print(result)

if "PROXY_IP:" not in result or result.split("PROXY_IP:")[1].strip() == "":
    print("❌ Прокси не работает!")
    sys.exit(1)

proxy_ip = result.split("PROXY_IP:")[1].strip()
print(f"✅ Прокси работает, IP = {proxy_ip}")

# Шаг 2: Скачать Xray
print("\n2. Скачивание Xray...")
result = ssh(r'''
$xrayDir = "C:\xray"
$xrayExe = "$xrayDir\xray.exe"

if (Test-Path $xrayExe) {
    Write-Output "XRAY:Already installed"
    & $xrayExe version 2>&1 | Select-Object -First 1
} else {
    Write-Output "Downloading Xray..."

    if (!(Test-Path $xrayDir)) {
        New-Item -ItemType Directory -Path $xrayDir -Force | Out-Null
    }

    $url = "https://github.com/XTLS/Xray-core/releases/download/v24.12.31/Xray-windows-64.zip"
    $zipPath = "$env:TEMP\xray.zip"

    curl.exe -L -o $zipPath $url 2>&1

    if (Test-Path $zipPath) {
        Expand-Archive -Path $zipPath -DestinationPath $xrayDir -Force
        Write-Output "XRAY:Installed"
        & $xrayExe version 2>&1 | Select-Object -First 1
    }
}
''')
print(result)

# Шаг 3: Создать конфиг Xray
print("\n3. Создание конфига Xray...")

# Xray конфиг: transparent proxy для всего трафика
xray_config = {
    "log": {"loglevel": "warning"},
    "inbounds": [
        {
            "tag": "transparent",
            "port": 12345,
            "protocol": "dokodemo-door",
            "settings": {
                "network": "tcp,udp",
                "followRedirect": True
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            }
        }
    ],
    "outbounds": [
        {
            "tag": "proxy",
            "protocol": "socks",
            "settings": {
                "servers": [{
                    "address": PROXY_HOST,
                    "port": PROXY_PORT,
                    "users": [{
                        "user": PROXY_USER,
                        "pass": PROXY_PASS
                    }]
                }]
            }
        },
        {
            "tag": "direct",
            "protocol": "freedom"
        }
    ],
    "routing": {
        "rules": [
            {"type": "field", "ip": [PROXY_HOST], "outboundTag": "direct"},
            {"type": "field", "ip": ["10.66.66.0/24"], "outboundTag": "direct"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"}
        ]
    }
}

config_json = json.dumps(xray_config, indent=2)
config_b64 = base64.b64encode(config_json.encode('utf-8')).decode()

result = ssh(f'''
$configPath = "C:\\xray\\config.json"
$configB64 = "{config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$configText = [System.Text.Encoding]::UTF8.GetString($configBytes)
[IO.File]::WriteAllText($configPath, $configText, [System.Text.Encoding]::UTF8)
Write-Output "CONFIG:Created"
''')
print(result)

# Шаг 4: Запустить Xray
print("\n4. Запуск Xray...")
result = ssh(r'''
# Остановить если работает
Stop-Process -Name xray -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$xrayExe = "C:\xray\xray.exe"
$configPath = "C:\xray\config.json"

# Запустить в фоне
Start-Process -FilePath $xrayExe -ArgumentList "run","-c",$configPath -WindowStyle Hidden

Start-Sleep 3

$proc = Get-Process xray -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "XRAY:Running PID=$($proc.Id)"
} else {
    Write-Output "XRAY:Not running"
}
''')
print(result)

# Шаг 5: Настроить маршрутизацию через iptables-подобный механизм
# На Windows это netsh + route
print("\n5. Настройка маршрутизации для VPN клиентов...")

result = ssh(r'''
# Проверить WireGuard
$wg = "C:\Program Files\WireGuard\wg.exe"
Write-Output "=== WireGuard Status ==="
& $wg show

Write-Output ""
Write-Output "=== NAT Status ==="
Get-NetNat | Format-Table Name, InternalIPInterfaceAddressPrefix

Write-Output ""
Write-Output "=== Current IP ==="
$ip = curl.exe -s --max-time 5 https://api.ipify.org 2>$null
Write-Output "Server IP: $ip"
''')
print(result)

print("\n" + "="*70)
print("  СТАТУС")
print("="*70)
print(f"""
WireGuard VPN: Работает на порту 51820
Xray: Запущен на порту 12345
Прокси: {PROXY_HOST}:{PROXY_PORT} (IP = {proxy_ip})

ПРОБЛЕМА:
На Windows нет простого способа перенаправить ВСЕ исходящий трафик
через Xray/прокси без TUN-драйвера или Proxifier.

РЕШЕНИЕ:
Для полноценной работы нужен **Linux VPS** где можно использовать
iptables + redsocks для прозрачного проксирования.

ТЕКУЩИЙ ВАРИАНТ:
VPN клиенты получат IP сервера (62.84.101.97).
Для IP прокси ({proxy_ip}) нужен Linux.
""")
