#!/usr/bin/env python3
"""
Set OpenClaw on VPS to use GLM-4.7 via Z.AI provider.
- Adds ZAI_API_KEY to /root/.openclaw/.env (from OPENCLAW_ZAI_API_KEY env var).
- Ensures /root/.openclaw/openclaw.json uses model zai/glm-4.7 as primary.

Environment variables (supports both VPS_* and VOICEBOT_* prefixes):
- VPS_HOST / VOICEBOT_HOST: VPS IP or hostname
- VPS_USER / VOICEBOT_USER: SSH username (default: root)
- VPS_PASSWORD / VOICEBOT_SSH_PASS: SSH password
- ZAI_API_KEY / OPENCLAW_ZAI_API_KEY: Z.AI API key
- TELEGRAM_BOT_TOKEN / OPENCLAW_TELEGRAM_BOT_TOKEN: Telegram bot token (optional)

Do NOT paste your API key in chat. Set it locally and run:
  $env:VPS_PASSWORD = "YourSSHPassword"
  $env:OPENCLAW_ZAI_API_KEY = "sk-..."
  python set_glm.py
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
REMOTE_DIR = "/root/.openclaw"
OPENCLAW_JSON = "/root/.openclaw/openclaw.json"
ZAI_KEY_VAR = "OPENCLAW_ZAI_API_KEY"
TG_TOKEN_VAR = "OPENCLAW_TELEGRAM_BOT_TOKEN"
PRIMARY_MODEL = "zai/glm-4.7"


def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return code, out, err


def main():
    # Support both variable names
    api_key = os.environ.get("ZAI_API_KEY") or os.environ.get(ZAI_KEY_VAR, "")
    api_key = api_key.strip()
    if not api_key:
        print("Set ZAI_API_KEY or OPENCLAW_ZAI_API_KEY (your Z.AI / GLM-4.7 API key) in environment and run again.")
        print("Do not paste the key in chat.")
        sys.exit(1)
    if not PASS:
        print("Set VPS_PASSWORD or VOICEBOT_SSH_PASS for SSH.")
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
        sftp = ssh.open_sftp()

        # 1. Update .env: ZAI_API_KEY + optional TELEGRAM_BOT_TOKEN
        code, content, _ = run(ssh, f"cat {REMOTE_DIR}/.env 2>/dev/null || true")
        lines = [l for l in content.splitlines() if l.strip()]
        new_lines = []
        seen = set()
        for line in lines:
            if line.strip().startswith("ZAI_API_KEY="):
                new_lines.append("ZAI_API_KEY=" + api_key)
                seen.add("ZAI_API_KEY")
            elif line.strip().startswith("TELEGRAM_BOT_TOKEN="):
                # Support both variable names
                tg = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get(TG_TOKEN_VAR, "")
                tg = tg.strip()
                if tg:
                    new_lines.append("TELEGRAM_BOT_TOKEN=" + tg)
                seen.add("TELEGRAM_BOT_TOKEN")
            else:
                new_lines.append(line)
        if "ZAI_API_KEY" not in seen:
            new_lines.append("ZAI_API_KEY=" + api_key)
        # Support both variable names
        tg = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get(TG_TOKEN_VAR, "")
        tg = tg.strip()
        if tg and "TELEGRAM_BOT_TOKEN" not in seen:
            new_lines.append("TELEGRAM_BOT_TOKEN=" + tg)
        env_content = "\n".join(new_lines) + "\n"
        with sftp.open(f"{REMOTE_DIR}/.env", "w") as f:
            f.write(env_content)
        print("[OK] Updated", REMOTE_DIR + "/.env (ZAI_API_KEY" + (", TELEGRAM_BOT_TOKEN" if tg else "") + ").")

        # 2. Ensure ~/.openclaw exists and openclaw.json has primary model zai/glm-4.7
        run(ssh, "mkdir -p /root/.openclaw")
        code, json_content, _ = run(ssh, f"cat {OPENCLAW_JSON} 2>/dev/null || echo '{{}}'")
        try:
            cfg = json.loads(json_content) if json_content.strip() else {}
        except json.JSONDecodeError:
            cfg = {}
        if "agents" not in cfg:
            cfg["agents"] = {}
        if "defaults" not in cfg["agents"]:
            cfg["agents"]["defaults"] = {}
        if "model" not in cfg["agents"]["defaults"]:
            cfg["agents"]["defaults"]["model"] = {}
        cfg["agents"]["defaults"]["model"]["primary"] = PRIMARY_MODEL
        if "channels" not in cfg:
            cfg["channels"] = {}
        if "telegram" not in cfg["channels"]:
            cfg["channels"]["telegram"] = {}
        cfg["channels"]["telegram"]["enabled"] = True
        cfg["channels"]["telegram"]["dmPolicy"] = "pairing"
        new_json = json.dumps(cfg, indent=2)
        with sftp.open(OPENCLAW_JSON, "w") as f:
            f.write(new_json)
        print("[OK] Set primary model", PRIMARY_MODEL, "and Telegram channel in", OPENCLAW_JSON)

        sftp.close()
        run(ssh, "systemctl restart openclaw")
        print("[OK] Restarted openclaw.")
        code, out, _ = run(ssh, "systemctl is-active openclaw")
        print("  openclaw status:", out.strip() if out else "unknown")
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
