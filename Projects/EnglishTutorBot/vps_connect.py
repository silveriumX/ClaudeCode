"""
VPS Connection Utility for EnglishTutorBot
==========================================
Единый модуль для подключения к Linux VPS через SSH (paramiko).

Использование:
    # Как модуль
    from vps_connect import run_ssh, upload_file, download_file, get_connection

    output = run_ssh("ps aux | grep python")
    upload_file("bot.py", "/root/english_tutor_bot/bot.py")

    # Как скрипт
    python vps_connect.py status       # Статус бота
    python vps_connect.py logs         # Последние логи
    python vps_connect.py errors       # Ошибки
    python vps_connect.py restart      # Перезапустить бота
    python vps_connect.py deploy       # Загрузить все файлы и перезапустить
    python vps_connect.py shell        # Интерактивная команда
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
REMOTE_DIR = os.getenv("VPS_REMOTE_DIR", "/root/english_tutor_bot")

# Файлы ядра бота (для деплоя)
CORE_FILES = [
    "bot.py",
    "user_profile.py",
    "session_manager.py",
    "intent_detector.py",
    "prompts.py",
    "web_search.py",
    "requirements.txt",
    # .env already on server, don't overwrite
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
                print(out)
            if err:
                print(f"[stderr] {err}")
        return out
    finally:
        client.close()


def upload_file(local_name: str, remote_path: str | None = None) -> None:
    """Загружает файл на VPS через SFTP."""
    local_path = LOCAL_DIR / local_name
    if not local_path.exists():
        print(f"File not found: {local_path}")
        return

    if remote_path is None:
        remote_path = f"{REMOTE_DIR}/{local_name}"

    client = get_connection()
    try:
        sftp = client.open_sftp()
        sftp.put(str(local_path), remote_path)
        sftp.close()
        print(f"Uploaded: {local_name} -> {remote_path}")
    finally:
        client.close()


def download_file(remote_name: str, local_path: str | None = None) -> None:
    """Скачивает файл с VPS через SFTP."""
    remote_path = f"{REMOTE_DIR}/{remote_name}"
    if local_path is None:
        local_path = str(LOCAL_DIR / f"downloaded_{remote_name}")

    client = get_connection()
    try:
        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        print(f"Downloaded: {remote_path} -> {local_path}")
    finally:
        client.close()


# ─── Bot Management ─────────────────────────────────────────────

def bot_status():
    """Показывает статус бота на VPS."""
    print("=== Bot Status ===")
    run_ssh("ps aux | grep 'python3 bot.py' | grep -v grep || echo 'Bot is NOT running'")
    print("\n=== Uptime ===")
    run_ssh("uptime")
    print("\n=== Disk ===")
    run_ssh("df -h / | tail -1")
    print("\n=== RAM ===")
    run_ssh("free -h | head -2")


def bot_logs(lines: int = 30):
    """Последние строки лога."""
    print(f"=== Last {lines} log lines ===")
    run_ssh(f"tail -{lines} {REMOTE_DIR}/bot.log 2>/dev/null || echo 'no log'")


def bot_errors(lines: int = 20):
    """Последние ошибки."""
    print(f"=== Last {lines} error lines ===")
    run_ssh(f"tail -{lines} {REMOTE_DIR}/bot_error.log 2>/dev/null || echo 'no errors'")


def bot_restart():
    """Останавливает и перезапускает бота через nohup."""
    print("=== Stopping bot ===")
    run_ssh("pkill -f 'python3 bot.py' 2>/dev/null; sleep 2; "
            "ps aux | grep 'python3 bot.py' | grep -v grep && echo 'WARN: still running' || echo 'Stopped'")

    print("\n=== Starting bot ===")
    run_ssh(
        f"cd {REMOTE_DIR} && "
        f"nohup python3 bot.py >> bot.log 2>> bot_error.log </dev/null & "
        f"sleep 2 && ps aux | grep 'python3 bot.py' | grep -v grep && echo 'Started OK' || echo 'FAILED to start'"
    )


def bot_deploy():
    """Загружает все файлы ядра и перезапускает бота."""
    print("=== Deploying core files ===")
    for f in CORE_FILES:
        if (LOCAL_DIR / f).exists():
            upload_file(f)
        else:
            print(f"  Skip (not found): {f}")

    print("\n=== Installing dependencies ===")
    run_ssh(f"cd {REMOTE_DIR} && pip3 install -r requirements.txt --quiet")

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
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        bot_logs(lines)
    elif cmd == "errors":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
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
