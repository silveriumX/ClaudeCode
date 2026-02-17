#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Get final migration report
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Get cycle completion
print("=" * 70)
print("РЕЗУЛЬТАТ ЦИКЛА ПРОВЕРКИ")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep 'Check completed\\|Loaded.*servers'")
completion = stdout.read().decode('utf-8', errors='replace')
print(completion)

# Count stats
print("\n" + "=" * 70)
print("СТАТИСТИКА SSH ПОДКЛЮЧЕНИЙ")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep -c 'Authentication.*successful' || echo 0")
ssh_success = stdout.read().decode('utf-8', errors='replace').strip()
print(f"✅ Успешных SSH подключений: {ssh_success}")

stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep -c 'SSH connection failed' || echo 0")
ssh_failed = stdout.read().decode('utf-8', errors='replace').strip()
print(f"❌ Неудачных SSH подключений: {ssh_failed}")

# Check for WinRM fallback usage
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep -c 'WinRM error' || echo 0")
winrm_count = stdout.read().decode('utf-8', errors='replace').strip()
print(f"⚠️  WinRM fallback вызовов: {winrm_count}")

# Show last info logs
print("\n" + "=" * 70)
print("ПОСЛЕДНИЕ INFO ЛОГИ (проверки серверов)")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep -E 'Checking [0-9]|\\[.*\\] (OK|ERROR)' | tail -20")
info_logs = stdout.read().decode('utf-8', errors='replace')
print(info_logs)

client.close()

print("\n" + "=" * 70)
print("✅ ОТЧЕТ ГОТОВ")
print("=" * 70)
