"""
Мониторинг логов в реальном времени
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import sys
import time

# Фикс кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def monitor_logs():
    """Мониторинг логов"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== МОНИТОРИНГ ЛОГОВ В РЕАЛЬНОМ ВРЕМЕНИ ===\n")
        print("Команда для мониторинга на сервере:")
        print("  journalctl -u finance_bot -f --no-pager\n")
        print("Последние 20 строк логов:\n")

        # Последние логи
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 20 --no-pager | grep -v 'getUpdates'")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        print("\n" + "="*70)
        print("ЧТО НУЖНО ПРОВЕРИТЬ:")
        print("1. Откройте 'Мои заявки' в Telegram")
        print("2. Нажмите на кнопку заявки")
        print("3. После этого выполните команду для просмотра логов:")
        print("\n   python Scripts\\get_recent_logs.py\n")

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    monitor_logs()
