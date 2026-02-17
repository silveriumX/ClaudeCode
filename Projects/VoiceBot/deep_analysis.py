#!/usr/bin/env python3
"""Deep log analysis + test Z.AI API."""
import os, sys, time, json
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import paramiko

HOST = "195.177.94.189"
PASS = os.environ.get("VOICEBOT_SSH_PASS", "")
ZAI_KEY = "525b2fbc0b954a6bb9aac9394789e349.vCDOfBTV1q1rmzv8"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, "root", PASS, timeout=20)

# 1. Test Z.AI API from VPS
print("=== 1. TEST Z.AI API ===")
test_cmd = f'''python3 << 'PYEOF'
import json, urllib.request
try:
    req = urllib.request.Request(
        "https://api.z.ai/api/paas/v4/chat/completions",
        data=json.dumps({{
            "model": "glm-4.7-flash",
            "messages": [{{"role": "user", "content": "hi"}}],
            "max_tokens": 100
        }}).encode(),
        headers={{
            "Content-Type": "application/json",
            "Authorization": "Bearer {ZAI_KEY}"
        }},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    print("SUCCESS:", data.get("choices", [{{}}])[0].get("message", {{}}).get("content", "empty")[:100])
except Exception as e:
    print("ERROR:", str(e)[:200])
PYEOF
'''
stdin, stdout, stderr = ssh.exec_command(test_cmd, timeout=30)
print(stdout.read().decode("utf-8", errors="replace").strip()[:300])

# 2. Full log file for errors
print("\n=== 2. LOG FILE ERRORS ===")
stdin, stdout, stderr = ssh.exec_command("grep -E 'error|Error|fail|reject' /tmp/openclaw/openclaw-2026-02-10.log 2>/dev/null | tail -10", timeout=10)
for line in stdout.read().decode("utf-8", errors="replace").strip().splitlines():
    try:
        j = json.loads(line)
        msg = str(j.get("1", ""))[:150]
        print(f"  {msg}")
    except:
        print(f"  {line[:150]}")

# 3. Check model config
print("\n=== 3. MODEL CONFIG ===")
stdin, stdout, stderr = ssh.exec_command("python3 -c \"import json; c=json.load(open('/root/.openclaw/openclaw.json')); print(json.dumps(c.get('agents',{}).get('defaults',{}).get('model',{}), indent=2))\"", timeout=10)
print(stdout.read().decode().strip())

# 4. Check .env files
print("\n=== 4. ENV FILES ===")
for path in ["/usr/lib/node_modules/openclaw/.env", "/root/.openclaw/.env"]:
    stdin, stdout, stderr = ssh.exec_command(f"cat {path} 2>/dev/null | grep -E 'ZAI|TELEGRAM' || echo 'NOT FOUND'", timeout=5)
    out = stdout.read().decode().strip()
    print(f"  {path}:")
    for line in out.splitlines():
        if "ZAI_API_KEY" in line:
            print(f"    ZAI_API_KEY: {line.split('=')[1][:15] if '=' in line else 'MISSING'}...")
        elif "TELEGRAM" in line:
            print(f"    TELEGRAM_BOT_TOKEN: {line.split('=')[1][:15] if '=' in line else 'MISSING'}...")
        else:
            print(f"    {line}")

# 5. Last conversation attempt in log
print("\n=== 5. LAST CONVERSATION ATTEMPT ===")
stdin, stdout, stderr = ssh.exec_command("tail -30 /tmp/openclaw/openclaw-2026-02-10.log 2>/dev/null", timeout=10)
for line in stdout.read().decode("utf-8", errors="replace").strip().splitlines()[-15:]:
    try:
        j = json.loads(line)
        subsys = str(j.get("0", ""))
        msg1 = str(j.get("1", ""))[:120]
        msg2 = str(j.get("2", ""))[:80]
        print(f"  {subsys[:40]} | {msg1} {msg2}"[:180])
    except:
        print(f"  {line[:180]}")

ssh.close()
