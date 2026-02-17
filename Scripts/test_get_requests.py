"""
Тест реального вызова get_requests_by_status
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

def test_get_requests():
    """Тест функции get_requests_by_status"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ТЕСТ ФУНКЦИИ get_requests_by_status")
        print("="*70 + "\n")

        test_script = """
cd /root/finance_bot
python3 -c "
from sheets import SheetsManager
import config

sheets = SheetsManager()
user_id = '1047520626'

print('=== ТЕСТ 1: Заявки со статусом CREATED (Создана) ===')
created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
print(f'Количество: {len(created)}')
for req in created:
    print(f'  - {req[\"request_id\"]} | {req[\"date\"]} | {req[\"amount\"]} ₽ | Статус: {req[\"status\"]}')

print('\\n=== ТЕСТ 2: Заявки со статусом PAID (Оплачена) ===')
paid = sheets.get_requests_by_status(config.STATUS_PAID, author_id=user_id)
print(f'Количество: {len(paid)}')
for req in paid:
    print(f'  - {req[\"request_id\"]} | {req[\"date\"]} | {req[\"amount\"]} ₽ | Статус: {req[\"status\"]}')

print('\\n=== ТЕСТ 3: Заявки со статусом CANCELLED (Отменена) ===')
cancelled = sheets.get_requests_by_status(config.STATUS_CANCELLED, author_id=user_id)
print(f'Количество: {len(cancelled)}')
for req in cancelled:
    print(f'  - {req[\"request_id\"]} | {req[\"date\"]} | {req[\"amount\"]} ₽ | Статус: {req[\"status\"]}')

print('\\n=== ТЕСТ 4: ВСЕ заявки пользователя (без фильтра статуса) ===')
# Проверим что в таблице
print('Прямая проверка в таблице Основные:')
sheet = sheets.get_worksheet(config.SHEET_JOURNAL)
all_values = sheet.get_all_values()
print(f'Всего строк: {len(all_values)}')
print('Строки с author_id={user_id}:')
for i, row in enumerate(all_values[1:], start=2):
    if len(row) > 16 and str(row[16]) == user_id:
        date = row[1] if len(row) > 1 else ''
        amount = row[2] if len(row) > 2 else ''
        status = row[10] if len(row) > 10 else ''
        request_id = row[0] if len(row) > 0 else ''
        print(f'  Строка {i}: {request_id} | {date} | {amount} ₽ | Статус: \"{status}\"')

print('\\n=== config.STATUS_* значения: ===')
print(f'STATUS_CREATED = \"{config.STATUS_CREATED}\"')
print(f'STATUS_PAID = \"{config.STATUS_PAID}\"')
print(f'STATUS_CANCELLED = \"{config.STATUS_CANCELLED}\"')
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

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_requests()
