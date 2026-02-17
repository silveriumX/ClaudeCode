#!/usr/bin/env python3
"""
Upload sheets.py to VPS using paramiko (SFTP)
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
VPS_HOST = "195.177.94.189"
VPS_USER = "root"
VPS_PATH = "/root/finance_bot"
LOCAL_FILE = r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\sheets.py"

def main():
    if not os.path.exists(LOCAL_FILE):
        print(f"ERROR: Local file not found: {LOCAL_FILE}")
        sys.exit(1)

    print(f"Connecting to {VPS_USER}@{VPS_HOST}...")

    # Get password
    import getpass
    password = getpass.getpass(f"Password for {VPS_USER}@{VPS_HOST}: ")

    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect with password
        ssh.connect(VPS_HOST, username=VPS_USER, password=password, timeout=10)
        print("✓ Connected")

        # Step 1: Create backup
        print("\nStep 1: Creating backup...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {VPS_PATH} && cp sheets.py sheets.py.backup_$(date +%Y%m%d_%H%M%S) && ls -lh sheets.py*"
        )
        print(stdout.read().decode())
        error = stderr.read().decode()
        if error:
            print(f"Error: {error}")

        # Step 2: Upload file
        print("\nStep 2: Uploading file via SFTP...")
        sftp = ssh.open_sftp()
        remote_temp = f"{VPS_PATH}/sheets.py.new"
        sftp.put(LOCAL_FILE, remote_temp)
        sftp.close()
        print(f"✓ Uploaded to {remote_temp}")

        # Step 3: Replace file
        print("\nStep 3: Replacing file...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {VPS_PATH} && mv sheets.py.new sheets.py && ls -lh sheets.py"
        )
        print(stdout.read().decode())

        # Step 4: Check lines 121-123
        print("\nStep 4: Checking lines 121-123...")
        stdin, stdout, stderr = ssh.exec_command(
            f"sed -n '121,123p' {VPS_PATH}/sheets.py"
        )
        lines = stdout.read().decode()
        print(lines)

        # Step 5: Restart bot
        print("\nStep 5: Restarting bot...")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl restart finance_bot && sleep 3 && systemctl status finance_bot --no-pager -n 10"
        )
        print(stdout.read().decode())

        # Step 6: Check logs
        print("\nStep 6: Checking logs...")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u finance_bot -n 30 --no-pager | tail -20"
        )
        print(stdout.read().decode())

        print("\n=== DONE ===")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
