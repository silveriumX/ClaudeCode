#!/usr/bin/env python3
"""
Откат изменений и восстановление доступа к прокси
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.getenv("VPS_WIN_HOST"), username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=10, look_for_keys=False)

cmd = r'''
Write-Output "=== ДИАГНОСТИКА И ВОССТАНОВЛЕНИЕ СЕТИ ==="

# 1. Остановить tun2socks
Write-Output ""
Write-Output "1. Stopping tun2socks..."
Stop-Process -Name tun2socks -Force -ErrorAction SilentlyContinue
Write-Output "Done"

# 2. Удалить tun0 адаптер если есть
Write-Output ""
Write-Output "2. Removing tun0 adapter..."
$tun = Get-NetAdapter | Where-Object {$_.Name -eq "tun0"}
if ($tun) {
    Disable-NetAdapter -Name "tun0" -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "tun0 disabled"
}

# 3. Проверить маршруты
Write-Output ""
Write-Output "3. Current routes:"
route print 0.0.0.0 | Select-String "0.0.0.0"

# 4. Удалить лишние маршруты к прокси если добавлялись
Write-Output ""
Write-Output "4. Removing custom routes..."
route delete {os.getenv("PROXY_HOST")} 2>$null

# 5. Проверить NAT
Write-Output ""
Write-Output "5. NAT configuration:"
Get-NetNat | Format-Table Name, InternalIPInterfaceAddressPrefix, Active

# 6. Проверить firewall
Write-Output ""
Write-Output "6. Checking if proxy IP is blocked..."
$rules = Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*proxy*" -or $_.DisplayName -like "*185.162*"}
if ($rules) {
    Write-Output "Found rules:"
    $rules | Select-Object DisplayName, Direction, Action
} else {
    Write-Output "No blocking rules found"
}

# 7. Тест прокси
Write-Output ""
Write-Output "7. Testing proxy..."
$result = curl.exe -x "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10000" -s --connect-timeout 15 https://api.ipify.org 2>&1
Write-Output "PROXY_RESULT:$result"

# 8. TCP тест
Write-Output ""
Write-Output "8. TCP test to proxy..."
$tcp = Test-NetConnection -ComputerName {os.getenv("PROXY_HOST")} -Port 10000 -WarningAction SilentlyContinue
Write-Output "TCP:$($tcp.TcpTestSucceeded)"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=120)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
