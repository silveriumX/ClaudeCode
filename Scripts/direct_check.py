"""
Прямая проверка через SSH - получение списка листов и данных
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

def direct_check():
    """Прямая проверка"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРЯМАЯ ПРОВЕРКА ЧЕРЕЗ SSH ===\n")

        # 1. Проверяем config
        print("1. Проверка config.py:\n")
        stdin, stdout, stderr = ssh.exec_command("grep 'SHEET_' /root/finance_bot/config.py | grep -v '#'")
        config_sheets = stdout.read().decode('utf-8', errors='replace')
        print(config_sheets)

        # 2. Проверяем Google Sheets ID
        print("\n2. Google Sheets ID:\n")
        stdin, stdout, stderr = ssh.exec_command("grep 'GOOGLE_SHEETS_ID' /root/finance_bot/config.py | grep -v '#'")
        sheets_id = stdout.read().decode('utf-8', errors='replace')
        print(sheets_id)

        # 3. Запускаем Python одной строкой для проверки листов
        print("\n3. Список листов в таблице:\n")
        python_cmd = "cd /root/finance_bot && python3 -c \"import sys; sys.path.insert(0, '/root/finance_bot'); from sheets import SheetsManager; s = SheetsManager(); ws = s.spreadsheet.worksheets(); [print(f'{i}. {w.title}') for i, w in enumerate(ws, 1)]\""
        stdin, stdout, stderr = ssh.exec_command(python_cmd, timeout=15)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)
        if error and 'FutureWarning' not in error:
            print(f"Ошибка: {error}")

        # 4. Проверяем количество заявок по статусам
        print("\n4. Проверка заявок по статусам:\n")
        python_cmd2 = "cd /root/finance_bot && python3 -c \"import sys; sys.path.insert(0, '/root/finance_bot'); from sheets import SheetsManager; import config; s = SheetsManager(); created = s.get_requests_by_status(config.STATUS_CREATED); paid = s.get_requests_by_status(config.STATUS_PAID); cancelled = s.get_requests_by_status(config.STATUS_CANCELLED); print(f'Создана: {len(created)} заявок'); print(f'Оплачена: {len(paid)} заявок'); print(f'Отменена: {len(cancelled)} заявок'); print(f'Всего (Создана + Оплачена): {len(created) + len(paid)} заявок')\""
        stdin, stdout, stderr = ssh.exec_command(python_cmd2, timeout=15)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)
        if error and 'FutureWarning' not in error:
            print(f"Ошибка: {error}")

        # 5. Получаем первые 3 заявки (любого статуса) для примера
        print("\n5. Примеры заявок (первые 3):\n")
        python_cmd3 = """cd /root/finance_bot && python3 -c "import sys; sys.path.insert(0, '/root/finance_bot'); from sheets import SheetsManager; s = SheetsManager(); all_data = s.journal_sheet.get_all_values(); headers = all_data[0]; print('Заголовки:', ', '.join(headers[:10])); print(); [print(f'{i}. Дата: {row[0]}, Сумма: {row[1]}, Валюта: {row[2]}, Статус: {row[3]}, Author ID: {row[10] if len(row) > 10 else \"N/A\"}') for i, row in enumerate(all_data[1:4], 1) if len(row) > 3]" """
        stdin, stdout, stderr = ssh.exec_command(python_cmd3, timeout=15)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)
        if error and 'FutureWarning' not in error:
            print(f"Ошибка: {error}")

        ssh.close()

        print("\n" + "="*70)
        print("ИТОГ:")
        print("Проверьте данные выше чтобы понять:")
        print("1. Какие листы есть в таблице")
        print("2. Сколько заявок в каждом статусе")
        print("3. Какие author_id используются")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    direct_check()
