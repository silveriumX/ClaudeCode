#!/usr/bin/env python3
"""
Force Telegram bot token in openclaw.json and restart.
Fixes 'bot not responding' when old bot was in config.

Environment variables (supports both VPS_* and VOICEBOT_* prefixes):
- VPS_HOST / VOICEBOT_HOST: VPS IP or hostname
- VPS_USER / VOICEBOT_USER: SSH username (default: root)
- VPS_PASSWORD / VOICEBOT_SSH_PASS: SSH password
- TELEGRAM_BOT_TOKEN / OPENCLAW_TELEGRAM_BOT_TOKEN: Telegram bot token
"""
import io
import json
import logging
import os
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Support both VPS_* and VOICEBOT_* variable names for backward compatibility
HOST = os.environ.get("VPS_HOST") or os.environ.get("VOICEBOT_HOST", "")
PORT = int(os.environ.get("VPS_PORT", "22"))
USER = os.environ.get("VPS_USER") or os.environ.get("VOICEBOT_USER", "root")
PASS = os.environ.get("VPS_PASSWORD") or os.environ.get("VOICEBOT_SSH_PASS", "")
OPENCLAW_JSON = "/root/.openclaw/openclaw.json"
TG_TOKEN_VAR = "OPENCLAW_TELEGRAM_BOT_TOKEN"


def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return code, out, err


def main():
    # Support both variable names
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get(TG_TOKEN_VAR, "")
    token = token.strip()
    if not token:
        print("Set TELEGRAM_BOT_TOKEN or OPENCLAW_TELEGRAM_BOT_TOKEN and run again.")
        sys.exit(1)
    if not PASS:
        print("Set VPS_PASSWORD or VOICEBOT_SSH_PASS.")
        sys.exit(1)
    if not HOST:
        print("Set VPS_HOST or VOICEBOT_HOST for VPS address.")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        logger.info(f"Connecting to {USER}@{HOST}:{PORT}")
        ssh.connect(HOST, PORT, USER, PASS, timeout=15)
        logger.info("SSH connection established")
    except paramiko.AuthenticationException as e:
        logger.error(f"SSH authentication failed: {e}")
        print("SSH authentication failed:", e)
        sys.exit(1)
    except paramiko.SSHException as e:
        logger.error(f"SSH connection error: {e}")
        print("SSH connection error:", e)
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected SSH error: {e}")
        print("SSH failed:", e)
        sys.exit(1)

    try:
        code, json_content, _ = run(ssh, f"cat {OPENCLAW_JSON} 2>/dev/null || echo '{{}}'")
        try:
            cfg = json.loads(json_content) if json_content.strip() else {}
        except json.JSONDecodeError:
            cfg = {}
        if "channels" not in cfg:
            cfg["channels"] = {}
        if "telegram" not in cfg["channels"]:
            cfg["channels"]["telegram"] = {}
        cfg["channels"]["telegram"]["enabled"] = True
        cfg["channels"]["telegram"]["dmPolicy"] = "pairing"
        cfg["channels"]["telegram"]["botToken"] = token
        new_json = json.dumps(cfg, indent=2)
        sftp = ssh.open_sftp()
        with sftp.open(OPENCLAW_JSON, "w") as f:
            f.write(new_json)
        sftp.close()
        print("[OK] Set botToken in", OPENCLAW_JSON)
        run(ssh, "systemctl restart openclaw")
        print("[OK] Restarted openclaw.")
        code, out, _ = run(ssh, "journalctl -u openclaw -n 15 --no-pager 2>/dev/null")
        for line in out.splitlines():
            if "telegram" in line.lower():
                print(" ", line.strip()[:100])
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
