#!/usr/bin/env python3
"""
Update USDT sheet structure to include author fields
Adds columns J, K, L for Telegram ID, Username, and FullName
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

def main():
    workspace = Path.cwd()
    print(f"[*] Workspace: {workspace}")

    local_file = workspace / "Projects/FinanceBot/sheets.py"
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

        # Upload sheets.py
        print(f"\n[*] Uploading {local_file} -> {REMOTE_PATH}/sheets.py")
        sftp.put(str(local_file), f"{REMOTE_PATH}/sheets.py")
        print(f"[+] Uploaded successfully")

        sftp.close()

        # Restart bot
        print("\n[*] Restarting finance_bot service...")
        stdin, stdout, stderr = client.exec_command("systemctl restart finance_bot")
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            print("[+] Service restarted successfully")
        else:
            error = stderr.read().decode('utf-8')
            print(f"[-] Error restarting service: {error}")
            sys.exit(1)

        # Wait for bot to start
        import time
        time.sleep(3)

        # Check logs
        print("\n[*] Checking recent logs...")
        stdin, stdout, stderr = client.exec_command(
            "journalctl -u finance_bot -n 30 --no-pager"
        )

        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        print("\n" + "="*80)
        print("[+] Deployment completed successfully!")
        print("="*80)
        print("\n📋 Изменения:")
        print("   • Лист USDT теперь имеет 12 колонок (A-L) вместо 9")
        print("   • Добавлены колонки J, K, L для данных инициатора:")
        print("     - J: Telegram ID инициатора")
        print("     - K: Username инициатора")
        print("     - L: Полное имя инициатора")
        print("\n⚠️  ВАЖНО:")
        print("   • Старые заявки в листе USDT НЕ имеют данных инициатора")
        print("   • Новые заявки будут создаваться с данными инициатора")
        print("   • Теперь фильтрация 'Мои заявки' работает для всех валют!")

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

if __name__ == "__main__":
    main()
