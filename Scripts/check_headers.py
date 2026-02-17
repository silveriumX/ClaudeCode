"""
Проверка реальной структуры заголовков Google Sheets
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

def check_headers():
    """Проверить заголовки таблиц"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА ЗАГОЛОВКОВ ТАБЛИЦ ===\n")

        # Проверяем заголовки всех листов
        python_cmd = """cd /root/finance_bot && python3 -c "
import sys
sys.path.insert(0, '/root/finance_bot')
from sheets import SheetsManager
import config

s = SheetsManager()

sheets_to_check = [
    (config.SHEET_JOURNAL, 'Основные'),
    (config.SHEET_OTHER_PAYMENTS, 'Разные выплаты'),
    (config.SHEET_USDT, 'USDT')
]

for sheet_name, display_name in sheets_to_check:
    try:
        sheet = s.get_worksheet(sheet_name)
        all_data = sheet.get_all_values()
        if all_data:
            headers = all_data[0]
            print(f'\\n=== {display_name} ({len(headers)} колонок) ===')
            for i, h in enumerate(headers):
                col_letter = chr(65 + i) if i < 26 else f'{chr(65 + i // 26 - 1)}{chr(65 + i % 26)}'
                print(f'{col_letter} ({i}): {h}')
        else:
            print(f'\\n=== {display_name} ===')
            print('Лист пуст')
    except Exception as e:
        print(f'\\n=== {display_name} ===')
        print(f'Ошибка: {e}')
" """

        stdin, stdout, stderr = ssh.exec_command(python_cmd, timeout=20)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)

        if error and 'FutureWarning' not in error:
            print("\n=== ОШИБКИ ===")
            print(error)

        # Теперь проверим что ОЖИДАЕТ код
        print("\n\n" + "="*70)
        print("ЧТО ОЖИДАЕТ КОД (из sheets.py):")
        print("="*70)
        print("\nRUB/BYN листы (19 колонок):")
        print("A (0):  ID заявки")
        print("B (1):  Дата")
        print("C (2):  Сумма")
        print("D (3):  Валюта")
        print("E (4):  Получатель")
        print("F (5):  Номер карты/телефона")
        print("G (6):  Банк")
        print("H (7):  Реквизиты")
        print("I (8):  Назначение")
        print("J (9):  Категория")
        print("K (10): Статус *****")
        print("L (11): ID сделки")
        print("M (12): Название аккаунта")
        print("N (13): Сумма USDT")
        print("O (14): Курс")
        print("P (15): Исполнитель")
        print("Q (16): Telegram ID автора *****")
        print("R (17): Username автора")
        print("S (18): Полное имя автора")

        print("\nUSDT лист (13 колонок):")
        print("A (0):  ID заявки")
        print("B (1):  Дата")
        print("C (2):  Сумма USDT")
        print("D (3):  Адрес кошелька")
        print("E (4):  Назначение")
        print("F (5):  Категория")
        print("G (6):  Статус *****")
        print("H (7):  ID транзакции")
        print("I (8):  Название аккаунта")
        print("J (9):  Исполнитель")
        print("K (10): Telegram ID автора *****")
        print("L (11): Username автора")
        print("M (12): Полное имя автора")

        ssh.close()

        print("\n" + "="*70)
        print("ВЫВОД:")
        print("Сравните РЕАЛЬНЫЕ заголовки с ОЖИДАЕМЫМИ!")
        print("Если колонок меньше 19 (для RUB/BYN) или 13 (для USDT),")
        print("значит таблица НЕ СООТВЕТСТВУЕТ структуре, которую ожидает код.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_headers()
