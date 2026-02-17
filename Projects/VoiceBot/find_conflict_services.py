#!/usr/bin/env python3
"""Find and disable ALL systemd services that conflict with OpenClaw Telegram."""
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

SCRIPT = '''#!/usr/bin/env python3
import subprocess, os, time

# Find all systemd services running python bots
print("=== ALL bot-related systemd services ===")
r = subprocess.run(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"], capture_output=True, text=True)
for line in r.stdout.splitlines():
    if any(word in line.lower() for word in ["bot", "voice", "chat", "media", "cursor", "download"]):
        print(f"  {line.strip()[:120]}")

print()

# Find what uses our Telegram token
TOKEN_PREFIX = "8445718442"
print(f"=== Files containing token {TOKEN_PREFIX} ===")
r = subprocess.run(["grep", "-r", TOKEN_PREFIX, "/root/", "--include=*.env", "--include=*.py", "--include=*.json", "-l"],
                    capture_output=True, text=True, timeout=10)
for line in r.stdout.strip().splitlines():
    print(f"  {line}")

print()

# Check each .env file for this token
print("=== Check .env files ===")
import glob
for env_file in glob.glob("/root/**/.env", recursive=True):
    try:
        with open(env_file) as f:
            content = f.read()
        if TOKEN_PREFIX in content:
            print(f"  CONFLICT: {env_file} contains our token!")
    except:
        pass

# Check all running python processes
print()
print("=== Running python processes connected to Telegram ===")
r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
for line in r.stdout.splitlines():
    if "149.154" in line and "pid=" in line:
        pid = line.split("pid=")[1].split(",")[0].split(")")[0]
        try:
            r2 = subprocess.run(["cat", f"/proc/{pid}/cmdline"], capture_output=True, text=True)
            cmd = r2.stdout.replace("\\x00", " ")[:100]
            print(f"  PID {pid}: {cmd}")
        except:
            pass
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/find_conflicts.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/find_conflicts.py', timeout=20)
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))

ssh.close()
