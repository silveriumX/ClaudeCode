#!/usr/bin/env python3
"""Clean restart OpenClaw, wait, then send test getUpdates to see if it works."""
import os, sys, time, json
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

SCRIPT = '''#!/usr/bin/env python3
import subprocess, time, json, urllib.request

print("=== Restart OpenClaw ===")
subprocess.run(["systemctl", "restart", "openclaw"])
time.sleep(15)

r = subprocess.run(["journalctl", "-u", "openclaw", "-n", "15", "--no-pager"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines()[-10:]:
    print(line[:150])

print()
print("=== Wait 5 more seconds, then check for 409 errors ===")
time.sleep(5)

r = subprocess.run(["journalctl", "-u", "openclaw", "--since", "10 seconds ago", "--no-pager"], capture_output=True, text=True)
lines = r.stdout.strip().splitlines()
conflict = [l for l in lines if "conflict" in l.lower() or "409" in l]
if conflict:
    print("CONFLICT FOUND:")
    for l in conflict:
        print(f"  {l[:180]}")
else:
    print("NO conflicts in last 10 seconds - GOOD!")

print()
print("=== Check if OpenClaw is actually polling ===")
r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
oc = [l for l in r.stdout.splitlines() if "openclaw" in l and "149.154" in l]
print(f"OpenClaw Telegram connections: {len(oc)}")
for l in oc:
    print(f"  {l.strip()[:120]}")
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/clean_test.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/clean_test.py', timeout=40)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))

ssh.close()
