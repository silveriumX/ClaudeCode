#!/usr/bin/env python3
"""Kill ALL python processes connected to Telegram, then restart OpenClaw CLEAN."""
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
import subprocess, time, os

print("=== 1. Stop OpenClaw ===")
subprocess.run(["systemctl", "stop", "openclaw"])
time.sleep(2)
subprocess.run(["pkill", "-9", "-f", "openclaw"], capture_output=True)
subprocess.run(["pkill", "-9", "-f", "run-node.mjs"], capture_output=True)
time.sleep(1)

print("=== 2. Find ALL processes connected to Telegram (149.154) ===")
r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
pids_to_kill = set()
for line in r.stdout.splitlines():
    if "149.154" in line:
        print("  FOUND:", line.strip()[:120])
        # extract pid
        if "pid=" in line:
            pid_str = line.split("pid=")[1].split(",")[0].split(")")[0]
            try:
                pid = int(pid_str)
                # don't kill system processes
                if pid > 1000:
                    pids_to_kill.add(pid)
            except:
                pass

print(f"\\n=== 3. Kill {len(pids_to_kill)} processes: {pids_to_kill} ===")
for pid in pids_to_kill:
    # check what it is first
    try:
        r = subprocess.run(["cat", f"/proc/{pid}/cmdline"], capture_output=True, text=True)
        cmd = r.stdout.replace("\\x00", " ").strip()
        print(f"  PID {pid}: {cmd[:100]}")
        os.kill(pid, 9)
        print(f"    KILLED")
    except Exception as e:
        print(f"    Error: {e}")

time.sleep(3)

print("\\n=== 4. Verify no more Telegram connections ===")
r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
tg = [l for l in r.stdout.splitlines() if "149.154" in l and "ESTAB" in l]
print(f"  Remaining Telegram connections: {len(tg)}")

print("\\n=== 5. Start OpenClaw FRESH ===")
subprocess.run(["systemctl", "start", "openclaw"])
time.sleep(12)

r = subprocess.run(["systemctl", "is-active", "openclaw"], capture_output=True, text=True)
print(f"  Service: {r.stdout.strip()}")

r = subprocess.run(["journalctl", "-u", "openclaw", "-n", "8", "--no-pager"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines()[-6:]:
    print(f"  {line[:150]}")

print("\\n=== 6. Verify connections ===")
r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
tg = [l for l in r.stdout.splitlines() if "149.154" in l and "ESTAB" in l]
oc = [l for l in tg if "openclaw" in l]
print(f"  Telegram: {len(tg)} total, {len(oc)} openclaw")
if len(tg) == len(oc):
    print("  CLEAN! Only OpenClaw connected to Telegram")
else:
    print("  WARNING: other processes still connected!")
    for l in tg:
        if "openclaw" not in l:
            print(f"    {l.strip()[:120]}")
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/kill_conflicts.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/kill_conflicts.py', timeout=40)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii"))
if err.strip():
    print("STDERR:", err.encode("ascii", errors="replace").decode("ascii")[:300])

ssh.close()
