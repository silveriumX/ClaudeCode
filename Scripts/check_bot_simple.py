"""
Проверка статуса Finance Bot (без эмодзи)
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import sys

# Фикс кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def check_status():
    """Проверить статус и логи бота"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        # Проверка что бот запущен
        print("=== Bot Status Check ===\n")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"Service status: {status}")

        if status != "active":
            print("\nWARNING: Bot is not active!")
        else:
            print("OK: Bot is running!")

        # Последние логи (только текст, без спецсимволов)
        print("\n=== Recent Logs ===")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 15 --no-pager | tail -15")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_status()
