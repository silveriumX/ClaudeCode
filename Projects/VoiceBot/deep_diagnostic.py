#!/usr/bin/env python3
"""Send a test message via Telegram API and check if OpenClaw processes it."""
import os, sys, json, time
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

print("=== 1. Check OpenClaw process is alive ===")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep openclaw | grep -v grep')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:500])

print("\n=== 2. Check memory/CPU ===")
stdin, stdout, stderr = ssh.exec_command('systemctl status openclaw --no-pager | grep -E "Memory|CPU|Active"')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:500])

print("\n=== 3. Check network connections to Telegram ===")
stdin, stdout, stderr = ssh.exec_command('ss -tnp | grep 149.154')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:500] if out.strip() else "NO connections to Telegram!")

print("\n=== 4. Send message to bot via API and check ===")
cmd = '''python3 -c "
import json, urllib.request, time

cfg = json.load(open('/root/.openclaw/openclaw.json'))
token = cfg['channels']['telegram']['botToken']

# First check pending updates
url = f'https://api.telegram.org/bot{token}/getUpdates?timeout=5'
resp = urllib.request.urlopen(url, timeout=15)
data = json.loads(resp.read())
print(f'getUpdates (5s timeout): {len(data.get(\\\"result\\\", []))} updates')
if data.get('result'):
    for upd in data['result'][-3:]:
        msg = upd.get('message', {})
        print(f'  {msg.get(\\\"text\\\", \\\"<no text>\\\")} from @{msg.get(\\\"from\\\", {}).get(\\\"username\\\", \\\"unknown\\\")}')
else:
    print('  Empty - OpenClaw is consuming updates (long polling active)')
" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
out = stdout.read().decode("utf-8", errors="replace")
print(out[:500])

print("\n=== 5. Check journalctl for ANYTHING since restart ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw --since "5 minutes ago" --no-pager | tail -30')
out = stdout.read().decode("utf-8", errors="replace")
lines = out.splitlines()[-15:]
for line in lines:
    print(line.encode("ascii", errors="replace").decode("ascii")[:150])

ssh.close()
