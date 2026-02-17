#!/usr/bin/env python3
"""
Step 1: Stop and remove OpenClaw.

Environment variables (supports both VPS_* and VOICEBOT_* prefixes):
- VPS_HOST / VOICEBOT_HOST: VPS IP or hostname
- VPS_USER / VOICEBOT_USER: SSH username (default: root)
- VPS_PASSWORD / VOICEBOT_SSH_PASS: SSH password
"""
import os
import sys
import time

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

cmds = [
    "systemctl stop openclaw 2>/dev/null; systemctl disable openclaw 2>/dev/null; pkill -9 -f openclaw 2>/dev/null; echo STEP1_DONE",
    "rm -rf /root/.openclaw /tmp/openclaw; echo STEP2_CONFIG_REMOVED",
    "rm -f /etc/systemd/system/openclaw.service; systemctl daemon-reload; echo STEP3_SERVICE_REMOVED",
    "which openclaw 2>/dev/null || echo NO_OPENCLAW_BINARY",
    "ls -la $(npm root -g)/openclaw/package.json 2>/dev/null || echo NO_GLOBAL_OPENCLAW",
    "npm root -g",
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    print(f"CMD: {cmd[:60]}")
    if out: print(f"  OUT: {out[:200]}")
    if err: print(f"  ERR: {err[:200]}")
    print()

ssh.close()
