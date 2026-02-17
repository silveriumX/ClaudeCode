#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Find where "Failed to create shell" comes from
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Search for "Failed to create shell" in all Python files
print("=" * 70)
print("ПОИСК: 'Failed to create shell' в коде")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("grep -rn 'Failed to create shell' /opt/server-monitor/ --include='*.py'")
search_result = stdout.read().decode('utf-8', errors='replace')
print(search_result if search_result else "НЕ НАЙДЕНО в коде")

# Check which files import paramiko
print("\n" + "=" * 70)
print("ФАЙЛЫ ИСПОЛЬЗУЮЩИЕ paramiko")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("grep -l 'import paramiko' /opt/server-monitor/*.py")
paramiko_files = stdout.read().decode('utf-8', errors='replace')
print(paramiko_files)

client.close()

print("\n" + "=" * 70)
print("✓ ПОИСК ЗАВЕРШЕН")
print("=" * 70)
