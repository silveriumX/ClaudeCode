#!/usr/bin/env python3
"""
On VPS: read token from openclaw.json, show length/prefix/suffix, then getMe.
No token in our stdin.

Environment variables (supports both VPS_* and VOICEBOT_* prefixes):
- VPS_HOST / VOICEBOT_HOST: VPS IP or hostname
- VPS_USER / VOICEBOT_USER: SSH username (default: root)
- VPS_PASSWORD / VOICEBOT_SSH_PASS: SSH password
"""
import json
import os
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

# Support both VPS_* and VOICEBOT_* variable names for backward compatibility
HOST = os.environ.get("VPS_HOST") or os.environ.get("VOICEBOT_HOST", "")
PORT = int(os.environ.get("VPS_PORT", "22"))
USER = os.environ.get("VPS_USER") or os.environ.get("VOICEBOT_USER", "root")
PASS = os.environ.get("VPS_PASSWORD") or os.environ.get("VOICEBOT_SSH_PASS", "")

if not HOST:
    print("Set VPS_HOST or VOICEBOT_HOST for VPS address.")
    sys.exit(1)
if not PASS:
    print("Set VPS_PASSWORD or VOICEBOT_SSH_PASS.")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, PASS, timeout=15)
# Read config on server
stdin, stdout, stderr = ssh.exec_command("cat /root/.openclaw/openclaw.json")
out = stdout.read().decode("utf-8", errors="replace")
cfg = json.loads(out)
token = (cfg.get("channels", {}).get("telegram", {}).get("botToken") or "").strip()
print("Token length:", len(token))
print("Token prefix:", repr(token[:22]))
print("Token suffix:", repr(token[-10:]) if len(token) > 10 else "")
# getMe on VPS using Python (same as other bots) - token from file
cmd = r"""python3 -c "
import json, urllib.request
j = json.load(open('/root/.openclaw/openclaw.json'))
t = (j.get('channels') or {}).get('telegram') or {}
tok = (t.get('botToken') or '').strip()
print('getMe:')
r = urllib.request.urlopen('https://api.telegram.org/bot' + tok + '/getMe', timeout=10)
print(r.read().decode())
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
me = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print("getMe (Python on VPS):", me[:450] if me else "empty")
if err:
    print("stderr:", err[:300])
ssh.close()
