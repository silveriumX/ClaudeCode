#!/usr/bin/env python3
"""Test ZAI API with all model variants."""
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
models = ["glm-4.7", "glm-4.7-flash", "glm-4.7-flashx", "glm-4.6", "glm-4.5-flash"]

for model in models:
    payload = json.dumps({{
        "model": model,
        "messages": [{{"role": "user", "content": "say hi"}}],
        "max_tokens": 10,
        "stream": False
    }}).encode()

    try:
        req = urllib.request.Request(
            "https://api.z.ai/api/paas/v4/chat/completions",
            data=payload,
            headers={{
                "Content-Type": "application/json",
                "Authorization": f"Bearer {{key}}"
            }}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        msg = result.get("choices", [{{}}])[0].get("message", {{}}).get("content", "?")
        print(f"  {{model}}: OK -> {{msg[:50]}}")
        break
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(f"  {{model}}: ERROR {{e.code}} -> {{body}}")
    except Exception as e:
        print(f"  {{model}}: FAIL -> {{e}}")
PYEOF
'''
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
if err.strip():
    print("STDERR:", err.encode("ascii", errors="replace").decode("ascii")[:300])

ssh.close()
