#!/usr/bin/env python3
import base64, io, os, sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

VPS_WIN_HOST = os.getenv("VPS_WIN_HOST")
VPS_WIN_PASSWORD = os.getenv("VPS_WIN_PASSWORD")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
PROXY_URL = f"socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(VPS_WIN_HOST, username='Administrator', password=VPS_WIN_PASSWORD, timeout=10, look_for_keys=False)

cmd = r'''
Write-Output "=== Checking WSL ==="
$wsl = Get-Command wsl -ErrorAction SilentlyContinue
if ($wsl) {
    Write-Output "WSL installed"
    wsl --list --verbose 2>&1
} else {
    Write-Output "WSL not installed"
}

Write-Output ""
Write-Output "=== Alternative: Use Proxifier in interactive session ==="
Write-Output "Proxifier is GUI-based and works when user is logged in."
Write-Output ""
Write-Output "Checking Proxifier..."

$proxifier = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
if (Test-Path $proxifier) {
    Write-Output "Proxifier: Installed"

    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "Proxifier: RUNNING (PID=$($proc.Id))"
    } else {
        Write-Output "Proxifier: Not running"
    }
} else {
    Write-Output "Proxifier: Not installed"
}

Write-Output ""
Write-Output "=== Quick test: proxy still works? ==="
''' + f'$ip = curl.exe -x "{PROXY_URL}" -s --max-time 10 https://api.ipify.org 2>$null\n' + r'''Write-Output "Proxy IP: $ip"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
