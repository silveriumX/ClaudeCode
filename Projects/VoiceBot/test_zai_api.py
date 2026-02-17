#!/usr/bin/env python3
"""Test ZAI API directly from VPS."""
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
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, "root", PASS, timeout=15)

cmd = '''python3 << 'PYEOF'
import json, urllib.request, os

# Read ZAI key from .env
key = ""
with open("/opt/openclaw/.env") as f:
    for line in f:
        if line.startswith("ZAI_API_KEY="):
            key = line.strip().split("=", 1)[1]

print(f"ZAI_API_KEY: {key[:15]}...{key[-5:]}")
print()

# Test 1: BigModel API (GLM official)
print("=== Test 1: BigModel API (open.bigmodel.cn) ===")
try:
    payload = json.dumps({
        "model": "glm-4",
        "messages": [{"role": "user", "content": "say hello"}],
        "max_tokens": 50
    }).encode()
    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }
    )
    resp = urllib.request.urlopen(req, timeout=20)
    result = json.loads(resp.read())
    print(f"  Status: OK")
    msg = result.get("choices", [{}])[0].get("message", {}).get("content", "no content")
    print(f"  Response: {msg[:100]}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"  HTTP ERROR {e.code}: {body[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

print()

# Test 2: DNS resolution
print("=== Test 2: DNS check ===")
import socket
for host in ["open.bigmodel.cn", "api.telegram.org"]:
    try:
        ip = socket.gethostbyname(host)
        print(f"  {host} -> {ip}")
    except Exception as e:
        print(f"  {host} -> DNS FAILED: {e}")

print()

# Test 3: Check OpenClaw .env for all relevant vars
print("=== Test 3: .env contents (keys only) ===")
with open("/opt/openclaw/.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k = line.split("=")[0]
            v = line.split("=", 1)[1]
            print(f"  {k}={v[:20]}...")
PYEOF
'''

stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
if err.strip():
    print("STDERR:", err.encode("ascii", errors="replace").decode("ascii")[:500])

ssh.close()
