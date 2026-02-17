#!/usr/bin/env python3
"""Disable WhatsApp in CHANNELS section too."""
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

print("=== 1. Read config ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json')
out = stdout.read().decode("utf-8", errors="replace")
cfg = json.loads(out)

print(f"channels.whatsapp.enabled: {cfg['channels'].get('whatsapp', {}).get('enabled', 'NOT SET')}")
print(f"plugins.whatsapp.enabled: {cfg['plugins']['entries']['whatsapp']['enabled']}")

print("\n=== 2. Disable WhatsApp in channels ===")
if 'whatsapp' in cfg['channels']:
    cfg['channels']['whatsapp']['enabled'] = False
    print("Set channels.whatsapp.enabled = False")

# Write back
sftp = ssh.open_sftp()
with sftp.open('/root/.openclaw/openclaw.json', 'w') as f:
    f.write(json.dumps(cfg, indent=2, ensure_ascii=False))
sftp.close()

print("\n=== 3. WhatsApp ПОЛНОСТЬЮ отключен ===")
print("In PuTTY run:")
print("  node scripts/run-node.mjs channels login")

ssh.close()
