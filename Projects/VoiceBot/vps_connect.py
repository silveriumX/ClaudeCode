"""
VPS Connection Utility for VoiceBot
=====================================
python vps_connect.py status       # Статус бота
python vps_connect.py logs [N]     # Последние логи
python vps_connect.py errors [N]   # Ошибки
python vps_connect.py restart      # Перезапустить
python vps_connect.py deploy       # Загрузить файлы + перезапуск
python vps_connect.py shell <cmd>  # SSH команда
"""

import paramiko
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

LOCAL_DIR = Path(__file__).parent
load_dotenv(LOCAL_DIR / ".env")

VPS_HOST = os.environ["VPS_HOST"]
VPS_PORT = int(os.getenv("VPS_PORT", "22"))
VPS_USER = os.environ["VPS_USER"]
VPS_PASSWORD = os.environ["VPS_PASSWORD"]
REMOTE_DIR = os.getenv("VPS_REMOTE_DIR", "/root/voice_bot")
REMOTE_DIR_PUBLIC = os.getenv("VPS_REMOTE_DIR_PUBLIC", "/root/voice_bot_public")

CORE_FILES = [
    "bot.py",
    "bot_server.py",
    "requirements.txt",
]
PUBLIC_FILES = [
    "bot_public.py",
]


def get_connection() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
    return client


def run_ssh(command: str, print_output: bool = True) -> str:
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


def upload_file(local_name: str, remote_path: str) -> None:
    local_path = LOCAL_DIR / local_name
    if not local_path.exists():
        print(f"  Skip (not found): {local_name}")
        return
    client = get_connection()
    try:
        sftp = client.open_sftp()
        sftp.put(str(local_path), remote_path)
        sftp.close()
        print(f"  Uploaded: {local_name} -> {remote_path}")
    finally:
        client.close()


def bot_status():
    print("=== VoiceBot Processes ===")
    run_ssh("ps aux | grep -E 'voice_bot.*bot' | grep -v grep || echo 'Not running'")
    print("\n=== Uptime / RAM / Disk ===")
    run_ssh("uptime && free -h | head -2 && df -h / | tail -1")


def bot_logs(lines: int = 30):
    run_ssh(f"tail -{lines} {REMOTE_DIR}/bot.log 2>/dev/null || echo 'no log'")


def bot_errors(lines: int = 20):
    run_ssh(f"tail -{lines} {REMOTE_DIR}/bot_error.log 2>/dev/null || echo 'no errors'")


def bot_restart():
    print("=== Stopping ===")
    run_ssh("pkill -f 'voice_bot/bot' 2>/dev/null; pkill -f 'voice_bot_public/bot' 2>/dev/null; sleep 2")
    print("=== Starting voice_bot ===")
    run_ssh(
        f"cd {REMOTE_DIR} && "
        f"source venv/bin/activate 2>/dev/null; "
        f"nohup {REMOTE_DIR}/venv/bin/python3 {REMOTE_DIR}/bot_server.py >> bot.log 2>> bot_error.log </dev/null &"
    )
    print("=== Starting voice_bot_public ===")
    run_ssh(
        f"cd {REMOTE_DIR_PUBLIC} && "
        f"nohup {REMOTE_DIR}/venv/bin/python3 {REMOTE_DIR_PUBLIC}/bot.py >> bot.log 2>> bot_error.log </dev/null & "
        f"sleep 2 && ps aux | grep -E 'voice_bot.*bot' | grep -v grep && echo 'Started OK' || echo 'FAILED'"
    )


def bot_deploy():
    print("=== Deploying voice_bot ===")
    for f in CORE_FILES:
        upload_file(f, f"{REMOTE_DIR}/{f}")
    print("=== Deploying voice_bot_public ===")
    for f in PUBLIC_FILES:
        upload_file(f, f"{REMOTE_DIR_PUBLIC}/{f.replace('bot_public.py', 'bot.py')}")
    print("\n=== Dependencies ===")
    run_ssh(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/pip install -r requirements.txt --quiet")
    bot_restart()
    print("\n=== Done ===")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower()
    if cmd == "status":
        bot_status()
    elif cmd == "logs":
        bot_logs(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
    elif cmd == "errors":
        bot_errors(int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    elif cmd == "restart":
        bot_restart()
    elif cmd == "deploy":
        bot_deploy()
    elif cmd == "shell":
        run_ssh(" ".join(sys.argv[2:])) if len(sys.argv) > 2 else print("Usage: python vps_connect.py shell <cmd>")
    else:
        print(f"Unknown: {cmd}\nAvailable: status, logs, errors, restart, deploy, shell")


if __name__ == "__main__":
    main()
