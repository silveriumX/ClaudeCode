#!/usr/bin/env python3
"""Get detailed Finance Bot error logs"""

import os
import sys
import io
from pathlib import Path

from dotenv import load_dotenv
import paramiko

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def get_detailed_errors():
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    commands = [
        ("Latest format error with context",
         "journalctl -u finance_bot --no-pager --since today | grep -B 10 -A 30 'unsupported format string' | tail -150"),
        ("All today errors",
         "journalctl -u finance_bot --no-pager --since today | grep -i 'error\\|exception\\|traceback' | tail -100"),
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
    get_detailed_errors()
