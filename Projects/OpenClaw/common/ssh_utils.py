"""
SSH Utilities for OpenClaw VPS Management

Common SSH operations shared across multiple scripts.
"""
import logging
from typing import Tuple

import paramiko

logger = logging.getLogger(__name__)


def run_ssh_command(
    ssh: paramiko.SSHClient,
    cmd: str,
    timeout: int = 30
) -> Tuple[int, str, str]:
    """
    Execute command on VPS via SSH.

    Args:
        ssh: Active paramiko SSHClient connection
        cmd: Shell command to execute
        timeout: Command timeout in seconds (default 30)

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Raises:
        paramiko.SSHException: If SSH command execution fails
    """
    logger.debug(f"Executing SSH command: {cmd}")

    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")

    if exit_code != 0:
        logger.warning(f"Command exited with code {exit_code}: {cmd}")

    return exit_code, out, err
