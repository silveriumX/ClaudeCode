#!/usr/bin/env python3
"""Kill all competing python processes that talk to Telegram, then restart OpenClaw."""
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

print("=== 1. Kill ALL python3 processes on VPS ===")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep python3 | grep -v grep')
out = stdout.read().decode("utf-8", errors="replace")
print("Existing python3 processes:")
for line in out.strip().splitlines():
    print(f"  {line.encode('ascii', errors='replace').decode('ascii')[:120]}")

stdin, stdout, stderr = ssh.exec_command('killall python3 2>/dev/null; echo "killed"')
out = stdout.read().decode("utf-8", errors="replace")
print(f"\n{out.strip()}")

print("\n=== 2. Restart OpenClaw ===")
stdin, stdout, stderr = ssh.exec_command('systemctl restart openclaw && sleep 8 && systemctl status openclaw --no-pager | head -10')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:800])

print("\n=== 3. Check no more conflicts ===")
stdin, stdout, stderr = ssh.exec_command('ss -tnp | grep 149.154')
out = stdout.read().decode("utf-8", errors="replace")
if out.strip():
    lines = out.strip().splitlines()
    for line in lines:
        print(f"  {line.encode('ascii', errors='replace').decode('ascii')[:120]}")
    # Check if only openclaw
    openclaw_only = all("openclaw" in l for l in lines)
    print(f"\nOnly OpenClaw connections: {openclaw_only}")
else:
    print("  No Telegram connections yet (OpenClaw may still be starting)")

print("\n=== DONE! Now send /start to @cosmicprincesskaguyabot ===")

ssh.close()
