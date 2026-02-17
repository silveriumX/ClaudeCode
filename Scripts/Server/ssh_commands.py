#!/usr/bin/env python3
"""
Execute SSH commands on VPS
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import paramiko

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

def run_ssh_commands(commands):
    """Execute SSH commands on VPS"""
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    try:
        # Connect
        print(f"Connecting to {host}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password, timeout=10)
        print("Connected!\n")

        # Execute commands
        for cmd in commands:
            print(f"$ {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            if output:
                print(output)
            if error:
                print(f"Error: {error}", file=sys.stderr)
            print()

        ssh.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    commands = [
        # Backup
        "cd /root/finance_bot && cp sheets.py sheets.py.backup_$(date +%Y%m%d_%H%M%S) && ls -lh sheets.py*",
        # Replace file
        "cd /root/finance_bot && mv sheets.py.new sheets.py && ls -lh sheets.py",
        # Check lines 121-123
        "sed -n '121,123p' /root/finance_bot/sheets.py",
        # Restart bot
        "systemctl restart finance_bot",
        # Wait
        "sleep 3",
        # Check status
        "systemctl status finance_bot --no-pager -n 10",
        # Check logs
        "journalctl -u finance_bot -n 30 --no-pager | tail -20"
    ]

    success = run_ssh_commands(commands)
    sys.exit(0 if success else 1)
