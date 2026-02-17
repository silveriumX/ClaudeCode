#!/usr/bin/env python3
"""
Test my_requests command on VPS via logs
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


import paramiko
import sys
import io
from time import sleep

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = os.getenv("VPS_LINUX_HOST")
USERNAME = "root"
PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

client = None

try:
    print(f"[*] Connecting to {HOST}...")

    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect
    client.connect(HOST, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] Connected!\n")

    # Check if bot is running
    print("[*] Checking bot status...")
    stdin, stdout, stderr = client.exec_command("systemctl status finance_bot --no-pager")
    status = stdout.read().decode('utf-8', errors='replace')

    if "active (running)" in status:
        print("[+] Bot is running")
    else:
        print("[-] Bot is not running!")
        print(status)
        sys.exit(1)

    # Get recent logs for "мои заявки" or "my_requests"
    print("\n[*] Checking recent logs for 'Мои заявки' command...")
    stdin, stdout, stderr = client.exec_command(
        "journalctl -u finance_bot --since '2 minutes ago' --no-pager | grep -i 'заявок\\|my_requests' | tail -20"
    )

    logs = stdout.read().decode('utf-8', errors='replace')
    if logs.strip():
        print("Recent activity:")
        print(logs)
    else:
        print("No recent activity for 'Мои заявки' command")

    # Get any errors in last 2 minutes
    print("\n[*] Checking for errors...")
    stdin, stdout, stderr = client.exec_command(
        "journalctl -u finance_bot --since '2 minutes ago' --no-pager | grep -i 'ошибка\\|error\\|traceback' | tail -20"
    )

    errors = stdout.read().decode('utf-8', errors='replace')
    if errors.strip():
        print("⚠️ Found errors:")
        print(errors)
    else:
        print("✅ No errors in last 2 minutes")

    print("\n" + "="*80)
    print("Instructions:")
    print("1. Open Telegram and go to your Finance Bot")
    print("2. Click '📋 Мои заявки' button")
    print("3. Check if it works without errors")
    print("="*80)

except paramiko.AuthenticationException:
    print("[-] Authentication failed.")
    sys.exit(1)
except Exception as e:
    print(f"[-] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    if client:
        client.close()
