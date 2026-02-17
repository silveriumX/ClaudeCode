#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Get detailed error breakdown
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Get all errors from last cycle (14:35:32 - 14:40:49)
print("=" * 70)
print("ВСЕ ОШИБКИ ПОСЛЕДНЕГО ЦИКЛА")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep -E 'ERROR.*for [0-9]|SSH connection failed|JSON parse'")
errors = stdout.read().decode('utf-8', errors='replace')
print(errors if errors else "Нет ошибок подключения")

# Get server results summaries
print("\n" + "=" * 70)
print("РЕЗУЛЬТАТЫ ПО СЕРВЕРАМ (INFO логи)")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep '\\[.*\\] (OK|ERROR)' | tail -20")
server_results = stdout.read().decode('utf-8', errors='replace')
print(server_results if server_results else "Нет INFO логов с результатами")

# Check if data is being sent to Google Sheets
print("\n" + "=" * 70)
print("ОБНОВЛЕНИЯ GOOGLE SHEETS")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:35:32' --until '14:40:50' --no-pager | grep -i 'sheets\\|updated' | head -10")
sheets_updates = stdout.read().decode('utf-8', errors='replace')
print(sheets_updates if sheets_updates else "Нет логов об обновлении Google Sheets")

client.close()

print("\n" + "=" * 70)
print("✓ АНАЛИЗ ЗАВЕРШЕН")
print("=" * 70)
