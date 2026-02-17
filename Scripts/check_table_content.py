"""
Проверка РЕАЛЬНОГО содержимого таблицы
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

def check_table_content():
    """Проверить реальное содержимое таблицы"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("РЕАЛЬНОЕ СОДЕРЖИМОЕ ТАБЛИЦЫ")
        print("="*70 + "\n")

        check_script = """
cd /root/finance_bot
python3 -c "
from sheets import SheetsManager
import config

sheets = SheetsManager()
sheet = sheets.get_worksheet(config.SHEET_JOURNAL)
all_values = sheet.get_all_values()

print(f'Всего строк: {len(all_values)}')
print()

# Заголовки
print('=== ЗАГОЛОВКИ (строка 1): ===')
if len(all_values) > 0:
    headers = all_values[0]
    for i, h in enumerate(headers, start=1):
        col_letter = chr(64 + i) if i <= 26 else f'A{chr(64 + i - 26)}'
        print(f'{col_letter} ({i:2d}): {h}')

print()
print('=== ДАННЫЕ (строки 2+): ===')
for row_num in range(1, min(len(all_values), 5)):  # Показываем до 4 строк данных
    print(f'\\nСтрока {row_num + 1}:')
    row = all_values[row_num]
    print(f'  Длина строки: {len(row)} колонок')

    # Показываем ключевые колонки
    print(f'  A (ID): {row[0] if len(row) > 0 else \"ПУСТО\"}')
    print(f'  B (Дата): {row[1] if len(row) > 1 else \"ПУСТО\"}')
    print(f'  C (Сумма): {row[2] if len(row) > 2 else \"ПУСТО\"}')
    print(f'  D (Валюта): {row[3] if len(row) > 3 else \"ПУСТО\"}')
    print(f'  E (Получатель): {row[4] if len(row) > 4 else \"ПУСТО\"}')
    print(f'  K (Статус): {row[10] if len(row) > 10 else \"ПУСТО\"}')
    print(f'  Q (Telegram ID): \"{row[16]}\" (len={len(row[16])})' if len(row) > 16 else '  Q (Telegram ID): ПУСТО')
    print(f'  R (Username): {row[17] if len(row) > 17 else \"ПУСТО\"}')
    print(f'  S (Полное имя): {row[18] if len(row) > 18 else \"ПУСТО\"}')

print()
print('=== ПРОВЕРКА: ===')
print(f'Ищем заявку с ID=REQ-20260130-005505-6C23D0E4')
for row_num, row in enumerate(all_values[1:], start=2):
    if len(row) > 0 and row[0] == 'REQ-20260130-005505-6C23D0E4':
        print(f'Найдена в строке {row_num}!')
        print(f'  Статус (K): \"{row[10]}\"' if len(row) > 10 else '  Статус: ПУСТО')
        print(f'  Telegram ID (Q): \"{row[16]}\"' if len(row) > 16 else '  Telegram ID: ПУСТО')
        break
else:
    print('НЕ НАЙДЕНА в таблице!')
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
    check_table_content()
