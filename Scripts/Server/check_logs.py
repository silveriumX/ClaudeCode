#!/usr/bin/env python3
"""
Check bot logs - ASCII only
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import sys
import paramiko
import re

def check_logs():
    """Check bot logs"""
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password, timeout=10)

        # Status
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode('utf-8').strip()
        print(f"Bot Status: {status}")

        # Recent logs (last 40 lines)
        print("\nRecent Logs:")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 40 --no-pager")
        logs = stdout.read().decode('utf-8', errors='ignore')

        # Remove emojis and special chars
        logs_clean = re.sub(r'[^\x00-\x7F]+', '?', logs)
        print(logs_clean)

        # Check for errors
        print("\n" + "=" * 80)
        print("Checking for errors...")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 50 --no-pager | grep -i 'error\\|exception\\|failed\\|traceback'")
        errors = stdout.read().decode('utf-8', errors='ignore').strip()

        if errors:
            print("ERRORS FOUND:")
            errors_clean = re.sub(r'[^\x00-\x7F]+', '?', errors)
            print(errors_clean)
        else:
            print("No errors found!")

        ssh.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    check_logs()
