#!/usr/bin/env python3
"""
Get recent OpenClaw logs and check if messages arrive from Telegram.

Environment variables (supports both VPS_* and VOICEBOT_* prefixes):
- VPS_HOST / VOICEBOT_HOST: VPS IP or hostname
- VPS_USER / VOICEBOT_USER: SSH username (default: root)
- VPS_PASSWORD / VOICEBOT_SSH_PASS: SSH password
"""
import io
import logging
import os
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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

if not HOST:
    print("Set VPS_HOST or VOICEBOT_HOST for VPS address.")
    sys.exit(1)
if not PASS:
    print("Set VPS_PASSWORD or VOICEBOT_SSH_PASS.")
    sys.exit(1)

def main() -> None:
    """
    Fetch and display recent OpenClaw logs from VPS.

    Connects to VPS via SSH and retrieves the last 100 lines from
    journalctl for the openclaw service, displaying the last 50.
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        logger.info(f"Connecting to {USER}@{HOST}:{PORT}")
        ssh.connect(HOST, PORT, USER, PASS, timeout=15)
        logger.info("SSH connection established")

        # Fetch last 100 lines
        stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 100 --no-pager 2>/dev/null')
        out = stdout.read().decode("utf-8", errors="replace")

        print("=== Recent logs (last 100 lines) ===")
        for line in out.splitlines()[-50:]:
            safe = line.encode("ascii", errors="replace").decode("ascii")[:150]
            print(safe)

        logger.info("Logs retrieved successfully")

    except paramiko.AuthenticationException as e:
        logger.error(f"SSH authentication failed: {e}")
        print(f"SSH authentication failed: {e}")
        sys.exit(1)
    except paramiko.SSHException as e:
        logger.error(f"SSH connection error: {e}")
        print(f"SSH connection error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error fetching logs: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        ssh.close()
        logger.info("SSH connection closed")


if __name__ == "__main__":
    main()
