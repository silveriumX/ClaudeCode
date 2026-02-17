#!/usr/bin/env python3
"""Monitor live logs while user sends message."""
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

print("=== LIVE MONITORING ===")
print("Send a message to @cosmicprincesskaguyabot RIGHT NOW")
print("Watching logs for 30 seconds...\n")

for i in range(15):  # 30 seconds (15 * 2s)
    stdin, stdout, stderr = ssh.exec_command('tail -30 /tmp/openclaw/openclaw-2026-02-09.log')
    out = stdout.read().decode("utf-8", errors="replace")
    lines = out.splitlines()

    # Look for NEW telegram activity
    new_tg = [l for l in lines if any(word in l.lower() for word in ['telegram', 'incoming', 'update', 'message'])]
    if new_tg:
        print(f"\n--- Iteration {i+1} (NEW ACTIVITY) ---")
        for line in new_tg[-5:]:
            safe = line.encode("ascii", errors="replace").decode("ascii")[:250]
            print(safe)
    else:
        print(f".", end="", flush=True)

    time.sleep(2)

print("\n\n=== Check getUpdates after monitoring ===")
cmd = '''python3 -c "
import json, urllib.request
cfg = json.load(open('/root/.openclaw/openclaw.json'))
token = cfg['channels']['telegram']['botToken']
url = f'https://api.telegram.org/bot{token}/getUpdates'
resp = urllib.request.urlopen(url, timeout=10)
data = json.loads(resp.read())
print('Updates:', len(data.get('result', [])))
" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode("utf-8", errors="replace")
print(out[:200])

ssh.close()
