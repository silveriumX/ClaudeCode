#!/usr/bin/env python3
"""
Deploy Finance Bot updates to VPS
Uploads: sheets.py, handlers/request.py, handlers/start.py, config.py
"""
import sys
import os
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed. Install: pip install paramiko")
    sys.exit(1)

# Configuration
VPS_HOST = "45.12.72.147"
VPS_USER = "root"
VPS_PATH = "/root/finance_bot"
LOCAL_BASE = r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot"

FILES_TO_UPLOAD = [
    "sheets.py",
    "handlers/request.py",
    "handlers/start.py",
    "config.py"
]

def main():
    print("=== Finance Bot Deploy ===\n")

    # Check all files exist
    for file in FILES_TO_UPLOAD:
        local_path = Path(LOCAL_BASE) / file
        if not local_path.exists():
            print(f"ERROR: Local file not found: {local_path}")
            sys.exit(1)

    print(f"Connecting to {VPS_USER}@{VPS_HOST}...")

    # Get password
    import getpass
    password = getpass.getpass(f"Password for {VPS_USER}@{VPS_HOST}: ")

    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect
        ssh.connect(VPS_HOST, username=VPS_USER, password=password, timeout=10)
        print("OK Connected\n")

        # Open SFTP
        sftp = ssh.open_sftp()

        # Upload each file
        for file in FILES_TO_UPLOAD:
            local_path = Path(LOCAL_BASE) / file
            remote_path = f"{VPS_PATH}/{file}"

            print(f"Uploading {file}...")

            # Create backup of existing file
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    f"[ -f {remote_path} ] && cp {remote_path} {remote_path}.backup_$(date +%Y%m%d_%H%M%S) || true"
                )
                stdout.read()
            except:
                pass

            # Upload file
            sftp.put(str(local_path), remote_path)
            print(f"  OK {file} uploaded")

        sftp.close()

        # Restart bot
        print("\nRestarting bot...")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl restart financebot && sleep 3 && systemctl status financebot --no-pager -n 10"
        )
        status_output = stdout.read().decode()
        print(status_output)

        # Check logs
        print("\nChecking recent logs...")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u financebot -n 30 --no-pager | tail -20"
        )
        logs = stdout.read().decode()
        print(logs)

        if "error" in logs.lower() or "exception" in logs.lower():
            print("\n[WARNING] Possible errors detected in logs!")
        else:
            print("\n[SUCCESS] Bot deployed and running!")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
