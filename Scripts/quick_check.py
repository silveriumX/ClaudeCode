#!/usr/bin/env python3
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

def ssh(cmd):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(os.getenv("VPS_WIN_HOST"), username="Administrator", password=os.getenv("VPS_WIN_PASSWORD"), timeout=15, look_for_keys=False)
    enc = base64.b64encode(cmd.encode('utf-16le')).decode()
    _, o, _ = c.exec_command(f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}", timeout=60)
    r = o.read().decode("utf-8", errors="ignore").strip()
    c.close()
    return r

print("="*60)
print("QUICK CHECK")
print("="*60)

result = ssh(r'''
# Процесс
$p = Get-Process Proxifier -EA 0
Write-Output "PROXIFIER:$(if($p){'PID='+$p.Id+' Session='+$p.SessionId}else{'NOT_RUNNING'})"

# IP
$ip = curl.exe -s --max-time 20 https://api.ipify.org 2>$null
Write-Output "IP:$ip"

# Соединения
$c = Get-NetTCPConnection -RemoteAddress {os.getenv("PROXY_HOST")} -EA 0
Write-Output "CONNECTIONS:$($c.Count)"

# Прямой тест прокси
Write-Output ""
Write-Output "Direct proxy test:"
$directIp = curl.exe -x "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10001" -s --max-time 20 https://api.ipify.org 2>$null
Write-Output "PROXY_DIRECT:$directIp"
''')

print(result)
print("="*60)
