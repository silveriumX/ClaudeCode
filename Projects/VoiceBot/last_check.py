#!/usr/bin/env python3
"""Quick log check then propose alternatives."""
import os, sys, time
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
import subprocess, json

# Last 30 lines of journalctl
print("=== JOURNALCTL last 30 ===")
r = subprocess.run(["journalctl", "-u", "openclaw", "-n", "30", "--no-pager"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines():
    print(line[:200])

# Last 10 lines of log file
print()
print("=== LOG FILE last 10 ===")
r = subprocess.run(["tail", "-10", "/tmp/openclaw/openclaw-2026-02-09.log"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines():
    try:
        j = json.loads(line)
        parts = [str(v) for v in j.values()]
        print(" | ".join(parts)[:200])
    except:
        print(line[:200])
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/last_check.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/last_check.py', timeout=15)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
ssh.close()
