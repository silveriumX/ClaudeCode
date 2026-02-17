#!/usr/bin/env python3
"""
Step 2: Fresh install OpenClaw globally via npm.

Installs to /usr/lib/node_modules/openclaw (or wherever npm global root is).

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
    ("Install OpenClaw globally", "npm install -g openclaw 2>&1 | tail -5"),
    ("Check version", "openclaw --version 2>&1"),
    ("Find binary", "which openclaw 2>&1"),
    ("Find package", "ls $(npm root -g)/openclaw/package.json 2>&1"),
    ("Verify installation", "test -f /usr/bin/openclaw && echo BINARY_EXISTS || echo BINARY_MISSING"),
]

for desc, cmd in cmds:
    print(f"=== {desc} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out: print(f"  {out[:500]}")
    if err: print(f"  ERR: {err[:500]}")
    print()

ssh.close()
