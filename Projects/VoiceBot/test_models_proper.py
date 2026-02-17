#!/usr/bin/env python3
"""Test Z.AI models with proper max_tokens + find non-reasoning model."""
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
import json, urllib.request

with open("/opt/openclaw/.env") as f:
    for line in f:
        if line.startswith("ZAI_API_KEY="):
            api_key = line.strip().split("=", 1)[1]

url = "https://api.z.ai/api/paas/v4/chat/completions"

def test_model(model, max_tok):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key
    }
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": max_tok
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "")
        finish = choice.get("finish_reason", "?")
        usage = data.get("usage", {})
        print(f"  model={model} max_tok={max_tok}")
        print(f"    finish_reason: {finish}")
        print(f"    content: {repr(content[:100])}")
        print(f"    has_reasoning: {bool(reasoning)} (len={len(reasoning)})")
        print(f"    usage: {usage}")
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(f"  model={model} max_tok={max_tok}: HTTP {e.code} - {body}")
        return False
    except Exception as e:
        print(f"  model={model} max_tok={max_tok}: ERROR - {e}")
        return False

# Test 1: glm-4.7-flash with MORE tokens
print("=== TEST 1: glm-4.7-flash with 2048 tokens ===")
test_model("glm-4.7-flash", 2048)

# Test 2: glm-4-flash (non-reasoning?)
print()
print("=== TEST 2: glm-4-flash ===")
test_model("glm-4-flash", 200)

# Test 3: glm-4-air
print()
print("=== TEST 3: glm-4-air ===")
test_model("glm-4-air", 200)

# Test 4: glm-4-flashx
print()
print("=== TEST 4: glm-4-flashx ===")
test_model("glm-4-flashx", 200)

# Test 5: glm-4-long
print()
print("=== TEST 5: glm-4-long ===")
test_model("glm-4-long", 200)

# Test 6: glm-4-plus
print()
print("=== TEST 6: glm-4-plus ===")
test_model("glm-4-plus", 200)

# Test 7: glm-4-0520
print()
print("=== TEST 7: glm-4-0520 ===")
test_model("glm-4-0520", 200)

# Test 8: glm-z1-flash
print()
print("=== TEST 8: glm-z1-flash ===")
test_model("glm-z1-flash", 2048)

# Test 9: glm-z1-air
print()
print("=== TEST 9: glm-z1-airx ===")
test_model("glm-z1-airx", 2048)
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/test_models.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_models.py', timeout=120)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
ssh.close()
