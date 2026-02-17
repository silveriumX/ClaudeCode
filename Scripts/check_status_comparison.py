"""
Детальная проверка сравнения статусов
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

def check_status_comparison():
    """Проверить сравнение статусов"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДЕТАЛЬНАЯ ПРОВЕРКА СРАВНЕНИЯ СТАТУСОВ")
        print("="*70 + "\n")

        check_script = """
cd /root/finance_bot
python3 -c "
from sheets import SheetsManager
import config

sheets = SheetsManager()
user_id = '8127547204'

# Читаем таблицу напрямую
sheet = sheets.get_worksheet(config.SHEET_JOURNAL)
all_values = sheet.get_all_values()

print('=== ПРЯМОЕ ЧТЕНИЕ ТАБЛИЦЫ ===')
print(f'config.STATUS_CREATED = \\\"{config.STATUS_CREATED}\\\"')
print(f'config.STATUS_PAID = \\\"{config.STATUS_PAID}\\\"')
print(f'config.STATUS_CANCELLED = \\\"{config.STATUS_CANCELLED}\\\"')
print()

for i, row in enumerate(all_values[1:], start=2):
    if len(row) > 16 and str(row[16]) == user_id:
        status_in_table = row[10] if len(row) > 10 else ''
        author_in_table = row[16] if len(row) > 16 else ''

        print(f'Строка {i}:')
        print(f'  Статус в таблице: \\\"{status_in_table}\\\" (len={len(status_in_table)})')
        print(f'  Author ID: \\\"{author_in_table}\\\" (len={len(author_in_table)})')
        print(f'  Статус == CREATED: {status_in_table == config.STATUS_CREATED}')
        print(f'  Статус == PAID: {status_in_table == config.STATUS_PAID}')
        print(f'  Статус == CANCELLED: {status_in_table == config.STATUS_CANCELLED}')
        print(f'  Author == user_id: {str(author_in_table) == str(user_id)}')

        # Побайтовое сравнение
        print(f'  Байты статуса: {[ord(c) for c in status_in_table]}')
        print(f'  Байты CREATED: {[ord(c) for c in config.STATUS_CREATED]}')
        print()

print('=== ТЕСТ get_requests_by_status ===')
# Добавим debug в функцию
print('Вызов: get_requests_by_status(config.STATUS_CREATED, author_id=user_id)')
created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
print(f'Результат: {len(created)} заявок')

if len(created) == 0:
    print('\\n!!! ЗАЯВКИ НЕ НАЙДЕНЫ !!!')
    print('Проблема в функции get_requests_by_status!')
"
"""

        stdin, stdout, stderr = ssh.exec_command(check_script)
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
    check_status_comparison()
