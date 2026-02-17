#!/usr/bin/env python3
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('89.110.121.89', username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=15)
print("✓ SSH Connected\n")

print("Restarting WinRM...")
stdin, stdout, stderr = client.exec_command(
    'powershell -Command "Restart-Service WinRM -Force; Start-Sleep 2; Get-Service WinRM | Select-Object -ExpandProperty Status"',
    timeout=15
)
print(f"  WinRM Status: {stdout.read().decode().strip()}")

client.close()
print("\nTesting from VPS...")
