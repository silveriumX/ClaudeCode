#!/usr/bin/env python3
"""
Step 2b: Install OpenClaw with longer timeout for slow connections.

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

# Run install in background, save output to file
cmd = "npm install -g openclaw > /tmp/openclaw_install.log 2>&1; echo EXIT_CODE=$? >> /tmp/openclaw_install.log"
print("Starting npm install (background)...")
ssh.exec_command(cmd)

# Wait and poll
for i in range(24):  # up to 4 minutes
    time.sleep(10)
    try:
        stdin, stdout, stderr = ssh.exec_command("tail -3 /tmp/openclaw_install.log 2>/dev/null", timeout=10)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        print(f"  [{(i+1)*10}s] {out[-200:]}")
        if "EXIT_CODE=" in out:
            break
    except:
        print(f"  [{(i+1)*10}s] waiting...")

# Final check
time.sleep(2)
stdin, stdout, stderr = ssh.exec_command("cat /tmp/openclaw_install.log | tail -10", timeout=10)
out = stdout.read().decode("utf-8", errors="replace").strip()
print(f"\n=== INSTALL LOG (last 10 lines) ===\n{out}")

stdin, stdout, stderr = ssh.exec_command("openclaw --version 2>&1", timeout=10)
out = stdout.read().decode("utf-8", errors="replace").strip()
print(f"\n=== VERSION ===\n  {out}")

stdin, stdout, stderr = ssh.exec_command("which openclaw 2>&1", timeout=10)
out = stdout.read().decode("utf-8", errors="replace").strip()
print(f"  Binary: {out}")

ssh.close()
