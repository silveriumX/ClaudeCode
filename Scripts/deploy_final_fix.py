"""
Деплой финального исправления
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

def deploy_final_fix():
    """Загрузить финальное исправление"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДЕПЛОЙ ФИНАЛЬНОГО ИСПРАВЛЕНИЯ")
        print("="*70 + "\n")

        # Загружаем файлы через SFTP
        sftp = ssh.open_sftp()

        files = [
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\sheets.py", "/root/finance_bot/sheets.py"),
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\handlers\request.py", "/root/finance_bot/handlers/request.py")
        ]

        for local, remote in files:
            print(f"Загрузка {local.split('\\')[-1]}...")
            sftp.put(local, remote)
            print(f"  ✓ {remote}\n")

        sftp.close()

        # Перезапускаем бота
        print("Перезапуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot && sleep 2 && systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"Статус: {status}\n")

        ssh.close()

        print("="*70)
        print("ДЕПЛОЙ ЗАВЕРШЁН!")
        print("="*70)
        print("""
ПРОВЕРКА:
1. python Scripts\\test_final_cancel.py  (отменит заявку через скрипт)
2. Откройте "📋 Мои заявки" в Telegram
3. Список должен быть ПУСТЫМ!
        """)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_final_fix()
