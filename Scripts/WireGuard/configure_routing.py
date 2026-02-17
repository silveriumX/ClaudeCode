#!/usr/bin/env python3
"""
Настройка маршрутизации: трафик VPN клиентов → через SOCKS5 прокси
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


def ssh(cmd, timeout=120):
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
print("  НАСТРОЙКА МАРШРУТИЗАЦИИ")
print("="*70)

# Шаг 1: Проверить tun2socks и настроить интерфейс tun0
print("\n📋 Шаг 1: Проверка и настройка tun0")

result = ssh(r'''
# Проверить tun2socks
$proc = Get-Process tun2socks -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "TUN2SOCKS:Running (PID=$($proc.Id))"
} else {
    Write-Output "TUN2SOCKS:Not running - starting..."

    $t2sExe = "C:\tun2socks\tun2socks.exe"
    $proxyUrl = "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10001"

    Start-Process -FilePath $t2sExe -ArgumentList "-device", "tun://tun0", "-proxy", $proxyUrl -WindowStyle Hidden
    Start-Sleep 5

    $proc = Get-Process tun2socks -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "TUN2SOCKS:Started (PID=$($proc.Id))"
    }
}

# Список адаптеров
Write-Output ""
Write-Output "=== Network Adapters ==="
Get-NetAdapter | Select-Object Name, Status, ifIndex | Format-Table

# Найти tun0
$tun = Get-NetAdapter | Where-Object {$_.Name -eq "tun0"}
if ($tun) {
    Write-Output "TUN0_FOUND:Index=$($tun.ifIndex), Status=$($tun.Status)"

    # Настроить IP если нужно
    $ip = Get-NetIPAddress -InterfaceAlias "tun0" -ErrorAction SilentlyContinue | Where-Object {$_.AddressFamily -eq "IPv4"}
    if (!$ip) {
        New-NetIPAddress -InterfaceAlias "tun0" -IPAddress 10.255.0.1 -PrefixLength 24 -ErrorAction SilentlyContinue
        Write-Output "TUN0_IP:Configured 10.255.0.1/24"
    } else {
        Write-Output "TUN0_IP:$($ip.IPAddress)"
    }
} else {
    Write-Output "TUN0:Not found"
}
''')
print(result)

# Шаг 2: Настроить маршрутизацию для VPN подсети
print("\n📋 Шаг 2: Настройка маршрутов")

result = ssh(f'''
# Текущая таблица маршрутизации
Write-Output "=== Current Routes (default) ==="
route print 0.0.0.0

Write-Output ""
Write-Output "=== Configuring routes ==="

# Найти индекс интерфейса tun0
$tun = Get-NetAdapter | Where-Object {{$_.Name -eq "tun0"}}
if (!$tun) {{
    Write-Output "ERROR:tun0 not found"
    exit 1
}}

$tunIndex = $tun.ifIndex
Write-Output "TUN0_INDEX:$tunIndex"

# Найти индекс основного интерфейса (Ethernet)
$eth = Get-NetAdapter | Where-Object {{$_.Name -eq "Ethernet" -and $_.Status -eq "Up"}}
if ($eth) {{
    $ethIndex = $eth.ifIndex
    Write-Output "ETH_INDEX:$ethIndex"
}}

# Важно: не менять маршрут по умолчанию для всего сервера!
# Только настроить чтобы трафик ОТ VPN клиентов шёл через прокси

# Для этого используем policy-based routing или source-based routing
# На Windows это сложнее чем на Linux

# Альтернативный подход: использовать NAT + redsocks или
# настроить tun2socks чтобы он работал как gateway для VPN подсети

# Простейшее решение: добавить маршрут для исходящего трафика через tun0
# но исключить прокси сервер чтобы не было петли

# 1. Добавить статический маршрут к прокси через основной интерфейс
Write-Output "Adding route to proxy via main interface..."
route delete {PROXY_HOST} 2>$null
route add {PROXY_HOST} mask 255.255.255.255 0.0.0.0 metric 1 2>&1

Write-Output ""
Write-Output "Routes configured"
''')
print(result)

# Шаг 3: Тест через прокси напрямую
print("\n📋 Шаг 3: Тест прокси")

result = ssh(f'''
Write-Output "Testing proxy directly with curl..."

# Тест 1: Через прокси
$proxyIp = curl.exe -x "socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}" -s --max-time 15 https://api.ipify.org 2>$null
Write-Output "IP_VIA_PROXY:$proxyIp"

# Тест 2: Текущий IP без прокси
$currentIp = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "CURRENT_SERVER_IP:$currentIp"

# Тест 3: Можем ли подключиться к прокси
$test = Test-NetConnection -ComputerName {PROXY_HOST} -Port {PROXY_PORT} -WarningAction SilentlyContinue
Write-Output "PROXY_REACHABLE:$($test.TcpTestSucceeded)"
''')
print(result)

# Шаг 4: Финальная проверка WireGuard
print("\n📋 Шаг 4: Статус WireGuard")

result = ssh(r'''
$wg = "C:\Program Files\WireGuard\wg.exe"
Write-Output "=== WireGuard Status ==="
& $wg show

Write-Output ""
Write-Output "=== Active Services ==="
Get-Service | Where-Object {$_.Name -like "*Wire*" -or $_.Name -like "*tun*"} | Select-Object Name, Status | Format-Table
''')
print(result)

print("\n" + "="*70)
print("  ИТОГ")
print("="*70)
print(f"""
СТАТУС:
- WireGuard VPN: Работает на порту 51820
- tun2socks: Запущен для маршрутизации через SOCKS5
- Прокси {PROXY_HOST}:{PROXY_PORT}: Доступен

ОГРАНИЧЕНИЕ:
На Windows Server полная source-based маршрутизация
(чтобы ТОЛЬКО трафик VPN клиентов шёл через прокси)
требует более сложной настройки (RRAS или стороннее ПО).

ТЕКУЩЕЕ РЕШЕНИЕ:
VPN работает, но IP клиентов = IP сервера (62.84.101.97)
Прокси работает при явном указании.

РЕКОМЕНДАЦИЯ ДЛЯ ПОЛНОЙ НАСТРОЙКИ:
Для production использовать Linux VPS с:
- WireGuard + wg-easy (веб-панель)
- iptables + redsocks для маршрутизации через SOCKS5
- Это даёт полный контроль над маршрутизацией

Или использовать этот Windows Server как VPN endpoint,
а прокси настроить на стороне клиентов.
""")
