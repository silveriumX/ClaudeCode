#!/usr/bin/env python3
"""
Watch OpenClaw logs in real-time (last 20 lines every 2 sec).

Environment variables (supports both VPS_* and VOICEBOT_* prefixes):
- VPS_HOST / VOICEBOT_HOST: VPS IP or hostname
- VPS_USER / VOICEBOT_USER: SSH username (default: root)
- VPS_PASSWORD / VOICEBOT_SSH_PASS: SSH password
"""
import io
import logging
import os
import sys
import time

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
    Watch OpenClaw logs in real-time.

    Connects to VPS via SSH and polls journalctl every 2 seconds,
    displaying the last 10 lines of the most recent 20 log entries.
    Runs for 30 iterations (1 minute) or until interrupted.
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        logger.info(f"Connecting to {USER}@{HOST}:{PORT}")
        ssh.connect(HOST, PORT, USER, PASS, timeout=15)
        logger.info("SSH connection established")

        print("=== Watching OpenClaw logs (press Ctrl+C to stop) ===")
        print("Now send /start to @cosmicprincesskaguyabot")
        print()

        for i in range(30):  # 1 minute
            stdin, stdout, stderr = ssh.exec_command('journalctl -u openclaw -n 20 --no-pager')
            out = stdout.read().decode("utf-8", errors="replace")
            lines = [l.encode("ascii", errors="replace").decode("ascii")[:150] for l in out.splitlines()[-10:]]
            print(f"\n--- Refresh {i+1} ---")
            for line in lines:
                print(line)
            time.sleep(2)

        logger.info("Watch cycle completed")

    except KeyboardInterrupt:
        print("\nStopped")
        logger.info("Watch interrupted by user")
    except paramiko.AuthenticationException as e:
        logger.error(f"SSH authentication failed: {e}")
        print(f"SSH authentication failed: {e}")
        sys.exit(1)
    except paramiko.SSHException as e:
        logger.error(f"SSH connection error: {e}")
        print(f"SSH connection error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error during watch: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        ssh.close()
        logger.info("SSH connection closed")


if __name__ == "__main__":
    main()
