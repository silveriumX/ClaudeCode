#!/usr/bin/env python3
"""Check if botToken is still correct in config."""
import os, sys, json
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

print("=== 1. Check current telegram config ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json')
out = stdout.read().decode("utf-8", errors="replace")
cfg = json.loads(out)
tg = cfg['channels']['telegram']
print(f"enabled: {tg['enabled']}")
print(f"dmPolicy: {tg['dmPolicy']}")
print(f"allowFrom: {tg.get('allowFrom', 'NOT SET')}")
print(f"botToken: {tg.get('botToken', 'NOT SET')[:20]}...{tg.get('botToken', '')[-10:]}")

print("\n=== 2. Test botToken with getMe ===")
token = tg.get('botToken', '')
cmd = f'''python3 -c "
import json, urllib.request
try:
    url = 'https://api.telegram.org/bot{token}/getMe'
    resp = urllib.request.urlopen(url, timeout=10)
    data = json.loads(resp.read())
    if data['ok']:
        bot = data['result']
        print(f'OK: @{{bot[\\\"username\\\"]}} ({{bot[\\\"first_name\\\"]}})')
    else:
        print('ERROR:', data)
except Exception as e:
    print('EXCEPTION:', e)
" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode("utf-8", errors="replace")
print(out[:500])

print("\n=== 3. Check recent OpenClaw telegram logs for errors ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw --since "2 minutes ago" | grep -iE "telegram|error|failed" | tail -15')
out = stdout.read().decode("utf-8", errors="replace")
if out.strip():
    for line in out.strip().splitlines()[-10:]:
        print(line.encode("ascii", errors="replace").decode("ascii")[:200])
else:
    print("No telegram errors in journalctl")

print("\n=== 4. Check direct log for telegram initialization ===")
stdin, stdout, stderr = ssh.exec_command('tail -200 /tmp/openclaw/openclaw-2026-02-09.log | grep telegram | tail -10')
out = stdout.read().decode("utf-8", errors="replace")
if out.strip():
    for line in out.strip().splitlines()[-8:]:
        print(line.encode("ascii", errors="replace").decode("ascii")[:250])

ssh.close()
