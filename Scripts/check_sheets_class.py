"""
Проверка класса GoogleSheets
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

def check_sheets_class():
    """Проверить имя класса в sheets.py"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА SHEETS.PY ===\n")

        # Ищем определение класса
        print("1. Поиск класса:\n")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'class ' /root/finance_bot/sheets.py | head -5")
        classes = stdout.read().decode('utf-8', errors='replace')
        print(classes if classes.strip() else "   Классы не найдены\n")

        # Ищем функцию get_requests_by_status
        print("\n2. Проверка функции get_requests_by_status:\n")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'def get_requests_by_status' /root/finance_bot/sheets.py")
        func = stdout.read().decode('utf-8', errors='replace')
        print(func if func.strip() else "   Функция не найдена\n")

        # Смотрим первые 50 строк sheets.py
        print("\n3. Первые 50 строк sheets.py:\n")
        stdin, stdout, stderr = ssh.exec_command("head -50 /root/finance_bot/sheets.py")
        head = stdout.read().decode('utf-8', errors='replace')
        print(head)

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_sheets_class()
