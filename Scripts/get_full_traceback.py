#!/usr/bin/env python3
"""Get full traceback for unsupported format string error"""

import os
import sys
import io
from pathlib import Path

from dotenv import load_dotenv
import paramiko

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def get_full_traceback():
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    commands = [
        ("Full traceback with line numbers for format error",
         "journalctl -u finance_bot --no-pager --since today -n 2000 | grep -B 30 'unsupported format string' | head -100"),
        ("Check sheets.py get_requests_by_status method",
         "cd /root/finance_bot && grep -n 'get_requests_by_status' sheets.py"),
        ("Check where format error happens in sheets.py",
         "cd /root/finance_bot && grep -n -A 5 -B 5 'f\"' sheets.py | grep -A 5 -B 5 'дата\\|сумма\\|статус'"),
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
    get_full_traceback()
