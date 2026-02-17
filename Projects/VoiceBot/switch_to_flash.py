#!/usr/bin/env python3
"""Switch OpenClaw to glm-4.7-flash and restart."""
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

print("=== 1. Update model in config ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json')
out = stdout.read().decode("utf-8", errors="replace")
cfg = json.loads(out)

old = cfg['agents']['defaults']['model']['primary']
cfg['agents']['defaults']['model']['primary'] = 'zai/glm-4.7-flash'
print(f"Changed: {old} -> zai/glm-4.7-flash")

sftp = ssh.open_sftp()
with sftp.open('/root/.openclaw/openclaw.json', 'w') as f:
    f.write(json.dumps(cfg, indent=2, ensure_ascii=False))
sftp.close()

print("\n=== 2. Kill foreground OpenClaw and restart service ===")
stdin, stdout, stderr = ssh.exec_command('pkill -f "run-node.mjs gateway" 2>/dev/null; sleep 2; systemctl restart openclaw && sleep 10 && systemctl status openclaw --no-pager | head -12')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:1000])

print("\n=== 3. Check logs ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 10 --no-pager')
out = stdout.read().decode("utf-8", errors="replace")
for line in out.splitlines()[-8:]:
    print(line.encode("ascii", errors="replace").decode("ascii")[:150])

print("\n=== DONE! Model switched to glm-4.7-flash ===")
print("Send /start to @cosmicprincesskaguyabot NOW!")

ssh.close()
