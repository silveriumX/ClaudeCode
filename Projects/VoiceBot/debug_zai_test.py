#!/usr/bin/env python3
"""Test Z.AI API more carefully + enable debug logging + send test message."""
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
import json, subprocess, os, urllib.request, time

# 1. Test Z.AI API with FULL response
print("=== 1. Z.AI API FULL RESPONSE ===")
with open("/opt/openclaw/.env") as f:
    for line in f:
        if line.startswith("ZAI_API_KEY="):
            api_key = line.strip().split("=", 1)[1]

url = "https://api.z.ai/api/paas/v4/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + api_key
}
payload = json.dumps({
    "model": "glm-4.7-flash",
    "messages": [{"role": "user", "content": "Hello! Say hi back."}],
    "max_tokens": 100
}).encode("utf-8")

try:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)
    raw = resp.read().decode("utf-8")
    print("  RAW RESPONSE:")
    print("  " + raw[:500])
    data = json.loads(raw)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "<EMPTY>")
    print("  CONTENT: " + repr(content))
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:500]
    print("  HTTP " + str(e.code) + ": " + body)
except Exception as e:
    print("  ERROR: " + str(e))

# 2. Check how OpenClaw calls Z.AI - what model ID format does it use?
print()
print("=== 2. OPENCLAW Z.AI PROVIDER CONFIG ===")
# Check if there's a providers config
cfg = json.load(open("/root/.openclaw/openclaw.json"))
providers = cfg.get("providers", {})
print("  providers: " + json.dumps(providers, indent=2)[:500])

# Check model routing
models = cfg.get("agents", {}).get("defaults", {}).get("models", {})
print("  models: " + json.dumps(models, indent=2)[:300])

model_primary = cfg.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "?")
print("  primary model: " + model_primary)

# 3. Enable debug logging
print()
print("=== 3. ENABLE DEBUG + RESTART ===")
env_path = "/opt/openclaw/.env"
with open(env_path) as f:
    env_content = f.read()

if "LOG_LEVEL=" not in env_content and "OPENCLAW_LOG_LEVEL=" not in env_content:
    with open(env_path, "a") as f:
        f.write("\\nLOG_LEVEL=debug\\nOPENCLAW_LOG_LEVEL=debug\\nDEBUG=openclaw*\\n")
    print("  Added debug env vars")
else:
    print("  Debug already set")

subprocess.run(["systemctl", "restart", "openclaw"])
time.sleep(12)
print("  OpenClaw restarted")

# 4. Now send a test message via Telegram sendMessage to trigger the bot
print()
print("=== 4. CHECK NEW LOGS ===")
r = subprocess.run(["journalctl", "-u", "openclaw", "-n", "15", "--no-pager"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines()[-10:]:
    print("  " + line[:200])

# 5. Read last few lines of log file for any debug output
print()
print("=== 5. LOG FILE (last 5 lines) ===")
r = subprocess.run(["tail", "-5", "/tmp/openclaw/openclaw-2026-02-09.log"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines():
    print("  " + line[:200])
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/debug_test.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/debug_test.py', timeout=60)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
ssh.close()
