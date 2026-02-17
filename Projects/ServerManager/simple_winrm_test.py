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
print("[OK] Connected to VPS\n")

# Very simple test
stdin, stdout, stderr = client.exec_command('''
cd /opt/server-monitor && python3 << 'EOF'
from winrm_connector import WinRMConnector
import config

connector = WinRMConnector(timeout=30)
result = connector.execute_command("194.59.31.156", "Administrator", os.getenv("VPS_WIN_PASSWORD"), "hostname")
print(f"Result type: {type(result)}")
print(f"Result repr: {repr(result)}")
print(f"Result len: {len(result) if result else 0}")
EOF
''', timeout=60)

print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

client.close()
