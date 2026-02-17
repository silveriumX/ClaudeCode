#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Get ALL errors from last cycle
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Get ALL errors (not just connection errors)
print("=" * 70)
print("ВСЕ ОШИБКИ (14:35:32 - 14:40:49)")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep 'ERROR' | grep -v 'Telegram'")
all_errors = stdout.read().decode('utf-8', errors='replace')
print(all_errors)

# Count errors by type
print("\n" + "=" * 70)
print("ПОДСЧЕТ ОШИБОК ПО ТИПАМ")
print("=" * 70)

stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep -c 'SSH connection failed' || echo 0")
ssh_failed = stdout.read().decode('utf-8', errors='replace').strip()

stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep -c 'WinRM error' || echo 0")
winrm_failed = stdout.read().decode('utf-8', errors='replace').strip()

stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep -c 'JSON parse error' || echo 0")
json_errors = stdout.read().decode('utf-8', errors='replace').strip()

stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep -c 'Exception.*client' || echo 0")
client_exceptions = stdout.read().decode('utf-8', errors='replace').strip()

print(f"SSH connection failed: {ssh_failed}")
print(f"WinRM fallback errors: {winrm_failed}")
print(f"JSON parse errors: {json_errors}")
print(f"Client exceptions: {client_exceptions}")

total_errors = int(ssh_failed) + int(winrm_failed) + int(json_errors) + int(client_exceptions)
print(f"\n📊 Всего ERROR логов: {total_errors}")
print(f"📊 Цикл показал: 10 ошибок")
print(f"📊 Разница: {10 - total_errors} (возможно, ошибки данных или timeout)")

client.close()

print("\n" + "=" * 70)
print("✓ АНАЛИЗ ЗАВЕРШЕН")
print("=" * 70)
