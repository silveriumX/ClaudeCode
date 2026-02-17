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
Write-Output "=== Testing proxy {os.getenv("PROXY_HOST")}:10000 ==="

$host = os.getenv("PROXY_HOST")
$port = 10000
$user = os.getenv("PROXY_USER")
$pass = os.getenv("PROXY_PASS")

# TCP test
Write-Output "TCP test..."
$tcp = Test-NetConnection -ComputerName $host -Port $port -WarningAction SilentlyContinue
Write-Output "TCP:$($tcp.TcpTestSucceeded)"

if ($tcp.TcpTestSucceeded) {
    Write-Output ""
    Write-Output "Testing curl through proxy..."
    $proxyUrl = "socks5://${user}:${pass}@${host}:${port}"
    $ip = curl.exe -x $proxyUrl -s --connect-timeout 15 https://api.ipify.org 2>$null
    Write-Output "PROXY_IP:$ip"

    if ($ip -and $ip -ne "62.84.101.97") {
        Write-Output ""
        Write-Output "=========================================="
        Write-Output "SUCCESS! Proxy works!"
        Write-Output "IP through proxy: $ip"
        Write-Output "=========================================="
    }
} else {
    Write-Output "PROXY:Not reachable"
}
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
