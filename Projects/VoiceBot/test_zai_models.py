#!/usr/bin/env python3
"""Test different Z.AI models to find working one."""
import os, sys, json
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

models_to_test = [
    "glm-4-plus",  # Может требовать платную подписку
    "glm-4-0520",  # Старая версия
    "glm-4-air",   # Легкая версия
    "glm-4-flash", # Flash без .7
    "glm-4-airx",  # Air extended
    "glm-4",       # Base model
]

print("=== TESTING Z.AI MODELS ===\n")

for model in models_to_test:
    test_cmd = f'''python3 << 'PYEOF'
import json, urllib.request
model = "{model}"
try:
    req = urllib.request.Request(
        "https://api.z.ai/api/paas/v4/chat/completions",
        data=json.dumps({{
            "model": model,
            "messages": [{{"role": "user", "content": "Say hello in 3 words"}}],
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
    content = data.get("choices", [{{}}])[0].get("message", {{}}).get("content", "")
    reasoning = data.get("choices", [{{}}])[0].get("message", {{}}).get("reasoning_content", "")
    finish = data.get("choices", [{{}}])[0].get("finish_reason", "?")
    print(f"OK | content={{!r:.50}} | finish={{}} | has_reasoning={{}}".format(content, finish, bool(reasoning)))
except urllib.error.HTTPError as e:
    body = e.read().decode()[:100]
    print(f"HTTP {e.code} | {body}")
except Exception as e:
    print(f"ERROR | {str(e)[:100]}")
PYEOF
'''
    stdin, stdout, stderr = ssh.exec_command(test_cmd, timeout=25)
    result = stdout.read().decode("utf-8", errors="replace").strip()
    print(f"{model:20} : {result}")

ssh.close()

print("\n=== RECOMMENDATION ===")
print("Выбери модель с content != empty и has_reasoning=False")
