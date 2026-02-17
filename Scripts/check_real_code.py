"""
Проверка РЕАЛЬНОГО callback_data в коде на сервере
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

def check_real_code():
    """Проверить реальный код callback_data"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА РЕАЛЬНОГО КОДА НА СЕРВЕРЕ ===\n")

        # Показываем строки 368-384 (создание кнопок в my_requests)
        print("1. Код создания кнопок в my_requests() (строки 368-384):\n")
        stdin, stdout, stderr = ssh.exec_command("sed -n '368,384p' /root/finance_bot/handlers/request.py")
        code1 = stdout.read().decode('utf-8', errors='replace')
        print(code1)

        # Показываем строки 472-487 (создание кнопок в navigation)
        print("\n2. Код создания кнопок в my_requests_navigation_callback() (строки 472-487):\n")
        stdin, stdout, stderr = ssh.exec_command("sed -n '472,487p' /root/finance_bot/handlers/request.py")
        code2 = stdout.read().decode('utf-8', errors='replace')
        print(code2)

        # MD5 сумма файла для проверки что он обновился
        print("\n3. MD5 сумма файла:\n")
        stdin, stdout, stderr = ssh.exec_command("md5sum /root/finance_bot/handlers/request.py")
        md5 = stdout.read().decode('utf-8', errors='replace')
        print(f"   {md5}")

        # Сравниваем с локальным файлом
        print("\n4. MD5 сумма локального файла:\n")
        import hashlib
        local_file = r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\handlers\request.py"
        with open(local_file, 'rb') as f:
            local_md5 = hashlib.md5(f.read()).hexdigest()
        print(f"   {local_md5}\n")

        server_md5 = md5.split()[0] if md5 else ""

        if server_md5 == local_md5:
            print("   ✓ MD5 совпадают - файлы идентичны")
        else:
            print("   ✗ MD5 НЕ совпадают - файлы РАЗНЫЕ!")
            print("   Возможно файл не загрузился или был изменён")

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_real_code()
