"""
Финальный тест с правильным user_id
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

def final_test():
    """Финальный тест"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ФИНАЛЬНЫЙ ТЕСТ")
        print("="*70 + "\n")

        test_script = """
cd /root/finance_bot
python3 -c "
from sheets import SheetsManager
import config

sheets = SheetsManager()
user_id = '8127547204'

print('=== ЗАЯВКИ СО СТАТУСОМ CREATED ===')
created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
print(f'Найдено: {len(created)} заявок')
for r in created:
    print(f'  ID: {r[\"request_id\"]}')
    print(f'  Дата: {r[\"date\"]}')
    print(f'  Сумма: {r[\"amount\"]} ₽')
    print(f'  Статус: {r[\"status\"]}')
    print(f'  Author ID: {r[\"author_id\"]}')
    print()

print('=== ТЕСТ ОТМЕНЫ ЗАЯВКИ ===')
if len(created) > 0:
    req = created[0]
    print(f'Отменяем заявку: {req[\"request_id\"]}')
    print(f'  Дата: {req[\"date\"]}')
    print(f'  Сумма: {req[\"amount\"]}')
    print(f'  Валюта: {req[\"currency\"]}')

    success = sheets.update_request_status(
        req['date'],
        req['amount'],
        req['currency'],
        config.STATUS_CANCELLED
    )

    print(f'\\nРезультат: {\"SUCCESS\" if success else \"FAILED\"}')

    if success:
        print('\\nПроверка после отмены:')
        updated_req = sheets.get_request_by_request_id(req['request_id'])
        if updated_req:
            print(f'  Новый статус: {updated_req[\"status\"]}')

        # Проверяем список
        created_after = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
        cancelled_after = sheets.get_requests_by_status(config.STATUS_CANCELLED, author_id=user_id)
        print(f'\\nЗаявок CREATED: {len(created_after)}')
        print(f'Заявок CANCELLED: {len(cancelled_after)}')
else:
    print('Нет заявок для отмены')
"
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
        print("ТЕПЕРЬ ПРОВЕРЬТЕ В ТЕЛЕГРАМ:")
        print("1. Откройте '📋 Мои заявки'")
        print("2. Список должен быть ПУСТОЙ (обе заявки отменены)")
        print("="*70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_test()
