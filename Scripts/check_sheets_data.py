"""
Проверка данных в Google Sheets - список заявок пользователя
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

def check_sheets_data():
    """Проверить данные в Google Sheets"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА ДАННЫХ GOOGLE SHEETS ===\n")

        # Создаём временный скрипт на сервере для проверки Sheets
        check_script = '''
import sys
sys.path.insert(0, '/root/finance_bot')

from sheets import SheetsManager
import config

# Инициализация
sheets = SheetsManager()

# ID пользователя из ваших тестов (нужно узнать реальный)
# Попробуем получить все заявки и посмотреть author_id
print("\\n=== ВСЕ ЗАЯВКИ (первые 10) ===\\n")

from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(
    config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('sheets', 'v4', credentials=creds)

# Получаем данные из листа Zhurnal
result = service.spreadsheets().values().get(
    spreadsheetId=config.GOOGLE_SHEETS_ID,
    range='Zhurnal!A1:Z100'
).execute()

values = result.get('values', [])
if not values:
    print("Лист Zhurnal пуст")
else:
    headers = values[0]
    print(f"Заголовки: {headers}\\n")
    print(f"Всего строк (включая заголовок): {len(values)}\\n")

    # Находим индексы нужных колонок
    try:
        date_idx = headers.index('Data')
        amount_idx = headers.index('Summa')
        currency_idx = headers.index('Valjuta')
        status_idx = headers.index('Status')
        author_idx = headers.index('ID_avtora')
        recipient_idx = headers.index('Poluchatel')
    except ValueError as e:
        print(f"Ошибка: не найдена колонка - {e}")
        sys.exit(1)

    print("Первые 15 заявок:\\n")
    for i, row in enumerate(values[1:16], 1):  # Skip header
        if len(row) > max(date_idx, amount_idx, currency_idx, status_idx, author_idx):
            date = row[date_idx] if len(row) > date_idx else ''
            amount = row[amount_idx] if len(row) > amount_idx else ''
            currency = row[currency_idx] if len(row) > currency_idx else ''
            status = row[status_idx] if len(row) > status_idx else ''
            author = row[author_idx] if len(row) > author_idx else ''
            recipient = row[recipient_idx] if len(row) > recipient_idx else ''

            print(f"{i}. Дата: {date}, Сумма: {amount} {currency}, Статус: {status}")
            print(f"   Author ID: {author}, Получатель: {recipient}\\n")

# Проверяем статусы
print("\\n=== СТАТИСТИКА ПО СТАТУСАМ ===\\n")
statuses = {}
for row in values[1:]:
    if len(row) > status_idx:
        status = row[status_idx]
        statuses[status] = statuses.get(status, 0) + 1

for status, count in statuses.items():
    print(f"{status}: {count} заявок")

print("\\n=== СТАТУСЫ ИЗ CONFIG ===")
print(f"STATUS_CREATED = '{config.STATUS_CREATED}'")
print(f"STATUS_PAID = '{config.STATUS_PAID}'")
print(f"STATUS_CANCELLED = '{config.STATUS_CANCELLED}'")
'''

        # Сохраняем скрипт на сервер
        print("1. Создание тестового скрипта на сервере...")
        stdin, stdout, stderr = ssh.exec_command(f"cat > /root/finance_bot/test_sheets.py << 'EOFPYTHON'\n{check_script}\nEOFPYTHON")
        print("   OK\n")

        # Запускаем скрипт
        print("2. Запуск проверки данных (это может занять несколько секунд)...\n")
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && python3 test_sheets.py", timeout=15)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)

        if error:
            print("\n=== ОШИБКИ ===")
            print(error)

        # Удаляем тестовый скрипт
        stdin, stdout, stderr = ssh.exec_command("rm /root/finance_bot/test_sheets.py")

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_sheets_data()
