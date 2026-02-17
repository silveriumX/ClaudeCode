"""
Полная проверка после удаления листа с кракозябрами
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv("VPS_LINUX_HOST"), username='root', password=os.getenv("VPS_LINUX_PASSWORD"))

print("="*70)
print("ПОЛНАЯ ПРОВЕРКА FINANCE BOT")
print("="*70 + "\n")

# 1. Проверка листов в таблице
print("1. Листы в Google Sheets:")
stdin, stdout, stderr = ssh.exec_command("""
cd /root/finance_bot
python3 << 'EOF'
from sheets import SheetsManager
sheets = SheetsManager()
all_sheets = sheets.spreadsheet.worksheets()
print(f"Всего листов: {len(all_sheets)}")
for i, s in enumerate(all_sheets, 1):
    print(f"  {i}. {s.title}")

# Проверяем наличие нужных листов
required = ['Основные', 'Разные выплаты', 'USDT', 'USDT Зарплаты']
print(f"\nПроверка обязательных листов:")
for name in required:
    try:
        sheet = sheets.spreadsheet.worksheet(name)
        print(f"  ✓ {name}")
    except:
        print(f"  ✗ {name} - НЕ НАЙДЕН!")
EOF
""")
print(stdout.read().decode('utf-8', errors='replace'))

# 2. Проверка config
print("\n2. Проверка config.py:")
stdin, stdout, stderr = ssh.exec_command("""
cd /root/finance_bot
python3 -c "
import config
print(f'SHEET_JOURNAL: {config.SHEET_JOURNAL}')
print(f'SHEET_OTHER_PAYMENTS: {config.SHEET_OTHER_PAYMENTS}')
print(f'SHEET_USDT: {config.SHEET_USDT}')
print(f'SHEET_USDT_SALARIES: {config.SHEET_USDT_SALARIES}')
"
""")
print(stdout.read().decode('utf-8', errors='replace'))

# 3. Проверка заявок пользователя
print("\n3. Заявки пользователя 8127547204:")
stdin, stdout, stderr = ssh.exec_command("""
cd /root/finance_bot
python3 << 'EOF'
from sheets import SheetsManager
import config

sheets = SheetsManager()
user_id = '8127547204'

# Созданные
created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
print(f"Создана: {len(created)}")
for r in created[:3]:
    print(f"  - {r.get('request_id')}: {r.get('amount')} {r.get('currency')} [{r.get('sheet_name')}]")

# Оплаченные
paid = sheets.get_requests_by_status(config.STATUS_PAID, author_id=user_id)
print(f"\nОплачена: {len(paid)}")
for r in paid[:3]:
    print(f"  - {r.get('request_id')}: {r.get('amount')} {r.get('currency')} [{r.get('sheet_name')}]")

# Общее количество
all_created = sheets.get_requests_by_status(config.STATUS_CREATED)
all_paid = sheets.get_requests_by_status(config.STATUS_PAID)
print(f"\nВсего в системе:")
print(f"  Создано: {len(all_created)}")
print(f"  Оплачено: {len(all_paid)}")
EOF
""")
print(stdout.read().decode('utf-8', errors='replace'))

# 4. Тест поиска по request_id
print("\n4. Тест поиска оплаченной заявки:")
stdin, stdout, stderr = ssh.exec_command("""
cd /root/finance_bot
python3 << 'EOF'
from sheets import SheetsManager
import config

sheets = SheetsManager()

# Получаем все оплаченные
all_paid = sheets.get_requests_by_status(config.STATUS_PAID)
if all_paid:
    test_req = all_paid[0]
    req_id = test_req.get('request_id')
    print(f"Тестовая заявка: {req_id}")
    print(f"  Сумма: {test_req.get('amount')}")
    print(f"  Лист: {test_req.get('sheet_name')}")

    # Пытаемся найти её через get_request_by_request_id
    print(f"\nПоиск через get_request_by_request_id...")
    found = sheets.get_request_by_request_id(req_id)
    if found:
        print(f"  ✓ Найдена! Лист: {found.get('sheet_name')}")
    else:
        print(f"  ✗ НЕ НАЙДЕНА!")
else:
    print("Нет оплаченных заявок для теста")
EOF
""")
print(stdout.read().decode('utf-8', errors='replace'))

# 5. Статус бота
print("\n5. Статус бота:")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
status = stdout.read().decode().strip()
print(f"Бот: {status}")

# 6. Последние логи
print("\n6. Последние логи (ошибки):")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u finance_bot -n 20 --no-pager | grep -E '(ERROR|Exception|Traceback)' | tail -5 || echo 'Нет ошибок'"
)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()

print("\n" + "="*70)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("="*70)
