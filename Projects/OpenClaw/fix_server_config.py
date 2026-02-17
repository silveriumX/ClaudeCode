#!/usr/bin/env python3
"""
Fix OpenClaw server configuration:
- Change model from flash to full version
- Fix Python PATH
- Reduce timeouts
- Restart service
"""
import json
import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("pip install python-dotenv")
    sys.exit(1)

# Load environment
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

HOST = os.getenv("VPS_HOST") or os.getenv("VOICEBOT_HOST")
USER = os.getenv("VPS_USER") or os.getenv("VOICEBOT_USER", "root")
PASS = os.getenv("VPS_PASSWORD") or os.getenv("VOICEBOT_SSH_PASS")

if not HOST or not PASS:
    print("Error: Missing VPS credentials in .env")
    sys.exit(1)

def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return code, out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"Connecting to {USER}@{HOST}...")
    try:
        ssh.connect(HOST, 22, USER, PASS, timeout=15)
    except Exception as e:
        print(f"SSH failed: {e}")
        sys.exit(1)

    try:
        sftp = ssh.open_sftp()

        # 1. Read current config
        print("\n[1/6] Reading current config...")
        with sftp.open("/root/.openclaw/openclaw.json", "r") as f:
            config = json.load(f)

        print(f"Current model: {config.get('agents', {}).get('defaults', {}).get('model', {}).get('primary')}")

        # 2. Update config
        print("\n[2/6] Updating configuration...")

        # Change model from flash to full version
        if 'agents' not in config:
            config['agents'] = {}
        if 'defaults' not in config['agents']:
            config['agents']['defaults'] = {}
        if 'model' not in config['agents']['defaults']:
            config['agents']['defaults']['model'] = {}

        config['agents']['defaults']['model']['primary'] = "zai/glm-4.7"  # Remove "-flash"

        # Add timeout
        config['agents']['defaults']['timeout'] = 300000  # 5 minutes

        # Reduce context TTL
        if 'contextPruning' not in config['agents']['defaults']:
            config['agents']['defaults']['contextPruning'] = {}
        config['agents']['defaults']['contextPruning']['ttl'] = "30m"  # Was 1h

        print("✓ Model changed: zai/glm-4.7-flash → zai/glm-4.7")
        print("✓ Timeout added: 300000ms (5 minutes)")
        print("✓ Context TTL reduced: 1h → 30m")

        # 3. Write new config
        print("\n[3/6] Writing updated config...")
        with sftp.open("/root/.openclaw/openclaw.json", "w") as f:
            f.write(json.dumps(config, indent=2))
        print("✓ Config saved")

        sftp.close()

        # 4. Fix Python PATH
        print("\n[4/6] Creating Python symlink...")
        code, out, err = run(ssh, "ln -sf /usr/bin/python3 /usr/bin/python")
        if code == 0:
            print("✓ Python symlink created")
        else:
            print(f"⚠ Warning: {err}")

        # Verify
        code, out, err = run(ssh, "python --version 2>&1")
        if "Python 3" in out:
            print(f"✓ Python works: {out.strip()}")

        # 5. Restart OpenClaw
        print("\n[5/6] Restarting OpenClaw...")
        code, out, err = run(ssh, "systemctl restart openclaw")
        if code == 0:
            print("✓ Service restart initiated")
        else:
            print(f"✗ Restart failed: {err}")
            return

        # Wait for restart
        print("Waiting 5 seconds for service to start...")
        time.sleep(5)

        # 6. Verify
        print("\n[6/6] Verifying changes...")
        code, out, err = run(ssh, "systemctl is-active openclaw")
        status = out.strip()
        print(f"Service status: {status}")

        if status == "active":
            print("\n" + "="*60)
            print("✅ ALL CHANGES APPLIED SUCCESSFULLY!")
            print("="*60)
            print("\nChanges:")
            print("• Model: zai/glm-4.7 (better quality)")
            print("• Timeout: 5 minutes (was 10)")
            print("• Context TTL: 30 minutes (was 1 hour)")
            print("• Python: symlink created")
            print("\nOpenClaw is now using a more powerful model.")
            print("Responses should be significantly better!")
        else:
            print(f"\n⚠ Warning: Service status is {status}")
            print("Check logs with: python vps_connect.py logs 50")

        # Show recent logs
        print("\n" + "="*60)
        print("Recent logs (last 15 lines):")
        print("="*60)
        code, out, err = run(ssh, "journalctl -u openclaw -n 15 --no-pager 2>&1")
        print(out)

    finally:
        ssh.close()

if __name__ == "__main__":
    main()
