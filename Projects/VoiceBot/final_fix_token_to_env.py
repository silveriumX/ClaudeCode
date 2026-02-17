#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ ФИКС: OpenClaw использует long polling ТОЛЬКО если botToken задан через .env,
а НЕ через openclaw.json.

Переносим botToken из конфига в /opt/openclaw/.env
"""
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

print("=== 1. Remove botToken from openclaw.json ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/.openclaw/openclaw.json')
out = stdout.read().decode("utf-8", errors="replace")
cfg = json.loads(out)
token = cfg['channels']['telegram'].get('botToken', '')
print(f"Token from config: {token[:20]}...{token[-10:]}")

# Remove botToken from config
if 'botToken' in cfg['channels']['telegram']:
    del cfg['channels']['telegram']['botToken']
    print("Removed botToken from config")

# Write config back
sftp = ssh.open_sftp()
with sftp.open('/root/.openclaw/openclaw.json', 'w') as f:
    f.write(json.dumps(cfg, indent=2, ensure_ascii=False))
sftp.close()
print("Config updated")

print("\n=== 2. Add TELEGRAM_BOT_TOKEN to /opt/openclaw/.env ===")
stdin, stdout, stderr = ssh.exec_command('cat /opt/openclaw/.env 2>/dev/null')
env_content = stdout.read().decode("utf-8", errors="replace")
lines = [l for l in env_content.splitlines() if not l.startswith('TELEGRAM_BOT_TOKEN=')]
lines.append(f'TELEGRAM_BOT_TOKEN={token}')
new_env = '\n'.join(lines) + '\n'

sftp = ssh.open_sftp()
with sftp.open('/opt/openclaw/.env', 'w') as f:
    f.write(new_env)
sftp.close()
print(f"Added TELEGRAM_BOT_TOKEN to .env")

print("\n=== 3. Restart OpenClaw ===")
stdin, stdout, stderr = ssh.exec_command('systemctl restart openclaw && sleep 12 && systemctl status openclaw --no-pager | head -15')
out = stdout.read().decode("utf-8", errors="replace")
print(out.encode("ascii", errors="replace").decode("ascii")[:1200])

print("\n=== 4. Check logs for telegram with username ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 15 --no-pager')
out = stdout.read().decode("utf-8", errors="replace")
lines = [l.encode("ascii", errors="replace").decode("ascii")[:150] for l in out.splitlines()[-10:]]
for line in lines:
    print(line)

print("\n=== Fixed! Token in .env, OpenClaw should use long polling now ===")

ssh.close()
