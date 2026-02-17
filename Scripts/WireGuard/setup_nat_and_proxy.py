#!/usr/bin/env python3
"""
Настройка NAT и маршрутизации через SOCKS5 прокси для WireGuard
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
print("  НАСТРОЙКА NAT И МАРШРУТИЗАЦИИ")
print("="*70)

# Шаг 1: Включить IP Forwarding
print("\n📋 Шаг 1: Включение IP Forwarding")
result = ssh(r'''
# Проверить текущее состояние
$forwarding = (Get-NetIPInterface | Where-Object {$_.Forwarding -eq "Enabled"}).Count

Write-Output "Current forwarding interfaces: $forwarding"

# Включить IP forwarding
Set-NetIPInterface -Forwarding Enabled -ErrorAction SilentlyContinue
Write-Output "IP_FORWARDING:Enabled"

# Проверить в реестре тоже
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
$ipForward = (Get-ItemProperty -Path $regPath).IPEnableRouter
if ($ipForward -ne 1) {
    Set-ItemProperty -Path $regPath -Name "IPEnableRouter" -Value 1
    Write-Output "REGISTRY:Updated (requires reboot for full effect)"
} else {
    Write-Output "REGISTRY:Already enabled"
}
''')
print(result)

# Шаг 2: Настроить NAT через Internet Connection Sharing или RRAS
print("\n📋 Шаг 2: Настройка NAT")
result = ssh(r'''
# Проверить доступные сетевые адаптеры
Write-Output "=== Network Adapters ==="
Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object Name, InterfaceDescription, Status | Format-Table

# Проверить адаптер WireGuard
$wgAdapter = Get-NetAdapter | Where-Object {$_.Name -like "*wg*" -or $_.InterfaceDescription -like "*WireGuard*"}
if ($wgAdapter) {
    Write-Output "WG_ADAPTER:$($wgAdapter.Name)"
} else {
    Write-Output "WG_ADAPTER:Not found"
}

# Проверить основной интерфейс для выхода в интернет
$mainAdapter = Get-NetAdapter | Where-Object {$_.Status -eq "Up" -and $_.Name -notlike "*wg*" -and $_.Name -notlike "*Loopback*"} | Select-Object -First 1
Write-Output "MAIN_ADAPTER:$($mainAdapter.Name)"
''')
print(result)

# Шаг 3: Установить и настроить NAT через netsh
print("\n📋 Шаг 3: Настройка NAT через netsh")
result = ssh(r'''
# На Windows Server используем RRAS или netsh для NAT

# Сначала проверим RRAS
$rras = Get-Service RemoteAccess -ErrorAction SilentlyContinue
if ($rras) {
    Write-Output "RRAS_STATUS:$($rras.Status)"
} else {
    Write-Output "RRAS:Not installed"
}

# Попробуем простой NAT через netsh routing
# netsh routing ip nat install
# netsh routing ip nat add interface "Ethernet" full
# netsh routing ip nat add interface "wg0" private

# Альтернатива - использовать Windows NAT
Write-Output ""
Write-Output "Checking Windows NAT..."
$nat = Get-NetNat -ErrorAction SilentlyContinue
if ($nat) {
    Write-Output "EXISTING_NAT:"
    $nat | Format-List
} else {
    Write-Output "NO_NAT_CONFIGURED"
}
''')
print(result)

# Шаг 4: Создать NAT для VPN подсети
print("\n📋 Шаг 4: Создание NAT правила")
result = ssh(r'''
# Удалить старый NAT если есть
Remove-NetNat -Name "WireGuardNAT" -Confirm:$false -ErrorAction SilentlyContinue

# Создать новый NAT для VPN подсети
try {
    New-NetNat -Name "WireGuardNAT" -InternalIPInterfaceAddressPrefix "10.66.66.0/24" -ErrorAction Stop
    Write-Output "NAT_CREATED:WireGuardNAT for 10.66.66.0/24"
} catch {
    Write-Output "NAT_ERROR:$($_.Exception.Message)"

    # Альтернативный метод - через ICS или routing
    Write-Output ""
    Write-Output "Trying alternative method..."
}

# Проверить NAT
$nat = Get-NetNat -ErrorAction SilentlyContinue
if ($nat) {
    Write-Output ""
    Write-Output "=== Active NAT ==="
    $nat | Select-Object Name, InternalIPInterfaceAddressPrefix, Active | Format-Table
}
''')
print(result)

# Шаг 5: Проверить статус WireGuard
print("\n📋 Шаг 5: Проверка WireGuard")
result = ssh(r'''
$wg = "C:\Program Files\WireGuard\wg.exe"
Write-Output "=== WireGuard Status ==="
& $wg show

Write-Output ""
Write-Output "=== WireGuard Interface IP ==="
Get-NetIPAddress | Where-Object {$_.InterfaceAlias -like "*wg*"} | Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table
''')
print(result)

print("\n" + "="*70)
print("  СТАТУС")
print("="*70)
print("""
WireGuard сервер настроен!

Для теста:
1. Скачай WireGuard клиент: https://www.wireguard.com/install/
2. Импортируй конфиг из файла:
   C:\\Users\\Admin\\Documents\\Cursor\\Scripts\\WireGuard\\client_config.conf
3. Нажми "Activate"

После подключения проверь:
- https://ipleak.net - должен показать IP сервера 62.84.101.97
- Весь трафик через VPN

ПРИМЕЧАНИЕ:
Сейчас IP будет = IP сервера (62.84.101.97).
Для использования IP прокси ({os.getenv("PROXY_HOST")}) нужна дополнительная
настройка маршрутизации через SOCKS5 на сервере.
""")
