#!/usr/bin/env python3
"""Deep dive into OpenClaw config and actual Telegram activity."""
import os, sys, time, json
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
import json, subprocess, os, urllib.request

# 1. Full Telegram config
print("=== 1. FULL TELEGRAM CONFIG ===")
cfg = json.load(open("/root/.openclaw/openclaw.json"))
tg = cfg.get("channels", {}).get("telegram", {})
print(json.dumps(tg, indent=2, default=str))

# 2. Full agents config
print()
print("=== 2. AGENTS CONFIG ===")
agents = cfg.get("agents", {})
print(json.dumps(agents, indent=2, default=str)[:500])

# 3. Plugins
print()
print("=== 3. PLUGINS ===")
plugins = cfg.get("plugins", {})
print(json.dumps(plugins, indent=2, default=str)[:500])

# 4. Check .env
print()
print("=== 4. .ENV KEYS ===")
with open("/opt/openclaw/.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            key = line.split("=")[0]
            val = line.split("=", 1)[1] if "=" in line else ""
            if "KEY" in key or "TOKEN" in key or "SECRET" in key:
                print(f"  {key} = {val[:15]}...{val[-5:]}" if len(val) > 20 else f"  {key} = {val}")
            else:
                print(f"  {key} = {val}")

# 5. OpenClaw version
print()
print("=== 5. OPENCLAW VERSION ===")
r = subprocess.run(["node", "-e", "try{const p=require('/opt/openclaw/package.json');console.log(p.name,p.version)}catch(e){console.log(e.message)}"],
                    capture_output=True, text=True, cwd="/opt/openclaw")
print(f"  {r.stdout.strip()}")

# 6. Check if Telegram channel needs login/onboarding
print()
print("=== 6. OPENCLAW CLI CHANNELS STATUS ===")
r = subprocess.run(["node", "scripts/run-node.mjs", "channels", "status"],
                    capture_output=True, text=True, cwd="/opt/openclaw", timeout=15)
print(f"  stdout: {r.stdout.strip()[:500]}")
print(f"  stderr: {r.stderr.strip()[:500]}")

# 7. strace check - is OpenClaw making network calls?
print()
print("=== 7. ACTIVE CONNECTIONS ===")
r = subprocess.run(["ss", "-tnp", "dst", "149.154.0.0/16"], capture_output=True, text=True)
print(r.stdout.strip()[:500])

# 8. Token test - can we getMe?
token = tg.get("botToken", "")
print()
print("=== 8. TOKEN GETME ===")
try:
    resp = urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
    data = json.loads(resp.read())
    bot_info = data["result"]
    print(f"  Bot: @{bot_info['username']} (id: {bot_info['id']})")
    print(f"  can_join_groups: {bot_info.get('can_join_groups')}")
    print(f"  can_read_all: {bot_info.get('can_read_all_group_messages')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 9. Check if bot has pending updates RIGHT NOW
print()
print("=== 9. PENDING UPDATES (non-consuming peek) ===")
try:
    resp = urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=5)
    data = json.loads(resp.read())
    print(f"  pending_update_count: {data['result']['pending_update_count']}")
    print(f"  webhook url: '{data['result']['url']}'")
except Exception as e:
    print(f"  ERROR: {e}")
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/deep_config.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/deep_config.py', timeout=25)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
ssh.close()
