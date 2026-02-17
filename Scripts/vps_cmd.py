import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# -*- coding: utf-8 -*-
"""Run commands on VPS via SSH (paramiko). Usage: python vps_cmd.py "command" """
import sys, io, paramiko, time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = os.getenv("VPS_VLESS_HOST")
USER = "root"
PASS = os.getenv("VPS_VLESS_PASSWORD")

def run(cmd, timeout=300):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=15)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    client.close()
    return out, err, code

if __name__ == "__main__":
    cmd = " && ".join(sys.argv[1:]) if len(sys.argv) > 1 else "echo ok"
    out, err, code = run(cmd)
    if out.strip():
        print(out.strip())
    if err.strip():
        print("[STDERR]", err.strip())
    print(f"[EXIT CODE: {code}]")
