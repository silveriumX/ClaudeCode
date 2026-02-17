#!/usr/bin/env python3
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
Write-Output "         ТЕКУЩИЙ СТАТУС"
Write-Output "=========================================="

# WireGuard
Write-Output ""
Write-Output "=== WireGuard ==="
$wgSvc = Get-Service WireGuardTunnel* -ErrorAction SilentlyContinue
if ($wgSvc) {
    Write-Output "Service: $($wgSvc.Name) = $($wgSvc.Status)"
}

$wg = "C:\Program Files\WireGuard\wg.exe"
if (Test-Path $wg) {
    & $wg show 2>&1
}

# Прокси тест
Write-Output ""
Write-Output "=== Прокси ==="
$proxyIp = curl.exe -x "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10000" -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "Proxy test IP: $proxyIp"

# Текущий IP сервера
Write-Output ""
Write-Output "=== IP сервера ==="
$serverIp = curl.exe -s --max-time 5 https://api.ipify.org 2>$null
Write-Output "Server IP: $serverIp"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
