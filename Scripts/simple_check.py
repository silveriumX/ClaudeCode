#!/usr/bin/env python3
import os
import base64, io, os, sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

VPS_WIN_HOST = os.getenv("VPS_WIN_HOST")
VPS_WIN_PASSWORD = os.getenv("VPS_WIN_PASSWORD")

def ssh(cmd, timeout=30):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(VPS_WIN_HOST, username="Administrator", password=VPS_WIN_PASSWORD, timeout=10, look_for_keys=False)
        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}", timeout=timeout)
        r = o.read().decode("utf-8", errors="ignore").strip()
        c.close()
        return r
    except Exception as e:
        return f"ERROR: {e}"

print("Check 1: Proxifier process")
print(ssh('Get-Process Proxifier -EA 0 | Select Id,SessionId | Format-List'))

print("\nCheck 2: External IP (short timeout)")
print(ssh('curl.exe -s --max-time 5 https://api.ipify.org 2>$null', 15))

print("\nCheck 3: Connections to proxy")
print(ssh('Get-NetTCPConnection -RemoteAddress {os.getenv("PROXY_HOST")} -EA 0 | Select RemotePort,State | Format-Table'))
