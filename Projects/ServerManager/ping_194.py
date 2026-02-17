#!/usr/bin/env python3
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(os.getenv("VPS_DOWNLOAD_HOST"), username='root', password=os.getenv("VPS_DOWNLOAD_PASSWORD"), timeout=15)

ip = "194.59.30.150"

print(f"Проверка доступности {ip}:\n")

# Ping
stdin, stdout, stderr = client.exec_command(f"ping -c 3 {ip}")
print("Ping:")
print(stdout.read().decode())

# Port 22 (SSH)
stdin, stdout, stderr = client.exec_command(f"timeout 3 bash -c 'echo >/dev/tcp/{ip}/22' && echo 'Port 22: OPEN' || echo 'Port 22: CLOSED'")
print(stdout.read().decode())

# Port 3389 (RDP)
stdin, stdout, stderr = client.exec_command(f"timeout 3 bash -c 'echo >/dev/tcp/{ip}/3389' && echo 'Port 3389: OPEN' || echo 'Port 3389: CLOSED'")
print(stdout.read().decode())

# Port 5985 (WinRM)
stdin, stdout, stderr = client.exec_command(f"timeout 3 bash -c 'echo >/dev/tcp/{ip}/5985' && echo 'Port 5985: OPEN' || echo 'Port 5985: CLOSED'")
print(stdout.read().decode())

client.close()
