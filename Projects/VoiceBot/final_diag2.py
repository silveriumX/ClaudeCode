#!/usr/bin/env python3
"""FINAL diagnostic via separate script on VPS."""
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

# Upload diagnostic script to VPS
SCRIPT = '''#!/usr/bin/env python3
import json, urllib.request, subprocess, os

cfg = json.load(open("/root/.openclaw/openclaw.json"))
token = cfg["channels"]["telegram"]["botToken"]

print("=== 1. Service ===")
r = subprocess.run(["systemctl", "is-active", "openclaw"], capture_output=True, text=True)
print("  Status:", r.stdout.strip())

print("\\n=== 2. Webhook ===")
try:
    resp = urllib.request.urlopen("https://api.telegram.org/bot" + token + "/getWebhookInfo", timeout=10)
    data = json.loads(resp.read())
    wh = data["result"]
    print("  URL:", repr(wh["url"]))
    print("  Pending:", wh["pending_update_count"])
except Exception as e:
    print("  Error:", e)

print("\\n=== 3. getUpdates (2s) ===")
try:
    resp = urllib.request.urlopen("https://api.telegram.org/bot" + token + "/getUpdates?timeout=2&limit=3", timeout=10)
    data = json.loads(resp.read())
    print("  Count:", len(data.get("result", [])))
    for u in data.get("result", []):
        msg = u.get("message", {})
        print("   ", u["update_id"], msg.get("text", "?"), "@" + msg.get("from", {}).get("username", "?"))
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:200]
    print("  HTTP", e.code, body)
except Exception as e:
    print("  Error:", e)

print("\\n=== 4. Journalctl last 2 min ===")
r = subprocess.run(["journalctl", "-u", "openclaw", "--since", "2 minutes ago", "--no-pager"], capture_output=True, text=True)
lines = r.stdout.strip().splitlines()
print("  Total lines:", len(lines))
for line in lines[-12:]:
    print(" ", line[:180])

print("\\n=== 5. Network ===")
r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
tg = [l for l in r.stdout.splitlines() if "149.154" in l]
oc = [l for l in tg if "openclaw" in l]
print("  Telegram connections:", len(tg), "(openclaw:", len(oc), ")")
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/diag.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/diag.py', timeout=30)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
if err.strip():
    print("STDERR:", err.encode("ascii", errors="replace").decode("ascii")[:300])

ssh.close()
