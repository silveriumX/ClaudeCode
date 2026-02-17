#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Analyze errors in current cycle
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Get all errors from current cycle
print("=" * 70)
print("ВСЕ ОШИБКИ ТЕКУЩЕГО ЦИКЛА (14:25:52 - 14:31:54)")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep 'ERROR'")
errors = stdout.read().decode('utf-8', errors='replace')
print(errors)

# Get all warnings
print("\n" + "=" * 70)
print("ВСЕ ПРЕДУПРЕЖДЕНИЯ")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep 'WARNING' | head -20")
warnings = stdout.read().decode('utf-8', errors='replace')
print(warnings)

# Check server results
print("\n" + "=" * 70)
print("РЕЗУЛЬТАТЫ СЕРВЕРОВ (логи из кода)")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '14:25:52' --no-pager | grep '\\[.*\\]' | tail -20")
results = stdout.read().decode('utf-8', errors='replace')
print(results if results else "Нет результатов с форматом [IP]")

client.close()

print("\n" + "=" * 70)
print("✓ АНАЛИЗ ЗАВЕРШЕН")
print("=" * 70)
