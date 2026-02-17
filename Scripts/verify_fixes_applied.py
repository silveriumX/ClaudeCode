"""
Проверка что исправления применились на сервере
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

def verify_fixes():
    """Проверить что исправления применились"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА ПРИМЕНЕНИЯ ИСПРАВЛЕНИЙ ===\n")

        # 1. Проверяем callback_data в my_requests
        print("1. Проверка формата callback в my_requests():\n")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'callback_data=f\"view_req_' /root/finance_bot/handlers/request.py | head -5")
        callbacks = stdout.read().decode('utf-8', errors='replace')
        print(callbacks)

        # 2. Проверяем view_request_callback
        print("\n2. Проверка view_request_callback():\n")
        stdin, stdout, stderr = ssh.exec_command("grep -A 10 'def view_request_callback' /root/finance_bot/handlers/request.py | head -15")
        view_req = stdout.read().decode('utf-8', errors='replace')
        print(view_req)

        # 3. Проверяем что бот использует request_id
        print("\n3. Поиск использования request_id:\n")
        stdin, stdout, stderr = ssh.exec_command("grep -n \"request\\['request_id'\\]\" /root/finance_bot/handlers/request.py")
        request_id_usage = stdout.read().decode('utf-8', errors='replace')
        print(request_id_usage if request_id_usage.strip() else "   НЕ НАЙДЕНО!")

        # 4. Последние логи с момента перезапуска
        print("\n4. Логи с момента перезапуска (после 23:28):\n")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot --since '23:28' --no-pager | tail -30")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        # 5. Проверка процесса
        print("\n5. Процесс бота:\n")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '/root/finance_bot/bot.py' | grep -v grep")
        process = stdout.read().decode('utf-8', errors='replace')
        print(process if process.strip() else "   Процесс не найден!")

        # 6. Проверка модификации файла
        print("\n6. Время модификации handlers/request.py:\n")
        stdin, stdout, stderr = ssh.exec_command("stat /root/finance_bot/handlers/request.py | grep Modify")
        mod_time = stdout.read().decode('utf-8', errors='replace')
        print(mod_time)

        ssh.close()

        print("\n" + "="*70)
        print("РЕКОМЕНДАЦИЯ:")
        print("Если callback_data всё ещё содержит date/amount/currency,")
        print("значит файл не обновился. Нужно проверить sftp загрузку.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_fixes()
