"""
Проверка названий листов в Google Sheets
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

def check_sheet_names():
    """Проверить названия листов"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА ЛИСТОВ В GOOGLE SHEETS ===\n")

        # Создаём скрипт для получения списка листов
        check_script = '''
import sys
sys.path.insert(0, '/root/finance_bot')

from sheets import SheetsManager
import config

# Проверяем config
print("=== CONFIG ===")
print(f"SHEET_JOURNAL = '{config.SHEET_JOURNAL}'")
print(f"SHEET_USERS = '{config.SHEET_USERS}'")
print(f"GOOGLE_SHEETS_ID = '{config.GOOGLE_SHEETS_ID}'")

# Инициализация
sheets = SheetsManager()

# Получаем список всех листов
print("\\n=== СПИСОК ЛИСТОВ В ТАБЛИЦЕ ===")
worksheets = sheets.spreadsheet.worksheets()
for i, ws in enumerate(worksheets, 1):
    print(f"{i}. {ws.title}")

print("\\n=== ПРОВЕРКА ДОСТУПА К ЛИСТАМ ===")
try:
    journal = sheets.journal_sheet
    print(f"✓ Лист журнала ({config.SHEET_JOURNAL}): {journal.row_count} строк")
except Exception as e:
    print(f"✗ Ошибка доступа к листу журнала: {e}")

try:
    users = sheets.users_sheet
    if users:
        print(f"✓ Лист пользователей ({config.SHEET_USERS}): {users.row_count} строк")
    else:
        print("✗ Лист пользователей не инициализирован")
except Exception as e:
    print(f"✗ Ошибка доступа к листу пользователей: {e}")
'''

        # Сохраняем и запускаем
        print("Запуск проверки...\n")
        stdin, stdout, stderr = ssh.exec_command(f"cat > /root/finance_bot/test_sheets.py << 'EOFPYTHON'\n{check_script}\nEOFPYTHON && python3 /root/finance_bot/test_sheets.py", timeout=15)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)

        if error and 'FutureWarning' not in error:
            print("\n=== ОШИБКИ ===")
            print(error)

        # Удаляем скрипт
        stdin, stdout, stderr = ssh.exec_command("rm /root/finance_bot/test_sheets.py")

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_sheet_names()
