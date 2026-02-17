#!/usr/bin/env python3
"""Fetch Finance Bot logs from VPS"""
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

def fetch_logs():
    # SSH connection parameters
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    # Commands to execute
    commands = [
        ("Search ALL logs for request errors", "journalctl -u finance_bot --no-pager | grep -A 20 -B 5 'получении списка заявок\\|Ошибка получения заявок\\|get_requests_by_status' | tail -200"),
        ("Bot startup and current status", "journalctl -u finance_bot --since today --no-pager | grep -A 5 'Запуск Finance Bot\\|Started Finance Bot\\|Main process exited'"),
    ]

    client = None

    try:
        print(f"[*] Connecting to {host}...")

        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect
        client.connect(host, username=username, password=password, timeout=10)
        print("[+] Connected!\n")

        # Execute commands
        for name, cmd in commands:
            print(f"\n{'='*80}")
            print(f"[*] {name}")
            print(f"{'='*80}")
            print(f"Command: {cmd}\n")

            stdin, stdout, stderr = client.exec_command(cmd, timeout=30)

            # Read output
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')

            if output:
                print(output)
            if error:
                print(f"[!] STDERR:\n{error}", file=sys.stderr)

            # Check exit code
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                print(f"[!] Exit code: {exit_code}")

        print(f"\n{'='*80}")
        print("[+] Done!")

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
    fetch_logs()
