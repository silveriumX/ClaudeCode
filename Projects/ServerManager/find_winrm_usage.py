#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Find where WinRM connector is still used
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Check server_monitor.py for WinRM imports/usage
print("=" * 70)
print("server_monitor.py - импорты и использование WinRM")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("grep -n 'winrm\\|WinRM' /opt/server-monitor/server_monitor.py || echo 'Not found'")
winrm_in_monitor = stdout.read().decode('utf-8', errors='replace')
print(winrm_in_monitor)

# Check for any fallback logic
print("\n" + "=" * 70)
print("ПОИСК: fallback логика в server_monitor.py")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("grep -n 'fallback\\|except.*:' /opt/server-monitor/server_monitor.py | head -20")
fallback = stdout.read().decode('utf-8', errors='replace')
print(fallback)

# Check session_checker if it exists and uses WinRM
print("\n" + "=" * 70)
print("session_checker.py - использует ли WinRM?")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("grep -n 'winrm\\|WinRM' /opt/server-monitor/session_checker.py || echo 'Not found'")
session_winrm = stdout.read().decode('utf-8', errors='replace')
print(session_winrm)

# Check if session_checker is imported in server_monitor.py
print("\n" + "=" * 70)
print("server_monitor.py - импортирует session_checker?")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("grep -n 'session_checker\\|SessionChecker' /opt/server-monitor/server_monitor.py")
session_import = stdout.read().decode('utf-8', errors='replace')
print(session_import if session_import else "SessionChecker не импортируется")

client.close()

print("\n" + "=" * 70)
print("✓ ПОИСК ЗАВЕРШЕН")
print("=" * 70)
