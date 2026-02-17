#!/usr/bin/env python3
"""
Check bot status and logs
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import sys
import paramiko

def check_bot():
    """Check bot status and logs"""
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password, timeout=10)

        # Status
        print("=== BOT STATUS ===")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode('utf-8').strip()
        print(f"Status: {status}")

        # Uptime
        stdin, stdout, stderr = ssh.exec_command("systemctl show finance_bot -p ActiveEnterTimestamp")
        uptime = stdout.read().decode('utf-8').strip()
        print(uptime)

        # Recent logs
        print("\n=== RECENT LOGS ===")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 30 --no-pager")
        logs = stdout.read().decode('utf-8', errors='ignore')
        print(logs)

        # Check for errors
        print("\n=== ERRORS ===")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 30 --no-pager | grep -i error")
        errors = stdout.read().decode('utf-8', errors='ignore').strip()
        if errors:
            print(errors)
        else:
            print("No errors found!")

        ssh.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    check_bot()
