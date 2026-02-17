#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Verify COMPLETE SSH migration - no more WinRM errors
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Check for "Failed to create shell" errors since migration
print("=" * 70)
print("ПРОВЕРКА: 'Failed to create shell' с 14:46:12")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:46:12' --no-pager | grep -c 'Failed to create shell' || echo 0")
shell_errors = stdout.read().decode('utf-8', errors='replace').strip().split('\n')[-1]
print(f"Ошибок 'Failed to create shell': {shell_errors}")

if int(shell_errors) == 0:
    print("✅ ОТЛИЧНО! Ошибок нет - WinRM полностью отключен!")
else:
    print(f"⚠️  Еще есть {shell_errors} ошибок WinRM")

# Check successful SSH connections
print("\n" + "=" * 70)
print("SSH ПОДКЛЮЧЕНИЯ с 14:46:12")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:46:12' --no-pager | grep -c 'Authentication.*successful' || echo 0")
ssh_success = stdout.read().decode('utf-8', errors='replace').strip()
print(f"✅ Успешных SSH подключений: {ssh_success}")

# Check last 30 lines
print("\n" + "=" * 70)
print("ПОСЛЕДНИЕ 30 СТРОК ЛОГА")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor -n 30 --no-pager")
logs = stdout.read().decode('utf-8', errors='replace')
print(logs)

client.close()

print("\n" + "=" * 70)
print("✓ ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 70)
