#!/usr/bin/env python3
"""
Deploy Finance Bot updates to VPS (automatic version)
Uploads: sheets.py, handlers/request.py, handlers/start.py, config.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed. Install: pip install paramiko")
    sys.exit(1)

# Configuration
VPS_HOST = os.getenv("VPS_FINANCE_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_FINANCE_PASSWORD")
VPS_PATH = "/root/finance_bot"
LOCAL_BASE = r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot"

FILES_TO_UPLOAD = [
    "sheets.py",
    "handlers/request.py",
    "handlers/start.py",
    "config.py"
]

def main():
    print("=== Finance Bot Deploy (Auto) ===\n")

    # Check all files exist
    for file in FILES_TO_UPLOAD:
        local_path = Path(LOCAL_BASE) / file
        if not local_path.exists():
            print(f"ERROR: Local file not found: {local_path}")
            sys.exit(1)
        print(f"OK File found: {file}")

    print(f"\nConnecting to {VPS_USER}@{VPS_HOST}...")

    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("OK Connected to VPS\n")

        # Open SFTP
        sftp = ssh.open_sftp()

        # Upload each file
        print("=== Uploading Files ===")
        for file in FILES_TO_UPLOAD:
            local_path = Path(LOCAL_BASE) / file
            remote_path = f"{VPS_PATH}/{file}"

            print(f"\nUploading {file}...")

            # Create backup of existing file
            try:
                backup_cmd = f"[ -f {remote_path} ] && cp {remote_path} {remote_path}.backup_$(date +%Y%m%d_%H%M%S) || true"
                stdin, stdout, stderr = ssh.exec_command(backup_cmd)
                stdout.read()
                print(f"  Backup created")
            except Exception as e:
                print(f"  Warning: Could not create backup: {e}")

            # Upload file
            sftp.put(str(local_path), remote_path)
            print(f"  OK {file} uploaded to {remote_path}")

        sftp.close()
        print("\n=== All Files Uploaded ===")

        # Restart bot
        print("\n=== Restarting Bot ===")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl restart financebot"
        )
        stdout.read()

        # Wait a bit
        import time
        time.sleep(3)

        # Check status
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl status financebot --no-pager -n 15"
        )
        status_output = stdout.read().decode('utf-8', errors='replace')
        print(status_output)

        # Check logs
        print("\n=== Checking Recent Logs ===")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u financebot -n 30 --no-pager"
        )
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        # Check for errors
        logs_lower = logs.lower()
        if "error" in logs_lower or "exception" in logs_lower or "traceback" in logs_lower:
            print("\n[WARNING] Possible errors detected in logs!")
            print("Please check the logs above.")
        else:
            print("\n=== SUCCESS ===")
            print("Bot deployed and running without errors!")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
