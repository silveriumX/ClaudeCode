"""
Простой тест отмены заявки
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

def simple_cancel_test():
    """Простой тест отмены"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ТЕСТ ОТМЕНЫ ЗАЯВКИ")
        print("="*70 + "\n")

        test_script = """
cd /root/finance_bot
python3 << 'ENDPYTHON'
from sheets import SheetsManager
import config

sheets = SheetsManager()
user_id = '8127547204'

print('=== ДО ОТМЕНЫ ===')
created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
cancelled = sheets.get_requests_by_status(config.STATUS_CANCELLED, author_id=user_id)
print(f'Заявок CREATED: {len(created)}')
print(f'Заявок CANCELLED: {len(cancelled)}')

if len(created) > 0:
    req = created[0]
    print(f'\\nОтменяем заявку:')
    print(f'  ID: {req.get("request_id", "N/A")}')
    print(f'  Дата: {req.get("date", "N/A")}')
    print(f'  Сумма: {req.get("amount", "N/A")}')
    print(f'  Валюта: {req.get("currency", "N/A")}')

    success = sheets.update_request_status(
        req['date'],
        req['amount'],
        req['currency'],
        config.STATUS_CANCELLED
    )

    print(f'\\nРезультат: {"SUCCESS" if success else "FAILED"}')

    print('\\n=== ПОСЛЕ ОТМЕНЫ ===')
    created_after = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
    cancelled_after = sheets.get_requests_by_status(config.STATUS_CANCELLED, author_id=user_id)
    print(f'Заявок CREATED: {len(created_after)}')
    print(f'Заявок CANCELLED: {len(cancelled_after)}')
else:
    print('\\nНет заявок для отмены')
ENDPYTHON
"""

        stdin, stdout, stderr = ssh.exec_command(test_script)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)
        if error:
            print("\nОШИБКИ:")
            print(error)

        ssh.close()

        print("\n" + "="*70)
        print("ТЕПЕРЬ В ТЕЛЕГРАМ:")
        print("1. Откройте '📋 Мои заявки'")
        print("2. Список должен быть ПУСТОЙ!")
        print("="*70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_cancel_test()
