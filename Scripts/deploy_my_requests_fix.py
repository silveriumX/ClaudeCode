#!/usr/bin/env python3
"""
Deploy fix for "my_requests" command to VPS
Fixes the "unsupported format string passed to NoneType" error
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


import paramiko
import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# SSH connection parameters
HOST = os.getenv("VPS_LINUX_HOST")
USERNAME = "root"
PASSWORD = os.getenv("VPS_LINUX_PASSWORD")
REMOTE_PATH = "/root/finance_bot"

# Files to upload
FILES_TO_UPLOAD = [
    "Projects/FinanceBot/sheets.py",
    "Projects/FinanceBot/handlers/request.py",
    "Projects/FinanceBot/handlers/payment.py",
]

def upload_files(sftp, local_base):
    """Upload files to VPS"""
    for file_path in FILES_TO_UPLOAD:
        local_file = local_base / file_path
        remote_file = f"{REMOTE_PATH}/{file_path.split('/')[-1]}"

        if file_path.startswith("Projects/FinanceBot/handlers/"):
            remote_file = f"{REMOTE_PATH}/handlers/{file_path.split('/')[-1]}"

        print(f"[*] Uploading {local_file} -> {remote_file}")

        try:
            sftp.put(str(local_file), remote_file)
            print(f"[+] Uploaded successfully")
        except Exception as e:
            print(f"[-] Error uploading {file_path}: {e}")
            return False

    return True

def restart_bot(ssh):
    """Restart Finance Bot service"""
    print("\n[*] Restarting finance_bot service...")

    stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot")
    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0:
        print("[+] Service restarted successfully")
        return True
    else:
        error = stderr.read().decode('utf-8')
        print(f"[-] Error restarting service: {error}")
        return False

def check_logs(ssh):
    """Check recent logs"""
    print("\n[*] Checking recent logs...")

    stdin, stdout, stderr = ssh.exec_command(
        "journalctl -u finance_bot -n 30 --no-pager"
    )

    logs = stdout.read().decode('utf-8', errors='replace')
    print(logs)

def main():
    # Get workspace path
    workspace = Path.cwd()
    print(f"[*] Workspace: {workspace}")

    # Check if files exist
    for file_path in FILES_TO_UPLOAD:
        local_file = workspace / file_path
        if not local_file.exists():
            print(f"[-] File not found: {local_file}")
            sys.exit(1)

    client = None

    try:
        print(f"\n[*] Connecting to {HOST}...")

        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect
        client.connect(HOST, username=USERNAME, password=PASSWORD, timeout=10)
        print("[+] Connected!")

        # Open SFTP
        sftp = client.open_sftp()

        # Upload files
        if not upload_files(sftp, workspace):
            print("\n[-] Failed to upload files")
            sys.exit(1)

        sftp.close()

        # Restart bot
        if not restart_bot(client):
            print("\n[-] Failed to restart bot")
            sys.exit(1)

        # Wait a bit for bot to start
        import time
        time.sleep(3)

        # Check logs
        check_logs(client)

        print("\n" + "="*80)
        print("[+] Deployment completed successfully!")
        print("="*80)
        print("\nTry using the '📋 Мои заявки' button now.")

    except paramiko.AuthenticationException:
        print("[-] Authentication failed. Check username/password.")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"[-] SSH error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
