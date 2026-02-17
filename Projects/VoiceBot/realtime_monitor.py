#!/usr/bin/env python3
"""
Check credential files + set up real-time monitoring.
Asks user to send message while monitoring.
"""
import os, sys, json, time
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import paramiko
HOST = "195.177.94.189"
PASS = os.environ.get("VOICEBOT_SSH_PASS", "")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, "root", PASS, timeout=15)

SCRIPT = '''#!/usr/bin/env python3
import json, subprocess, os, time, urllib.request

cfg = json.load(open("/root/.openclaw/openclaw.json"))
token = cfg["channels"]["telegram"]["botToken"]

# 1. Check credential files
print("=== 1. CREDENTIAL FILES ===")
files = {
    "telegram-pairing.json": "/root/.openclaw/credentials/telegram-pairing.json",
    "telegram-allowFrom.json": "/root/.openclaw/credentials/telegram-allowFrom.json",
    "paired.json": "/root/.openclaw/devices/paired.json",
    "device-auth.json": "/root/.openclaw/identity/device-auth.json",
    "device.json": "/root/.openclaw/identity/device.json",
}
for name, path in files.items():
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        print(f"  {name}: {content[:300]}")
    else:
        print(f"  {name}: NOT FOUND")
    print()

# 2. Check workspace identity
print("=== 2. IDENTITY ===")
for fname in ["IDENTITY.md", "USER.md", "BOOTSTRAP.md"]:
    path = f"/root/.openclaw/workspace/{fname}"
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        print(f"  --- {fname} ---")
        print(f"  {content[:300]}")
        print()

# 3. REAL-TIME TEST: record offset, check for updates in a loop
print("=== 3. REAL-TIME MONITORING (30 seconds) ===")
logfile = "/tmp/openclaw/openclaw-2026-02-09.log"
initial_size = os.path.getsize(logfile) if os.path.exists(logfile) else 0

print(f"  Log offset: {initial_size}")
print(f"  Monitoring for 30 seconds...")
print(f"  >>> SEND A MESSAGE TO @cosmicprincesskaguyabot NOW <<<")

start_time = time.time()
last_size = initial_size
while time.time() - start_time < 30:
    time.sleep(3)
    current_size = os.path.getsize(logfile) if os.path.exists(logfile) else 0
    if current_size > last_size:
        with open(logfile, "rb") as f:
            f.seek(last_size)
            new_data = f.read().decode("utf-8", errors="replace")
        for line in new_data.strip().splitlines():
            try:
                j = json.loads(line)
                subsys = str(j.get("0", ""))
                msg1 = str(j.get("1", ""))[:100]
                msg2 = str(j.get("2", ""))[:100]
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] {subsys} | {msg1} | {msg2}")
            except:
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] {line[:200]}")
        last_size = current_size

# Also check journalctl for last 30 seconds
print()
print("=== 4. JOURNALCTL LAST 30 SEC ===")
r = subprocess.run(["journalctl", "-u", "openclaw", "--since", "30 seconds ago", "--no-pager"],
                    capture_output=True, text=True)
lines = r.stdout.strip().splitlines()
print(f"  Total lines: {len(lines)}")
for line in lines:
    print(f"  {line[:180]}")
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/realtime_monitor.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

print(">>> SEND A MESSAGE TO @cosmicprincesskaguyabot IN TELEGRAM NOW! <<<")
print("Monitoring for 30 seconds...")
print()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/realtime_monitor.py', timeout=60)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
ssh.close()
