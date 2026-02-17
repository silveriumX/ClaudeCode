#!/usr/bin/env python3
"""Get FRESH telegram logs from last 30 seconds."""
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

print("=== Current OpenClaw process info ===")
stdin, stdout, stderr = ssh.exec_command('systemctl status openclaw --no-pager | head -15')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:1000])

print("\n=== Last 30 lines of journalctl ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 30 --no-pager')
out = stdout.read().decode("utf-8", errors="replace")
lines = [l.encode("ascii", errors="replace").decode("ascii")[:150] for l in out.splitlines()[-20:]]
for line in lines:
    print(line)

print("\n=== Direct log file (last 50 lines, raw JSON) ===")
stdin, stdout, stderr = ssh.exec_command('tail -50 /tmp/openclaw/openclaw-2026-02-09.log')
out = stdout.read().decode("utf-8", errors="replace")
# find telegram lines
tg_lines = [l for l in out.splitlines() if 'telegram' in l.lower()]
if tg_lines:
    print(f"Found {len(tg_lines)} telegram lines in last 50:")
    for line in tg_lines[-8:]:
        print(line.encode("ascii", errors="replace").decode("ascii")[:300])
else:
    print("NO telegram lines in last 50 log lines")

ssh.close()
