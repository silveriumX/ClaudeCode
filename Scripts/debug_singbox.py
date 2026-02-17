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
$exe = "C:\sing-box\sing-box.exe"
$config = "C:\sing-box\config.json"

Write-Output "=== Checking files ==="
Write-Output "exe exists: $(Test-Path $exe)"
Write-Output "config exists: $(Test-Path $config)"

Write-Output ""
Write-Output "=== Trying to run directly ==="
Set-Location "C:\sing-box"

# Запустить и показать вывод (с таймаутом)
$output = & $exe run -c $config 2>&1 | Select-Object -First 20
Write-Output $output
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=30)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
