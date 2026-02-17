#!/usr/bin/env python3
"""Disable WhatsApp in OpenClaw config."""
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

print("=== 1. Disable WhatsApp in config ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json')
out = stdout.read().decode("utf-8", errors="replace")
cfg = json.loads(out)

print(f"WhatsApp enabled: {cfg['plugins']['entries']['whatsapp']['enabled']}")
cfg['plugins']['entries']['whatsapp']['enabled'] = False
print("Changed to: False")

# Write back
sftp = ssh.open_sftp()
with sftp.open('/root/.openclaw/openclaw.json', 'w') as f:
    f.write(json.dumps(cfg, indent=2, ensure_ascii=False))
sftp.close()

print("\n=== 2. Config saved ===")
print("Now in PuTTY run:")
print("  node scripts/run-node.mjs channels login")
print("\nIt should ask about TELEGRAM now (not WhatsApp)")

ssh.close()
