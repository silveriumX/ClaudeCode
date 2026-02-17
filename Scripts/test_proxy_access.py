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
Write-Output "=== Testing proxy connectivity ==="

# Test TCP connection
Write-Output "Testing TCP to {os.getenv("PROXY_HOST")}:10001..."
$tcp = Test-NetConnection -ComputerName {os.getenv("PROXY_HOST")} -Port 10001 -WarningAction SilentlyContinue
Write-Output "TCP_TEST:$($tcp.TcpTestSucceeded)"
Write-Output "PING:$($tcp.PingSucceeded)"

# Test with curl directly
Write-Output ""
Write-Output "Testing curl with SOCKS5 proxy..."
$result = curl.exe -x "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10001" -s --connect-timeout 15 https://api.ipify.org 2>&1
Write-Output "CURL_RESULT:$result"

# Test without proxy
Write-Output ""
Write-Output "Current server IP:"
$serverIp = curl.exe -s --max-time 5 https://api.ipify.org 2>$null
Write-Output "SERVER_IP:$serverIp"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=90)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
