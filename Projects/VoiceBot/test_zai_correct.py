#!/usr/bin/env python3
"""Test ZAI API with CORRECT endpoint api.z.ai."""
import os, sys
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
NEW_KEY = os.environ.get("NEW_ZAI_KEY", "")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, "root", PASS, timeout=15)

cmd = f'''python3 << 'PYEOF'
import json, urllib.request

key = "{NEW_KEY}"
print(f"Key: {{key[:15]}}...")

# Test with CORRECT endpoint: api.z.ai
payload = json.dumps({{
    "model": "glm-4.7",
    "messages": [{{"role": "user", "content": "say hello in one word"}}],
    "max_tokens": 20
}}).encode()

print("\\nTest: https://api.z.ai/api/paas/v4/chat/completions")
try:
    req = urllib.request.Request(
        "https://api.z.ai/api/paas/v4/chat/completions",
        data=payload,
        headers={{
            "Content-Type": "application/json",
            "Authorization": f"Bearer {{key}}"
        }}
    )
    resp = urllib.request.urlopen(req, timeout=20)
    result = json.loads(resp.read())
    msg = result.get("choices", [{{}}])[0].get("message", {{}}).get("content", "no content")
    print(f"SUCCESS! Response: {{msg}}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP ERROR {{e.code}}: {{body[:500]}}")
except Exception as e:
    print(f"ERROR: {{e}}")
PYEOF
'''
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
if err.strip():
    print("STDERR:", err.encode("ascii", errors="replace").decode("ascii")[:300])

ssh.close()
