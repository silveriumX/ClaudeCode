#!/usr/bin/env python3
"""Check FULL log file for ANY message processing / AI errors."""
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
import json, subprocess, os

# 1. Search ALL log entries for errors, messages, AI calls
print("=== 1. FULL LOG SEARCH for key terms ===")
logfile = "/tmp/openclaw/openclaw-2026-02-09.log"
if os.path.exists(logfile):
    with open(logfile) as f:
        lines = f.readlines()
    print(f"Total log lines: {len(lines)}")

    keywords = ["error", "Error", "fail", "message", "incoming", "chat", "reply", "zai", "glm", "429", "400", "401", "403", "500", "timeout", "reject", "dm", "user"]
    for kw in keywords:
        matches = [(i, l.strip()) for i, l in enumerate(lines) if kw.lower() in l.lower()]
        if matches:
            print(f"\\n  --- '{kw}' ({len(matches)} matches) ---")
            for idx, line in matches[-3:]:  # last 3 matches
                try:
                    j = json.loads(line)
                    parts = [str(v) for k, v in j.items()]
                    short = " | ".join(parts)[:200]
                    print(f"    L{idx}: {short}")
                except:
                    print(f"    L{idx}: {line[:200]}")

# 2. Check journalctl for errors
print("\\n\\n=== 2. JOURNALCTL ERRORS ===")
r = subprocess.run(["journalctl", "-u", "openclaw", "--since", "today", "--no-pager", "-p", "err"],
                    capture_output=True, text=True)
if r.stdout.strip():
    for line in r.stdout.strip().splitlines()[-10:]:
        print(f"  {line[:200]}")
else:
    print("  No error-level entries")

# 3. Check if there are multiple log files
print("\\n=== 3. LOG FILES ===")
r = subprocess.run(["ls", "-la", "/tmp/openclaw/"], capture_output=True, text=True)
print(r.stdout.strip()[:500])

# 4. Check OpenClaw data dir for conversation history
print("\\n=== 4. CONVERSATIONS ===")
conv_dir = os.path.expanduser("~/.openclaw/conversations")
if os.path.exists(conv_dir):
    convs = os.listdir(conv_dir)
    print(f"  Total conversations: {len(convs)}")
    for c in sorted(convs)[-5:]:
        path = os.path.join(conv_dir, c)
        size = os.path.getsize(path) if os.path.isfile(path) else "dir"
        print(f"    {c}: {size}")
else:
    print("  No conversations dir")

# 5. Try Z.AI API directly
print("\\n=== 5. Z.AI API TEST ===")
import urllib.request
with open("/opt/openclaw/.env") as f:
    for line in f:
        if line.startswith("ZAI_API_KEY="):
            api_key = line.strip().split("=", 1)[1]

url = "https://api.z.ai/api/paas/v4/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}
payload = json.dumps({
    "model": "glm-4.7-flash",
    "messages": [{"role": "user", "content": "Say hello in one word"}],
    "max_tokens": 50
}).encode("utf-8")

try:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    content = data["choices"][0]["message"]["content"]
    print(f"  SUCCESS: {content[:100]}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:200]
    print(f"  HTTP {e.code}: {body}")
except Exception as e:
    print(f"  ERROR: {e}")
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/full_log_check.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/full_log_check.py', timeout=30)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
ssh.close()
