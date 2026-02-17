#!/usr/bin/env python3
"""Remove unsupported 'timeout' field from OpenClaw config"""
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import paramiko
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

HOST = os.getenv("VPS_HOST") or os.getenv("VOICEBOT_HOST")
USER = os.getenv("VPS_USER") or os.getenv("VOICEBOT_USER", "root")
PASS = os.getenv("VPS_PASSWORD") or os.getenv("VOICEBOT_SSH_PASS")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, USER, PASS, timeout=15)

try:
    sftp = ssh.open_sftp()

    # Read config
    print("Reading config...")
    with sftp.open("/root/.openclaw/openclaw.json", "r") as f:
        config = json.load(f)

    # Remove timeout field
    if 'agents' in config and 'defaults' in config['agents']:
        if 'timeout' in config['agents']['defaults']:
            del config['agents']['defaults']['timeout']
            print("✓ Removed unsupported 'timeout' field")

    # Write back
    print("Saving config...")
    with sftp.open("/root/.openclaw/openclaw.json", "w") as f:
        f.write(json.dumps(config, indent=2))

    sftp.close()

    # Restart
    print("Restarting OpenClaw...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart openclaw")
    stdout.channel.recv_exit_status()

    import time
    time.sleep(3)

    # Check status
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active openclaw")
    status = stdout.read().decode().strip()
    print(f"\n✅ Service status: {status}")

    # Show config
    print("\n✅ Fixed configuration applied!")
    print("\nCurrent model:", config.get('agents', {}).get('defaults', {}).get('model', {}).get('primary'))
    print("Context TTL:", config.get('agents', {}).get('defaults', {}).get('contextPruning', {}).get('ttl'))

finally:
    ssh.close()
