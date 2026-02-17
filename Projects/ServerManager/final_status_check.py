#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Final status check - see if SSH monitoring works correctly now
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Check last 200 lines for new cycle
print("=" * 70)
print("ПОСЛЕДНЯЯ ПРОВЕРКА (после 14:25:52)")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:00' --no-pager | tail -80")
logs = stdout.read().decode('utf-8', errors='replace')
print(logs)

# Count successful SSH connections
print("\n" + "=" * 70)
print("СТАТИСТИКА SSH")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep -c 'Authentication.*successful' || echo 0")
ssh_count = stdout.read().decode('utf-8', errors='replace').strip()
print(f"Успешных SSH подключений: {ssh_count}")

# Check for errors
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep -c 'ERROR' || echo 0")
error_count = stdout.read().decode('utf-8', errors='replace').strip()
print(f"Ошибок: {error_count}")

# Check completion
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep 'Check completed' || echo 'Цикл еще не завершен'")
completion = stdout.read().decode('utf-8', errors='replace')
print(f"\nСтатус цикла: {completion if 'Цикл' not in completion else completion}")

client.close()

print("\n" + "=" * 70)
print("✓ ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 70)
