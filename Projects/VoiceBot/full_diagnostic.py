#!/usr/bin/env python3
"""FULL diagnostic: config, getUpdates, .env, detailed logs."""
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

print("=== 1. FULL CONFIG ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json')
out = stdout.read().decode("utf-8", errors="replace")
cfg = json.loads(out)
print(json.dumps(cfg, indent=2, ensure_ascii=False).encode("ascii", errors="replace").decode("ascii")[:3000])

print("\n=== 2. .ENV file ===")
stdin, stdout, stderr = ssh.exec_command('cat /opt/openclaw/.env')
out = stdout.read().decode("utf-8", errors="replace")
for line in out.strip().splitlines():
    key = line.split("=")[0] if "=" in line else line
    val = line.split("=", 1)[1][:20] if "=" in line else ""
    print(f"  {key}={val}...")

print("\n=== 3. getUpdates ===")
token = cfg.get('channels', {}).get('telegram', {}).get('botToken', '')
if not token:
    # try .env
    print("  botToken NOT in config! Checking .env...")
    stdin, stdout, stderr = ssh.exec_command('grep TELEGRAM /opt/openclaw/.env')
    out = stdout.read().decode("utf-8", errors="replace")
    print(f"  .env: {out.strip()}")
else:
    cmd = f'''python3 -c "
import json, urllib.request
url = 'https://api.telegram.org/bot{token}/getUpdates'
resp = urllib.request.urlopen(url, timeout=10)
data = json.loads(resp.read())
print('Updates:', len(data.get('result', [])))
for upd in data.get('result', [])[-3:]:
    msg = upd.get('message', {{}})
    print(f'  {{upd[\\\"update_id\\\"]}}: {{msg.get(\\\"text\\\", \\\"<none>\\\")}}')
" 2>&1'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    print(out[:500])

print("\n=== 4. Detailed log file (last 30 lines) ===")
stdin, stdout, stderr = ssh.exec_command('tail -30 /tmp/openclaw/openclaw-2026-02-09.log')
out = stdout.read().decode("utf-8", errors="replace")
for line in out.splitlines()[-15:]:
    safe = line.encode("ascii", errors="replace").decode("ascii")[:200]
    print(safe)

print("\n=== 5. Check if OpenClaw is doing polling (strace) ===")
stdin, stdout, stderr = ssh.exec_command('ss -tnp | grep 641844 | head -10')
out = stdout.read().decode("utf-8", errors="replace")
if out.strip():
    print(out.encode("ascii", errors="replace").decode("ascii")[:500])
else:
    # get current PID
    stdin, stdout, stderr = ssh.exec_command('systemctl show openclaw --property=MainPID')
    pid_out = stdout.read().decode("utf-8", errors="replace").strip()
    print(f"  MainPID: {pid_out}")
    pid = pid_out.split("=")[1] if "=" in pid_out else ""
    if pid and pid != "0":
        stdin, stdout, stderr = ssh.exec_command(f'ss -tnp | grep {pid} | head -10')
        out = stdout.read().decode("utf-8", errors="replace")
        print(f"  Network connections for PID {pid}:")
        print(out.encode("ascii", errors="replace").decode("ascii")[:500] if out.strip() else "  NONE")

ssh.close()
