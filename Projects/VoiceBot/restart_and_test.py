#!/usr/bin/env python3
"""Restart OpenClaw and monitor logs in real-time."""
import os, sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)
HOST = "195.177.94.189"
PASS = os.environ.get("VOICEBOT_SSH_PASS", "")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, "root", PASS, timeout=15)

print("=== 1. Restart OpenClaw ===")
stdin, stdout, stderr = ssh.exec_command('systemctl restart openclaw && sleep 5 && systemctl status openclaw | head -15')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:1000])

print("\n=== 2. Waiting for startup (check logs) ===")
stdin, stdout, stderr = ssh.exec_command('sleep 10 && journalctl -u openclaw -n 15 --no-pager')
out = stdout.read().decode("utf-8", errors="replace")
lines = [l.encode("ascii", errors="replace").decode("ascii")[:150] for l in out.splitlines()[-10:]]
for line in lines:
    print(line)

print("\n=== OpenClaw restarted. NOW SEND A MESSAGE TO THE BOT ===")
print("Send '/start' to @cosmicprincesskaguyabot RIGHT NOW")
print("Then wait 5 seconds and press Enter here...")

ssh.close()
