#!/usr/bin/env python3
"""FINAL diagnostic - check EVERYTHING in one shot."""
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

cmd = '''python3 << 'PYEOF'
import json, urllib.request, subprocess, os

cfg = json.load(open("/root/.openclaw/openclaw.json"))
token = cfg["channels"]["telegram"]["botToken"]

# 1. Service status
print("=== 1. Service ===")
r = subprocess.run(["systemctl", "is-active", "openclaw"], capture_output=True, text=True)
print(f"  Status: {r.stdout.strip()}")

# 2. getWebhookInfo
print("\n=== 2. Webhook ===")
try:
    resp = urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=10)
    data = json.loads(resp.read())
    wh = data["result"]
    print(f"  URL: '{wh['url']}'")
    print(f"  Pending: {wh['pending_update_count']}")
except Exception as e:
    print(f"  Error: {e}")

# 3. Try getUpdates with short timeout
print("\n=== 3. getUpdates (2s timeout) ===")
try:
    resp = urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates?timeout=2&limit=3", timeout=10)
    data = json.loads(resp.read())
    print(f"  Count: {len(data.get('result', []))}")
    for u in data.get("result", []):
        msg = u.get("message", {})
        print(f"    {u['update_id']}: {msg.get('text', '?')} from @{msg.get('from', {}).get('username', '?')}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:200]
    print(f"  HTTP {e.code}: {body}")
except Exception as e:
    print(f"  Error: {e}")

# 4. Recent journalctl
print("\n=== 4. ALL journalctl (last 2 min) ===")
r = subprocess.run(["journalctl", "-u", "openclaw", "--since", "2 minutes ago", "--no-pager"],
                    capture_output=True, text=True)
lines = r.stdout.strip().splitlines()
print(f"  Total lines: {len(lines)}")
for line in lines[-15:]:
    print(f"  {line[:180]}")

# 5. Log file - last lines
print("\n=== 5. Log file (new entries) ===")
r = subprocess.run(["tail", "-5", "/tmp/openclaw/openclaw-2026-02-09.log"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines():
    try:
        j = json.loads(line)
        s = j.get("0", "")
        m = j.get("1", "") or j.get("2", "")
        print(f"  {str(s)[:50]} | {str(m)[:120]}")
    except:
        print(f"  {line[:180]}")

# 6. ZAI env key
print("\n=== 6. .env check ===")
with open("/opt/openclaw/.env") as f:
    for line in f:
        if line.startswith("ZAI_API_KEY="):
            k = line.strip().split("=",1)[1]
            print(f"  ZAI_API_KEY: {k[:15]}...{k[-5:]}")

# 7. Network connections
print("\n=== 7. Network to Telegram ===")
r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
tg = [l for l in r.stdout.splitlines() if "149.154" in l]
for l in tg[:5]:
    print(f"  {l.strip()[:120]}")
print(f"  Total Telegram connections: {len(tg)}")
PYEOF
'''
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
if err.strip():
    print("STDERR:", err.encode("ascii", errors="replace").decode("ascii")[:300])

ssh.close()
