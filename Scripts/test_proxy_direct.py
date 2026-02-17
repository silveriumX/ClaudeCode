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

# Тест прокси напрямую
cmd = r'''
$proxyUrl = "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10001"
$ip = curl.exe -x $proxyUrl -s --max-time 15 https://api.ipify.org 2>$null
Write-Output "PROXY_IP:$ip"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=30)
print('Direct proxy test:')
print(o.read().decode('utf-8', errors='ignore').strip())
c.close()
