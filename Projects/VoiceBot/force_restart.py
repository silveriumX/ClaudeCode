#!/usr/bin/env python3
"""Force restart OpenClaw."""
import os, sys, time
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

print("=== Kill ALL openclaw ===")
ssh.exec_command('pkill -9 -f "openclaw" 2>/dev/null; pkill -9 -f "run-node.mjs" 2>/dev/null')
time.sleep(3)

print("=== Start service ===")
stdin, stdout, stderr = ssh.exec_command('systemctl start openclaw && sleep 12 && systemctl status openclaw --no-pager | head -10')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:800])

print("\n=== Logs ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 10 --no-pager')
out = stdout.read().decode("utf-8", errors="replace")
for line in out.splitlines()[-8:]:
    print(line.encode("ascii", errors="replace").decode("ascii")[:150])

ssh.close()
