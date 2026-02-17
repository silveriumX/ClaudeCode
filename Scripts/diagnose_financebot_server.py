"""
Диагностика Finance Bot на сервере
Проверка кодировок и файлов
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
VPS_PATH = "/root/finance_bot"

def execute_command(ssh, command, description=""):
    """Выполнить команду на сервере"""
    if description:
        print(f"\n{'='*60}")
        print(f"{description}")
        print('='*60)
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='replace')
    error = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()

    if output:
        print(output)
    if error and exit_code != 0:
        print(f"ERROR: {error}")

    return output, error, exit_code

def diagnose():
    """Диагностика сервера"""
    try:
        print("=== Connecting to VPS ===")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)
        print(f"Connected to {VPS_HOST}")

        # 1. Проверка статуса бота
        execute_command(ssh,
            "systemctl status finance_bot --no-pager -l",
            "1. Bot Service Status")

        # 2. Список файлов проекта
        execute_command(ssh,
            f"ls -lah {VPS_PATH}",
            "2. Project Files")

        # 3. Проверка кодировки файлов Python
        execute_command(ssh,
            f"file {VPS_PATH}/*.py",
            "3. File Encodings Check")

        # 4. Проверка sheets.py на дубликаты методов
        execute_command(ssh,
            f"grep -n 'def get_requests_by_status' {VPS_PATH}/sheets.py",
            "4. Check for duplicate methods in sheets.py")

        # 5. Проверка handlers/menu.py на кодировку
        execute_command(ssh,
            f"file {VPS_PATH}/handlers/menu.py",
            "5. Menu handler encoding")

        # 6. Проверка эмодзи в menu.py
        execute_command(ssh,
            f"grep -n 'Мои заявки' {VPS_PATH}/handlers/menu.py | head -5",
            "6. Check 'Moi zayavki' button in menu.py")

        # 7. Последние 30 строк логов
        execute_command(ssh,
            "journalctl -u finance_bot -n 30 --no-pager",
            "7. Recent Logs (last 30 lines)")

        # 8. Проверка что бот активен
        output, _, _ = execute_command(ssh,
            "systemctl is-active finance_bot",
            "8. Bot Active Status")

        if "active" in output:
            print("\nOK: Bot is running")
        else:
            print("\nWARNING: Bot may not be running properly")

        # 9. Проверка Python версии
        execute_command(ssh,
            "python3 --version",
            "9. Python Version")

        # 10. Проверка locale на сервере
        execute_command(ssh,
            "locale",
            "10. Server Locale Settings")

        ssh.close()
        print("\n" + "="*60)
        print("DIAGNOSIS COMPLETE")
        print("="*60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()
