#!/usr/bin/env python3
"""View get_requests_by_status method from VPS"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def view_method():
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    commands = [
        ("View get_requests_by_status method (line 499-533)",
         "cd /root/finance_bot && sed -n '499,533p' sheets.py"),
        ("View where requests are formatted for display",
         "cd /root/finance_bot/handlers && grep -n -A 10 'Ошибка при получении' menu.py"),
        ("Check how requests are displayed in menu.py",
         "cd /root/finance_bot/handlers && sed -n '1,50p' menu.py"),
    ]

    client = None

    try:
        print(f"[*] Connecting to {host}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, timeout=10)
        print("[+] Connected!\n")

        for name, cmd in commands:
            print(f"\n{'='*80}")
            print(f"[*] {name}")
            print(f"{'='*80}\n")

            stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
            output = stdout.read().decode('utf-8', errors='replace')

            if output:
                print(output)
            else:
                print("(No output)")

        print(f"\n{'='*80}")
        print("[+] Done!")

    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    view_method()
