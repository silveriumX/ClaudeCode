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
Write-Output "=== Stopping tun2socks ==="
Stop-Process -Name tun2socks -Force -ErrorAction SilentlyContinue
Start-Sleep 2

Write-Output "tun2socks stopped"

Write-Output ""
Write-Output "=== Testing proxy WITHOUT tun2socks ==="

# Test curl with proxy
Write-Output "Testing curl..."
$result = curl.exe -x "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10001" -s --connect-timeout 20 https://api.ipify.org 2>&1
Write-Output "PROXY_IP:$result"

# Test TCP
Write-Output ""
Write-Output "Testing TCP connection..."
$tcp = Test-NetConnection -ComputerName {os.getenv("PROXY_HOST")} -Port 10001 -WarningAction SilentlyContinue
Write-Output "TCP:$($tcp.TcpTestSucceeded)"

# Current IP
Write-Output ""
$ip = curl.exe -s --max-time 5 https://api.ipify.org 2>$null
Write-Output "SERVER_IP:$ip"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=90)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
