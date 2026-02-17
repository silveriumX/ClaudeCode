"""
VPS Connection Utility for FinanceBot
======================================
Единый модуль для подключения к Linux VPS через SSH (paramiko).

Использование:
    python vps_connect.py status       # Статус бота и systemd
    python vps_connect.py logs [N]     # Последние N строк journalctl
    python vps_connect.py errors [N]   # Только ошибки
    python vps_connect.py restart      # Перезапуск через systemd
    python vps_connect.py deploy       # Загрузить src/ и перезапустить
    python vps_connect.py shell <cmd>  # Произвольная SSH команда
"""

import paramiko
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

LOCAL_DIR = Path(__file__).parent
load_dotenv(LOCAL_DIR / ".env")

# ─── VPS Configuration (from .env) ──────────────────────────────
VPS_HOST = os.environ["VPS_HOST"]
VPS_PORT = int(os.getenv("VPS_PORT", "22"))
VPS_USER = os.environ["VPS_USER"]
VPS_PASSWORD = os.environ["VPS_PASSWORD"]
REMOTE_DIR = os.getenv("VPS_REMOTE_DIR", "/root/finance_bot")
SERVICE_NAME = "finance_bot"

# Файлы ядра бота (для деплоя)
CORE_FILES = [
    "src/bot.py",
    "src/config.py",
    "src/sheets.py",
    "src/drive_manager.py",
    "src/__init__.py",
    "src/handlers/__init__.py",
    "src/handlers/start.py",
    "src/handlers/menu.py",
    "src/handlers/request.py",
    "src/handlers/payment.py",
    "src/handlers/edit_handlers.py",
    "src/handlers/fact_expense.py",
    "src/utils/__init__.py",
    "src/utils/auth.py",
    "src/utils/categories.py",
    "src/utils/formatters.py",
    "requirements.txt",
]


# ─── Connection ──────────────────────────────────────────────────

def get_connection() -> paramiko.SSHClient:
    """Создаёт и возвращает SSH-подключение."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        VPS_HOST,
        port=VPS_PORT,
        username=VPS_USER,
        password=VPS_PASSWORD,
        timeout=15,
    )
    return client


def run_ssh(command: str, print_output: bool = True) -> str:
    """Выполняет команду на VPS, возвращает stdout."""
    client = get_connection()
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if print_output:
            if out:
                print(out.encode("ascii", errors="replace").decode())
            if err:
                print(f"[stderr] {err.encode('ascii', errors='replace').decode()}")
        return out
    finally:
        client.close()


def upload_file(local_name: str, remote_path: str | None = None) -> None:
    """Загружает файл на VPS через SFTP."""
    local_path = LOCAL_DIR / local_name
    if not local_path.exists():
        print(f"  Skip (not found): {local_name}")
        return

    if remote_path is None:
        remote_path = f"{REMOTE_DIR}/{local_name}"

    client = get_connection()
    try:
        sftp = client.open_sftp()
        # Создаём директории если нужно
        parts = remote_path.rsplit("/", 1)
        if len(parts) == 2:
            try:
                sftp.stat(parts[0])
            except FileNotFoundError:
                run_ssh(f"mkdir -p {parts[0]}", print_output=False)
        sftp.put(str(local_path), remote_path)
        sftp.close()
        print(f"  Uploaded: {local_name}")
    finally:
        client.close()


# ─── Bot Management (systemd) ───────────────────────────────────

def bot_status():
    """Показывает статус бота на VPS."""
    print("=== Service Status ===")
    run_ssh(f"systemctl status {SERVICE_NAME} --no-pager -l 2>/dev/null | head -15 || echo 'No systemd service'")
    print("\n=== Process ===")
    run_ssh("ps aux | grep 'finance_bot' | grep -v grep || echo 'Not running'")
    print("\n=== Uptime / RAM / Disk ===")
    run_ssh("uptime && free -h | head -2 && df -h / | tail -1")


def bot_logs(lines: int = 50):
    """Последние строки journalctl."""
    print(f"=== Last {lines} log lines ===")
    run_ssh(f"journalctl -u {SERVICE_NAME} --no-pager -n {lines} 2>/dev/null || tail -{lines} {REMOTE_DIR}/bot.log 2>/dev/null || echo 'no logs'")


def bot_errors(lines: int = 30):
    """Только ошибки."""
    print(f"=== Last {lines} errors ===")
    run_ssh(f"journalctl -u {SERVICE_NAME} --no-pager -p err -n {lines} 2>/dev/null || tail -{lines} {REMOTE_DIR}/bot_error.log 2>/dev/null || echo 'no errors'")


def bot_restart():
    """Перезапускает бота через systemd."""
    print("=== Restarting ===")
    run_ssh(f"systemctl restart {SERVICE_NAME} && sleep 2 && systemctl is-active {SERVICE_NAME}")


def bot_deploy():
    """Загружает все файлы ядра и перезапускает бота."""
    print("=== Deploying core files ===")
    for f in CORE_FILES:
        upload_file(f)

    print("\n=== Installing dependencies ===")
    run_ssh(f"cd {REMOTE_DIR} && pip3 install -r requirements.txt --quiet 2>&1 | tail -3")

    bot_restart()
    print("\n=== Deploy complete ===")


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "status":
        bot_status()
    elif cmd == "logs":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        bot_logs(lines)
    elif cmd == "errors":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        bot_errors(lines)
    elif cmd == "restart":
        bot_restart()
    elif cmd == "deploy":
        bot_deploy()
    elif cmd == "shell":
        if len(sys.argv) > 2:
            run_ssh(" ".join(sys.argv[2:]))
        else:
            print("Usage: python vps_connect.py shell <command>")
    else:
        print(f"Unknown command: {cmd}")
        print("Available: status, logs, errors, restart, deploy, shell")


if __name__ == "__main__":
    main()
