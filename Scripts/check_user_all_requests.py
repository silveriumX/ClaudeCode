"""
Проверка всех заявок пользователя 8127547204
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv("VPS_LINUX_HOST"), username='root', password=os.getenv("VPS_LINUX_PASSWORD"))

script = """
cd /root/finance_bot
python3 << 'PYTHON'
from sheets import SheetsManager
import config

sheets = SheetsManager()
user_id = '8127547204'

# Получаем созданные
created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
print(f"STATUS_CREATED ('{config.STATUS_CREATED}'): {len(created)} requests")
for r in created[:3]:
    print(f"  - {r.get('request_id')}: {r.get('date')} - {r.get('amount')} - {r.get('status')}")

# Получаем оплаченные
paid = sheets.get_requests_by_status(config.STATUS_PAID, author_id=user_id)
print(f"\\nSTATUS_PAID ('{config.STATUS_PAID}'): {len(paid)} requests")
for r in paid[:3]:
    print(f"  - {r.get('request_id')}: {r.get('date')} - {r.get('amount')} - {r.get('status')}")

# Проверяем все заявки этого пользователя (любой статус)
print(f"\\nВсе листы для поиска:")
for sheet_name in [config.SHEET_JOURNAL, config.SHEET_OTHER_PAYMENTS, config.SHEET_USDT]:
    print(f"  - {sheet_name}")
    try:
        sheet = sheets.get_worksheet(sheet_name)
        all_values = sheet.get_all_values()
        rows = all_values[1:]

        # Для каждой валюты свой индекс author_id
        if sheet_name == config.SHEET_USDT:
            author_idx = 10  # K
            status_idx = 6   # G
        else:
            author_idx = 16  # Q
            status_idx = 10  # K

        user_rows = [r for r in rows if len(r) > author_idx and str(r[author_idx]) == user_id]
        print(f"    Найдено строк: {len(user_rows)}")
        for row in user_rows[:2]:
            status = row[status_idx] if len(row) > status_idx else ''
            req_id = row[0] if len(row) > 0 else ''
            print(f"      {req_id}: status='{status}'")
    except Exception as e:
        print(f"    Ошибка: {e}")
PYTHON
"""

stdin, stdout, stderr = ssh.exec_command(script)
output = stdout.read().decode('utf-8', errors='replace')
print(output)

error = stderr.read().decode('utf-8', errors='replace')
if error:
    print("\nERRORS:")
    print(error)

ssh.close()
