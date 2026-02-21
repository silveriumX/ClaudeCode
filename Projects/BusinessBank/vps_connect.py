"""
VPS Connection Utility for BusinessBank WB Bot
================================================
python vps_connect.py status       # Статус бота
python vps_connect.py logs [N]     # Последние N строк логов (default 50)
python vps_connect.py errors       # Только строки с ERROR/Exception
python vps_connect.py restart      # Перезапустить бота
python vps_connect.py deploy       # Загрузить файлы + перезапуск
python vps_connect.py shell <cmd>  # Произвольная SSH команда
"""

import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

LOCAL_DIR = Path(__file__).parent
load_dotenv(LOCAL_DIR / ".env")

# VPS-креды берём из VoiceTaskBot/.env (общий VPS)
_vvps_env = LOCAL_DIR.parent / "VoiceTaskBot" / ".env"
load_dotenv(_vvps_env, override=False)

VPS_HOST     = os.environ["VPS_HOST"]
VPS_PORT     = int(os.getenv("VPS_PORT", "22"))
VPS_USER     = os.environ["VPS_USER"]
VPS_PASSWORD = os.environ["VPS_PASSWORD"]
REMOTE_DIR   = "/root/wb_bot"

# Корневые файлы для деплоя
DEPLOY_FILES = [
    "bot.py",
    "requirements.txt",
]

# Все .py файлы из src/ (без __pycache__)
SRC_DIR = LOCAL_DIR / "src"
SRC_FILES = sorted(SRC_DIR.glob("*.py"))

# service_account.json — из FinanceBot (рядом лежит)
SA_LOCAL = LOCAL_DIR.parent / "FinanceBot" / "service_account.json"


def get_connection() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
    return client


def run_ssh(command: str, timeout: int = 30) -> str:
    client = get_connection()
    try:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if out:
            print(out)
        if err:
            print(f"[stderr] {err}")
        return out
    finally:
        client.close()


def upload_files() -> None:
    run_ssh(f"mkdir -p {REMOTE_DIR}/src")

    client = get_connection()
    sftp = client.open_sftp()
    try:
        # Корневые файлы
        for filename in DEPLOY_FILES:
            local_path = LOCAL_DIR / filename
            if local_path.exists():
                print(f"  Uploading {filename}...")
                sftp.put(str(local_path), f"{REMOTE_DIR}/{filename}")
            else:
                print(f"  [WARN] not found: {filename}")

        # src/*.py
        for src_file in SRC_FILES:
            print(f"  Uploading src/{src_file.name}...")
            sftp.put(str(src_file), f"{REMOTE_DIR}/src/{src_file.name}")

        # service_account.json
        if SA_LOCAL.exists():
            print("  Uploading service_account.json...")
            sftp.put(str(SA_LOCAL), f"{REMOTE_DIR}/service_account.json")
        else:
            print(f"  [WARN] service_account.json not found at {SA_LOCAL}")

        # .env для VPS (SA_PATH указывает на локальный путь в REMOTE_DIR)
        env_content = _build_vps_env()
        with sftp.open(f"{REMOTE_DIR}/.env", "w") as f:
            f.write(env_content)
        print("  Uploading .env (VPS version)...")

    finally:
        sftp.close()
        client.close()


def _build_vps_env() -> str:
    """Собрать .env для VPS — SA_PATH заменяем на локальный путь сервера."""
    load_dotenv(LOCAL_DIR / ".env")
    lines = [
        f"BOT_TOKEN={os.getenv('BOT_TOKEN', '')}",
        f"WB_SHEETS_ID={os.getenv('WB_SHEETS_ID', '')}",
        f"SA_PATH=service_account.json",  # на VPS рядом с bot.py
        f"BOT_ALLOWED_IDS={os.getenv('BOT_ALLOWED_IDS', '')}",
    ]
    return "\n".join(lines) + "\n"


def cmd_status() -> None:
    print("=== WB Bot Status ===")
    run_ssh(f"ps aux | grep -E '[b]ot.py' | grep wb_bot | head -5")
    print()
    run_ssh(f"ls -la {REMOTE_DIR}/ 2>/dev/null | head -20")


def cmd_logs(n: int = 50) -> None:
    run_ssh(f"tail -n {n} {REMOTE_DIR}/bot.log 2>/dev/null || echo 'No logs found'")


def cmd_errors() -> None:
    run_ssh(f"grep -E 'ERROR|Exception|Traceback' {REMOTE_DIR}/bot.log 2>/dev/null | tail -30")


def _kill_bot() -> None:
    kill_cmd = (
        f"if [ -f {REMOTE_DIR}/bot.pid ]; then "
        f"  kill -9 $(cat {REMOTE_DIR}/bot.pid) 2>/dev/null; fi; "
        f"kill -9 $(for f in /proc/*/cwd; do "
        f"  [ \"$(readlink $f 2>/dev/null)\" = \"{REMOTE_DIR}\" ] && "
        f"  basename $(dirname $f); "
        f"done) 2>/dev/null; "
        f"rm -f {REMOTE_DIR}/bot.pid; "
        f"sleep 1; echo 'killed'"
    )
    run_ssh(kill_cmd)


def cmd_restart() -> None:
    import time

    print("Restarting WB Bot...")
    _kill_bot()

    python_bin = f"{REMOTE_DIR}/venv/bin/python"
    client = get_connection()
    try:
        start_cmd = (
            f"cd {REMOTE_DIR}; "
            f"nohup {python_bin} -X utf8 bot.py >> bot.log 2>&1 & "
            f"echo $! > bot.pid"
        )
        _, stdout, _ = client.exec_command(start_cmd, timeout=5)
        try:
            stdout.read(64)
        except Exception:
            pass
    finally:
        client.close()

    time.sleep(3)
    pid_check = run_ssh(f"cat {REMOTE_DIR}/bot.pid 2>/dev/null")
    if pid_check:
        run_ssh(f"ps -p {pid_check} -o pid,stat,cmd --no-headers 2>/dev/null || echo 'process not found'")
        print(f"  PID {pid_check} running.")
    else:
        print("  WARNING: bot.pid not found — check bot.log")
    print("Bot restarted.")


def cmd_deploy() -> None:
    print("=== Deploying WB Bot ===")

    print("\n1. Uploading files...")
    upload_files()

    print("\n2. Installing dependencies...")
    run_ssh(
        f"cd {REMOTE_DIR} && "
        f"python3 -m venv venv 2>/dev/null; "
        f"source venv/bin/activate && "
        f"pip install -q -r requirements.txt",
        timeout=180,
    )

    print("\n3. Restarting bot...")
    cmd_restart()

    print("\nDeploy complete!")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "status":
        cmd_status()
    elif cmd == "logs":
        n = int(args[1]) if len(args) > 1 else 50
        cmd_logs(n)
    elif cmd == "errors":
        cmd_errors()
    elif cmd == "restart":
        cmd_restart()
    elif cmd == "deploy":
        cmd_deploy()
    elif cmd == "shell":
        if len(args) < 2:
            print("Usage: vps_connect.py shell <command>")
        else:
            run_ssh(" ".join(args[1:]))
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
