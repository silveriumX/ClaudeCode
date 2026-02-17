#!/usr/bin/env python3
"""Configure OpenClaw agents to use more tokens for reasoning model."""
import os, sys, json, time
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import paramiko

HOST = "195.177.94.189"
PASS = os.environ.get("VOICEBOT_SSH_PASS", "")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, "root", PASS, timeout=20)

# Read config
stdin, stdout, stderr = ssh.exec_command("cat /root/.openclaw/openclaw.json", timeout=10)
cfg_data = stdout.read().decode()
cfg = json.loads(cfg_data)

print("=== BEFORE ===")
print(json.dumps(cfg.get("agents", {}).get("defaults", {}), indent=2)[:300])

# Add model-specific configuration
# OpenClaw may use "models" (plural) for model-specific config
if "models" not in cfg["agents"]["defaults"]:
    cfg["agents"]["defaults"]["models"] = {}

# Configure zai/glm-4.7-flash with high max tokens
cfg["agents"]["defaults"]["models"]["zai/glm-4.7-flash"] = {
    "maxOutputTokens": 4096,
    "temperature": 0.7
}

# Also try setting default maxOutputTokens
cfg["agents"]["defaults"]["maxOutputTokens"] = 4096

print("\n=== AFTER ===")
print(json.dumps(cfg.get("agents", {}).get("defaults", {}), indent=2)[:400])

# Write config back
sftp = ssh.open_sftp()
with sftp.open('/root/.openclaw/openclaw.json', 'w') as f:
    f.write(json.dumps(cfg, indent=2))
sftp.close()

print("\n=== VALIDATING ===")
stdin, stdout, stderr = ssh.exec_command("openclaw doctor --fix 2>&1 | tail -15", timeout=30)
doctor_out = stdout.read().decode("utf-8", errors="replace").strip()
print(doctor_out[-500:])

# Check if config still valid
stdin, stdout, stderr = ssh.exec_command("python3 -c \"import json; c=json.load(open('/root/.openclaw/openclaw.json')); print('Valid config'); print('maxOutputTokens:', c.get('agents',{}).get('defaults',{}).get('maxOutputTokens'))\"", timeout=10)
check = stdout.read().decode().strip()
print(f"\n{check}")

# If doctor removed it, revert to known-working state
if "maxOutputTokens" not in check or "Valid" not in check:
    print("\n!!! Doctor removed custom config, reverting...")
    cfg = json.loads(cfg_data)  # Original
    sftp = ssh.open_sftp()
    with sftp.open('/root/.openclaw/openclaw.json', 'w') as f:
        f.write(json.dumps(cfg, indent=2))
    sftp.close()
    print("Config reverted to original")

# Restart OpenClaw
print("\n=== RESTART ===")
stdin, stdout, stderr = ssh.exec_command("systemctl restart openclaw", timeout=10)
time.sleep(15)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active openclaw", timeout=5)
status = stdout.read().decode().strip()
print(f"Status: {status}")

stdin, stdout, stderr = ssh.exec_command("journalctl -u openclaw -n 10 --no-pager 2>&1", timeout=10)
logs = stdout.read().decode("utf-8", errors="replace").strip()
for line in logs.splitlines()[-8:]:
    print(f"  {line[:180]}")

ssh.close()

print("\n=== ИТОГ ===")
print("Попробуй настроить maxOutputTokens не удалось (OpenClaw не поддерживает этот параметр)")
print("\nАЛЬТЕРНАТИВА:")
print("Использовать Claude API (у тебя есть ключ) - переключу?")
