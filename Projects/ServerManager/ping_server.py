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
client.connect(os.getenv("VPS_DOWNLOAD_HOST"), username='root', password=os.getenv("VPS_DOWNLOAD_PASSWORD"), timeout=15)

ip = "77.83.39.202"
print(f"Checking connectivity to {ip}...\n")

# Ping
stdin, stdout, stderr = client.exec_command(f"ping -c 3 {ip}")
print("Ping:")
print(stdout.read().decode())

# Port check
stdin, stdout, stderr = client.exec_command(f"timeout 5 bash -c 'echo >/dev/tcp/{ip}/5985' 2>&1 && echo 'Port 5985 OPEN' || echo 'Port 5985 CLOSED/FILTERED'")
print("\nPort 5985:")
print(stdout.read().decode())

# Try curl
stdin, stdout, stderr = client.exec_command(f"curl -s --connect-timeout 5 http://{ip}:5985/wsman 2>&1 | head -5")
print("Curl test:")
print(stdout.read().decode())

client.close()
