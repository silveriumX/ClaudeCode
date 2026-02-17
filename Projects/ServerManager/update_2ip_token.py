#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Скрипт для обновления токена 2IP.io на VPS
"""
import paramiko
import sys
import os

from pathlib import Path
import sys

def load_credentials():
    """Загрузка credentials из файла .credentials"""
    creds_file = Path(__file__).resolve().parent / ".credentials"
    creds = {}
    if not creds_file.exists():
        return creds
    with creds_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                creds[key.strip()] = value.strip()
    return creds

# Load credentials from file
_creds = load_credentials()
VPS_HOST = _creds.get('VPS_HOST', '151.241.154.57')
VPS_USER = _creds.get('VPS_USER', 'root')
VPS_PASSWORD = os.getenv("VPS_WIN_PASSWORD")
VPS_PORT = int(_creds.get('VPS_PORT', 22))

# New token
NEW_TOKEN = "pbkydkrfxx3yas61"

def main():
    print(f"[*] Connecting to {VPS_HOST}...")

    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[OK] Connected!\n")

        # 1. Check current .env file
        print("[*] Checking current .env file...")
        stdin, stdout, stderr = client.exec_command("cat /opt/server-monitor/.env")
        current_env = stdout.read().decode()
        print("Current .env content:")
        print("=" * 60)
        print(current_env)
        print("=" * 60)

        # 2. Check current token
        stdin, stdout, stderr = client.exec_command("grep API_TOKEN_2IP /opt/server-monitor/.env")
        current_token_line = stdout.read().decode().strip()
        print(f"\n[INFO] Current token line: {current_token_line}")

        # 3. Update token
        print(f"\n[*] Updating token to: {NEW_TOKEN}")
        update_cmd = f'sed -i "s/API_TOKEN_2IP=.*/API_TOKEN_2IP={NEW_TOKEN}/" /opt/server-monitor/.env'
        stdin, stdout, stderr = client.exec_command(update_cmd)
        stdout.channel.recv_exit_status()

        # 4. Verify update
        print("[*] Verifying update...")
        stdin, stdout, stderr = client.exec_command("grep API_TOKEN_2IP /opt/server-monitor/.env")
        new_token_line = stdout.read().decode().strip()
        print(f"[OK] New token line: {new_token_line}")

        # 5. Check all services status
        print("\n[*] Checking services status...")
        services = ['server-monitor', 'command-webhook', 'proxyma-monitor']

        for service in services:
            stdin, stdout, stderr = client.exec_command(f"systemctl is-active {service}")
            status = stdout.read().decode().strip()
            print(f"  {service}: {status}")

        # 6. Restart server-monitor service to apply new token
        print("\n[*] Restarting server-monitor service...")
        stdin, stdout, stderr = client.exec_command("systemctl restart server-monitor")
        stdout.channel.recv_exit_status()
        print("[OK] Service restarted")

        # 7. Check if service started successfully
        import time
        time.sleep(2)
        stdin, stdout, stderr = client.exec_command("systemctl is-active server-monitor")
        status = stdout.read().decode().strip()

        if status == "active":
            print("[SUCCESS] server-monitor is running!")
        else:
            print(f"[WARN] server-monitor status: {status}")

        # 8. Show recent logs
        print("\n[*] Recent server-monitor logs:")
        stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor -n 20 --no-pager")
        logs = stdout.read().decode()
        print(logs)

        print("\n" + "=" * 60)
        print("[SUCCESS] Token update completed!")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
