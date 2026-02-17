"""
Проверка логов после открытия Мои заявки
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

def check_my_requests_logs():
    """Проверить логи"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("\n" + "="*70)
        print("ЛОГИ ПОСЛЕ ОТКРЫТИЯ 'МОИ ЗАЯВКИ'")
        print("="*70 + "\n")

        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u finance_bot -n 20 --no-pager | grep -E 'DEBUG_MY_REQUESTS|get_requests_by_status'"
        )
        logs = stdout.read().decode('utf-8', errors='replace')

        if logs.strip():
            print(logs)
        else:
            print("DEBUG логи не найдены. Показываем последние 20 строк:")
            stdin, stdout, stderr = ssh.exec_command(
                "journalctl -u finance_bot -n 20 --no-pager | grep -v getUpdates"
            )
            logs = stdout.read().decode('utf-8', errors='replace')
            print(logs)

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_my_requests_logs()
