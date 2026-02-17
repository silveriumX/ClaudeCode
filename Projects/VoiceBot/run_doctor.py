#!/usr/bin/env python3
"""Check config and run openclaw doctor."""
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
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, "root", PASS, timeout=15)

print("=== 1. Check current telegram config ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json | jq .channels.telegram')
out = stdout.read().decode("utf-8", errors="replace")
print(out[:800])

print("\n=== 2. Run openclaw doctor --fix ===")
stdin, stdout, stderr = ssh.exec_command('cd /opt/openclaw && node scripts/run-node.mjs doctor --fix 2>&1')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:1500])

print("\n=== 3. Check config after doctor ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json | jq .channels.telegram')
out = stdout.read().decode("utf-8", errors="replace")
print(out[:800])

print("\n=== 4. Restart OpenClaw ===")
stdin, stdout, stderr = ssh.exec_command('systemctl restart openclaw && sleep 10 && systemctl status openclaw --no-pager | head -12')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:1000])

ssh.close()
