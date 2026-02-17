#!/usr/bin/env python3
"""
OpenClaw VPS Management Tool

Unified script for managing OpenClaw deployment on VPS.

Usage:
    python vps_connect.py status              - Check OpenClaw status
    python vps_connect.py logs [N]            - Show last N log lines (default 50)
    python vps_connect.py restart             - Restart OpenClaw service
    python vps_connect.py deploy              - Deploy OpenClaw to VPS
    python vps_connect.py shell <cmd>         - Execute shell command on VPS

Environment variables (from .env):
    VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
    ANTHROPIC_API_KEY, ZAI_API_KEY, TELEGRAM_BOT_TOKEN
"""
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# UTF-8 support for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import paramiko
except ImportError:
    print("Error: paramiko not installed")
    print("Install: pip install -r requirements.txt")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv not installed")
    print("Install: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vps_connect.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class VPSConnector:
    """SSH connection manager for OpenClaw VPS"""

    def __init__(self):
        # Load environment variables
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_path}")
        else:
            logger.warning(f".env file not found at {env_path}")

        # Get credentials (support both new and legacy variable names)
        self.host = os.getenv("VPS_HOST") or os.getenv("VOICEBOT_HOST")
        self.port = int(os.getenv("VPS_PORT", "22"))
        self.user = os.getenv("VPS_USER") or os.getenv("VOICEBOT_USER", "root")
        self.password = os.getenv("VPS_PASSWORD") or os.getenv("VOICEBOT_SSH_PASS")

        if not self.host or not self.password:
            logger.error("Missing VPS credentials")
            logger.error("Required: VPS_HOST, VPS_PASSWORD in .env file")
            sys.exit(1)

        logger.info(f"Connecting to VPS: {self.user}@{self.host}:{self.port}")
        self.ssh: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        """Establish SSH connection"""
        logger.info(f"Establishing SSH connection to {self.host}:{self.port}")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(
                self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                timeout=15
            )
            logger.info("SSH connection established successfully")
        except paramiko.AuthenticationException as e:
            logger.error(f"SSH authentication failed: {e}")
            sys.exit(1)
        except paramiko.SSHException as e:
            logger.error(f"SSH connection error: {e}")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"Unexpected error during SSH connection: {e}")
            sys.exit(1)

    def disconnect(self) -> None:
        """Close SSH connection"""
        if self.ssh:
            self.ssh.close()
            logger.info("SSH connection closed")

    def run(self, cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute command on VPS and return (exit_code, stdout, stderr)"""
        if not self.ssh:
            logger.error("SSH not connected. Call connect() first.")
            raise RuntimeError("Not connected. Call connect() first.")

        logger.debug(f"Executing command: {cmd}")
        stdin, stdout, stderr = self.ssh.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")

        if exit_code != 0:
            logger.warning(f"Command exited with code {exit_code}: {cmd}")

        return exit_code, out, err

    def status(self) -> None:
        """Check OpenClaw service status"""
        logger.info("Checking OpenClaw status")
        print("=== OpenClaw Status ===\n")

        # Service status
        code, out, err = self.run("systemctl is-active openclaw 2>&1")
        status = out.strip() if out else "unknown"
        print(f"Service: {status}")
        logger.info(f"Service status: {status}")

        # Process check
        code, out, err = self.run("pgrep -f 'openclaw|node.*gateway' | wc -l")
        processes = out.strip()
        print(f"Processes: {processes}")
        logger.info(f"Process count: {processes}")

        # Installation check
        code, out, err = self.run("test -f /usr/bin/openclaw && echo 'exists' || echo 'missing'")
        install_status = out.strip()
        print(f"Installation: {install_status}")
        logger.info(f"Installation status: {install_status}")

        # Config check
        code, out, err = self.run("test -f /root/.openclaw/openclaw.json && echo 'exists' || echo 'missing'")
        config_status = out.strip()
        print(f"Config: {config_status}")
        logger.info(f"Config status: {config_status}")

        # Version
        code, out, err = self.run("openclaw --version 2>&1")
        version = out.strip() if out else "N/A"
        print(f"Version: {version}")
        logger.info(f"OpenClaw version: {version}")

    def logs(self, lines: int = 50) -> None:
        """Show recent OpenClaw logs"""
        logger.info(f"Fetching last {lines} log lines")
        print(f"=== Last {lines} log lines ===\n")

        code, out, err = self.run(f"journalctl -u openclaw -n {lines} --no-pager 2>&1")
        if out:
            print(out)
        if err:
            logger.error(f"Error fetching logs: {err}")
            print(f"Error: {err}", file=sys.stderr)

    def restart(self) -> None:
        """Restart OpenClaw service"""
        logger.info("Restarting OpenClaw service")
        print("=== Restarting OpenClaw ===\n")

        code, out, err = self.run("systemctl restart openclaw 2>&1")
        if code == 0:
            print("✓ Service restarted")
            logger.info("Service restarted successfully")
        else:
            print(f"✗ Restart failed: {err}")
            logger.error(f"Restart failed: {err}")
            return

        # Wait and check status
        time.sleep(2)

        code, out, err = self.run("systemctl is-active openclaw 2>&1")
        status = out.strip()
        print(f"Status: {status}")
        logger.info(f"Post-restart status: {status}")

        # Show recent logs
        code, out, err = self.run("journalctl -u openclaw -n 10 --no-pager 2>&1")
        print("\nRecent logs:")
        print(out)

    def deploy(self) -> None:
        """Deploy OpenClaw to VPS (placeholder - implement based on needs)"""
        logger.warning("Deploy functionality called but not yet implemented")
        print("=== Deploy OpenClaw ===\n")
        print("Deploy functionality not yet implemented.")
        print("Use scripts in scripts/setup/ for installation.")

    def shell(self, cmd: str) -> None:
        """Execute arbitrary shell command"""
        logger.info(f"Executing shell command: {cmd}")
        print(f"=== Running: {cmd} ===\n")

        code, out, err = self.run(cmd, timeout=60)
        if out:
            print(out)
        if err:
            logger.warning(f"Command stderr: {err}")
            print(f"stderr: {err}", file=sys.stderr)

        if code != 0:
            logger.error(f"Command failed with exit code {code}")
            print(f"\nExit code: {code}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    logger.info(f"Starting vps_connect.py with command: {command}")

    vps = VPSConnector()
    vps.connect()

    try:
        if command == "status":
            vps.status()

        elif command == "logs":
            lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            vps.logs(lines)

        elif command == "restart":
            vps.restart()

        elif command == "deploy":
            vps.deploy()

        elif command == "shell":
            if len(sys.argv) < 3:
                logger.error("Shell command requires an argument")
                print("Error: shell command requires an argument")
                print("Usage: python vps_connect.py shell <command>")
                sys.exit(1)
            vps.shell(sys.argv[2])

        else:
            logger.error(f"Unknown command: {command}")
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)

        logger.info(f"Command '{command}' completed successfully")

    except Exception as e:
        logger.exception(f"Error executing command '{command}': {e}")
        raise
    finally:
        vps.disconnect()


if __name__ == "__main__":
    main()
