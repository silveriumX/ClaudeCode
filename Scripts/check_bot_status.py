"""
Проверка статуса Finance Bot после деплоя
"""
import os
from pathlib import Path

from dotenv import load_dotenv
import paramiko

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def check_status():
    """Проверить статус и логи бота"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        # Статус
        print("=== STATUS ===")
        stdin, stdout, stderr = ssh.exec_command("systemctl status finance_bot --no-pager")
        print(stdout.read().decode())

        # Последние логи
        print("\n=== LOGS (last 20 lines) ===")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 20 --no-pager")
        print(stdout.read().decode())

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_status()
