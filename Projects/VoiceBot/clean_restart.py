#!/usr/bin/env python3
"""Kill ALL openclaw processes hard, then clean restart."""
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

print("=== 1. Stop service ===")
stdin, stdout, stderr = ssh.exec_command('systemctl stop openclaw')
stdout.read()
time.sleep(2)

print("=== 2. Kill ALL openclaw and node processes ===")
stdin, stdout, stderr = ssh.exec_command('pkill -9 -f "openclaw" 2>/dev/null; pkill -9 -f "run-node.mjs" 2>/dev/null; echo done')
stdout.read()
time.sleep(2)

print("=== 3. Check nothing left ===")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep -E "openclaw|run-node" | grep -v grep')
out = stdout.read().decode("utf-8", errors="replace")
if out.strip():
    print(f"  STILL RUNNING: {out.strip()}")
else:
    print("  All openclaw processes killed")

print("\n=== 4. Check Telegram connections ===")
stdin, stdout, stderr = ssh.exec_command('ss -tnp | grep 149.154')
out = stdout.read().decode("utf-8", errors="replace")
if out.strip():
    for line in out.strip().splitlines():
        print(f"  {line.encode('ascii', errors='replace').decode('ascii')[:120]}")
else:
    print("  No Telegram connections - CLEAN!")

print("\n=== 5. Wait 3 seconds, then start OpenClaw fresh ===")
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command('systemctl start openclaw && sleep 10 && systemctl status openclaw --no-pager | head -10')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:800])

print("\n=== 6. Check logs ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 15 --no-pager')
out = stdout.read().decode("utf-8", errors="replace")
lines = [l.encode("ascii", errors="replace").decode("ascii")[:150] for l in out.splitlines()[-10:]]
for line in lines:
    print(line)

print("\n=== 7. Check Telegram connections (should be ONLY openclaw) ===")
stdin, stdout, stderr = ssh.exec_command('ss -tnp | grep 149.154')
out = stdout.read().decode("utf-8", errors="replace")
if out.strip():
    for line in out.strip().splitlines():
        print(f"  {line.encode('ascii', errors='replace').decode('ascii')[:120]}")

print("\n=== CLEAN RESTART DONE! Send /start to bot NOW ===")

ssh.close()
