#!/usr/bin/env python3
"""Simple status check with retry."""
import os, sys, time
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

time.sleep(5)  # Wait before connecting

try:
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("Connecting...")
    ssh.connect("195.177.94.189", 22, "root", os.environ.get("VOICEBOT_SSH_PASS", ""), timeout=25)
    print("Connected!")

    stdin, stdout, stderr = ssh.exec_command("systemctl is-active openclaw", timeout=10)
    status = stdout.read().decode().strip()
    print(f"\nStatus: {status}")

    stdin, stdout, stderr = ssh.exec_command("journalctl -u openclaw -n 15 --no-pager 2>&1", timeout=15)
    logs = stdout.read().decode("utf-8", errors="replace").strip()
    print(f"\n=== LOGS ===")
    for line in logs.splitlines()[-12:]:
        print(line[:180])

    stdin, stdout, stderr = ssh.exec_command("python3 -c \"import json; c=json.load(open('/root/.openclaw/openclaw.json')); print('allowFrom:', c.get('channels',{}).get('telegram',{}).get('allowFrom'))\"", timeout=10)
    af = stdout.read().decode().strip()
    print(f"\n{af}")

    ssh.close()
except Exception as e:
    print(f"ERROR: {e}")
