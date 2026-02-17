#!/usr/bin/env python3
"""Watch DETAILED log file for ANY activity in next 20 seconds."""
import os, sys, time
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

# Get initial line count
stdin, stdout, stderr = ssh.exec_command('wc -l /tmp/openclaw/openclaw-2026-02-09.log')
initial = int(stdout.read().decode().strip().split()[0])
print(f"Log file has {initial} lines. Watching for NEW lines...")
print("SEND /start to @cosmicprincesskaguyabot NOW!\n")

for i in range(10):
    time.sleep(2)
    stdin, stdout, stderr = ssh.exec_command(f'tail -n +{initial+1} /tmp/openclaw/openclaw-2026-02-09.log')
    out = stdout.read().decode("utf-8", errors="replace")
    new_lines = out.strip().splitlines()
    if new_lines:
        print(f"\n*** {len(new_lines)} NEW LINES at iteration {i+1} ***")
        for line in new_lines:
            safe = line.encode("ascii", errors="replace").decode("ascii")[:250]
            print(safe)
        initial += len(new_lines)
    else:
        print(f".", end="", flush=True)

print("\n\nDone watching.")
ssh.close()
