#!/usr/bin/env python3
"""Set new ZAI API key, test it, restart OpenClaw."""
import os, sys, json
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

print(f"=== 1. Update ZAI_API_KEY in .env ===")
print(f"New key: {NEW_KEY[:15]}...{NEW_KEY[-5:]}")

# Read current .env
sftp = ssh.open_sftp()
with sftp.open('/opt/openclaw/.env', 'r') as f:
    env_content = f.read().decode('utf-8')

# Replace ZAI key
new_lines = []
for line in env_content.splitlines():
    if line.startswith("ZAI_API_KEY="):
        new_lines.append(f"ZAI_API_KEY={NEW_KEY}")
    else:
        new_lines.append(line)

with sftp.open('/opt/openclaw/.env', 'w') as f:
    f.write('\n'.join(new_lines) + '\n')
sftp.close()
print("Updated .env")

print(f"\n=== 2. Test new key with BigModel API ===")
cmd = f'''python3 << 'PYEOF'
import json, urllib.request

key = "{NEW_KEY}"
payload = json.dumps({{
    "model": "glm-4-flash",
    "messages": [{{"role": "user", "content": "say hello in one word"}}],
    "max_tokens": 20
}}).encode()

try:
    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=payload,
        headers={{
            "Content-Type": "application/json",
            "Authorization": f"Bearer {{key}}"
        }}
    )
    resp = urllib.request.urlopen(req, timeout=20)
    result = json.loads(resp.read())
    msg = result.get("choices", [{{}}])[0].get("message", {{}}).get("content", "no content")
    print(f"API OK! Response: {{msg[:100]}}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP ERROR {{e.code}}: {{body[:300]}}")
except Exception as e:
    print(f"ERROR: {{e}}")
PYEOF
'''
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=25)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
if err.strip():
    print("STDERR:", err.encode("ascii", errors="replace").decode("ascii")[:300])

print("=== 3. Stop running OpenClaw, restart service ===")
stdin, stdout, stderr = ssh.exec_command('pkill -f "run-node.mjs gateway" 2>/dev/null; sleep 2; systemctl restart openclaw && sleep 10 && systemctl status openclaw --no-pager | head -10')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:800])

print("\n=== 4. Check logs ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 12 --no-pager')
out = stdout.read().decode("utf-8", errors="replace")
for line in out.splitlines()[-8:]:
    print(line.encode("ascii", errors="replace").decode("ascii")[:150])

ssh.close()
