#!/usr/bin/env python3
"""
Append or update ANTHROPIC_API_KEY in /root/.openclaw/.env on VPS.
Uses OPENCLAW_ANTHROPIC_KEY from environment. ASCII-only output for Windows.

Environment variables (supports both VPS_* and VOICEBOT_* prefixes):
- VPS_HOST / VOICEBOT_HOST: VPS IP or hostname
- VPS_USER / VOICEBOT_USER: SSH username (default: root)
- VPS_PASSWORD / VOICEBOT_SSH_PASS: SSH password
- ANTHROPIC_API_KEY / OPENCLAW_ANTHROPIC_KEY: API key to set
"""
import io
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
KEY_VAR = "OPENCLAW_ANTHROPIC_KEY"


def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return code, out, err


def main():
    # Support both variable names
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(KEY_VAR, "")
    api_key = api_key.strip()
    if not api_key:
        print("Set ANTHROPIC_API_KEY or OPENCLAW_ANTHROPIC_KEY in environment and run again.")
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
        # Read current .env
        code, content, _ = run(ssh, f"cat {REMOTE_DIR}/.env 2>/dev/null || true")
        lines = [l for l in content.splitlines() if l.strip()]
        new_lines = []
        has_key = False
        for line in lines:
            if line.strip().startswith("ANTHROPIC_API_KEY="):
                new_lines.append(f"ANTHROPIC_API_KEY={api_key}")
                has_key = True
            else:
                new_lines.append(line)
        if not has_key:
            new_lines.append(f"ANTHROPIC_API_KEY={api_key}")

        new_content = "\n".join(new_lines) + "\n"
        # Write via SFTP to avoid shell escaping of API key
        sftp = ssh.open_sftp()
        try:
            with sftp.open(f"{REMOTE_DIR}/.env", "w") as f:
                f.write(new_content)
        finally:
            sftp.close()
        print("Updated", REMOTE_DIR + "/.env with ANTHROPIC_API_KEY.")
        print("Restart: ssh root@%s systemctl restart openclaw" % HOST)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
