#!/usr/bin/env python3
"""
Финальная настройка - GOST как прокси для VPN клиентов
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
Write-Output "=========================================="
Write-Output "    ФИНАЛЬНАЯ НАСТРОЙКА"
Write-Output "=========================================="

# 1. Убедиться что GOST работает
$gost = "C:\gost\gost.exe"
$proc = Get-Process gost* -ErrorAction SilentlyContinue

if (!$proc) {
    Write-Output "Starting GOST..."
    $args = @("-L", "socks5://0.0.0.0:1080", "-F", "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10000")
    Start-Process -FilePath $gost -ArgumentList $args -WindowStyle Hidden
    Start-Sleep 3
}

$proc = Get-Process gost* -ErrorAction SilentlyContinue
Write-Output "GOST: Running (PID=$($proc.Id))"

# 2. Открыть порт 1080 в firewall для VPN подсети
Write-Output ""
Write-Output "Configuring firewall..."
Remove-NetFirewallRule -DisplayName "GOST Proxy" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "GOST Proxy" -Direction Inbound -LocalPort 1080 -Protocol TCP -Action Allow | Out-Null
Write-Output "Firewall: Port 1080 open"

# 3. Создать задачу для автозапуска GOST
Write-Output ""
Write-Output "Setting up autostart..."
$taskName = "GOST_Autostart"
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

$gostArgs = "-L socks5://0.0.0.0:1080 -F socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10000"
schtasks /Create /TN $taskName /TR "`"$gost`" $gostArgs" /SC ONSTART /RU SYSTEM /RL HIGHEST /F 2>&1 | Out-Null
Write-Output "Autostart: Configured"

# 4. Тест
Write-Output ""
Write-Output "=== Testing ==="
$proxyIp = curl.exe -x "socks5://127.0.0.1:1080" -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "IP via GOST proxy: $proxyIp"

# 5. WireGuard статус
Write-Output ""
Write-Output "=== WireGuard ==="
$wg = "C:\Program Files\WireGuard\wg.exe"
& $wg show

Write-Output ""
Write-Output "=========================================="
Write-Output "    ГОТОВО!"
Write-Output "=========================================="
Write-Output ""
Write-Output "VPN: 62.84.101.97:51820"
Write-Output "Proxy: 10.66.66.1:1080 (SOCKS5)"
Write-Output "External IP via proxy: $proxyIp"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
