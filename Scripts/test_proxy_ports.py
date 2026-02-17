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
Write-Output "=== Testing different proxy ports ==="

$host = os.getenv("PROXY_HOST")
$ports = @(10001, 10000, 10002, 10003, 10004, 10010, 1080, 8080)
$user = os.getenv("PROXY_USER")
$pass = os.getenv("PROXY_PASS")

foreach ($port in $ports) {
    Write-Output ""
    Write-Output "Testing port $port..."

    # Quick TCP test (timeout 3 sec)
    $tcp = Test-NetConnection -ComputerName $host -Port $port -WarningAction SilentlyContinue

    if ($tcp.TcpTestSucceeded) {
        Write-Output "PORT_$port`:TCP_OK"

        # Try curl
        $proxyUrl = "socks5://${user}:${pass}@${host}:${port}"
        $ip = curl.exe -x $proxyUrl -s --connect-timeout 10 https://api.ipify.org 2>$null
        if ($ip) {
            Write-Output "PORT_$port`:WORKS - IP=$ip"
        } else {
            Write-Output "PORT_$port`:TCP_OK but curl failed"
        }
    } else {
        Write-Output "PORT_$port`:CLOSED"
    }
}

Write-Output ""
Write-Output "=== Ping test ==="
$ping = Test-Connection -ComputerName $host -Count 1 -ErrorAction SilentlyContinue
if ($ping) {
    Write-Output "PING:OK ($($ping.ResponseTime)ms)"
} else {
    Write-Output "PING:FAILED - Host may be blocking ICMP or unreachable"
}
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=180)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
