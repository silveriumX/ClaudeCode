"""
Исправление структуры USDT листа - добавление недостающих колонок
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

def fix_usdt_sheet():
    """Добавить недостающие колонки в USDT лист"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ИСПРАВЛЕНИЕ СТРУКТУРЫ USDT ЛИСТА ===\n")

        # Создаём скрипт для добавления колонок
        fix_script = """
import sys
sys.path.insert(0, '/root/finance_bot')
from sheets import SheetsManager
import config

s = SheetsManager()
usdt_sheet = s.get_worksheet(config.SHEET_USDT)

# Получаем текущие данные
all_data = usdt_sheet.get_all_values()
print(f"Текущее количество строк: {len(all_data)}")
print(f"Текущее количество колонок в заголовке: {len(all_data[0]) if all_data else 0}")

if not all_data:
    print("Лист пуст, ничего не делаем")
    sys.exit(0)

# Текущие заголовки (10 колонок)
headers = all_data[0]
print(f"\\nТекущие заголовки: {headers}")

# Проверяем, нужно ли добавлять колонки
if len(headers) >= 13:
    print("\\nКолонки уже добавлены! Ничего не делаем.")
    sys.exit(0)

# Добавляем 3 новые колонки в заголовок
new_headers = headers + ['Telegram ID инициатора', 'Username инициатора', 'Полное имя инициатора']
print(f"\\nНовые заголовки ({len(new_headers)} колонок): {new_headers}")

# Обновляем заголовок
usdt_sheet.update('A1:M1', [new_headers])
print("\\n✓ Заголовки обновлены!")

# Для каждой существующей строки добавляем пустые значения в новые колонки
if len(all_data) > 1:
    print(f"\\nДобавление пустых значений в {len(all_data)-1} строк...")
    for row_idx in range(2, len(all_data) + 1):  # Начинаем со 2-й строки (пропускаем заголовок)
        row = all_data[row_idx - 1]
        if len(row) < 13:
            # Добавляем пустые значения
            missing = 13 - len(row)
            new_row = row + [''] * missing
            usdt_sheet.update(f'A{row_idx}:M{row_idx}', [new_row])
            print(f"  Строка {row_idx}: добавлено {missing} пустых значений")

print("\\n✓ Структура USDT листа исправлена!")
print("\\nТеперь лист USDT имеет 13 колонок (A-M):")
print("A: ID заявки")
print("B: Дата")
print("C: Сумма USDT")
print("D: Адрес кошелька")
print("E: Назначение")
print("F: Категория")
print("G: Статус")
print("H: ID транзакции")
print("I: Название аккаунта")
print("J: Исполнитель")
print("K: Telegram ID инициатора  ← НОВАЯ")
print("L: Username инициатора     ← НОВАЯ")
print("M: Полное имя инициатора   ← НОВАЯ")
"""

        # Создаём временный файл
        stdin, stdout, stderr = ssh.exec_command("cat > /tmp/fix_usdt.py")
        stdin.write(fix_script)
        stdin.channel.shutdown_write()

        # Запускаем скрипт
        print("Запуск исправления...\n")
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && python3 /tmp/fix_usdt.py", timeout=30)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)

        if error and 'FutureWarning' not in error:
            print("\n=== ОШИБКИ ===")
            print(error)

        # Удаляем временный файл
        stdin, stdout, stderr = ssh.exec_command("rm /tmp/fix_usdt.py")

        # Проверяем результат
        print("\n" + "="*70)
        print("ПРОВЕРКА РЕЗУЛЬТАТА:")
        print("="*70 + "\n")

        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && python3 -c \"import sys; sys.path.insert(0, '/root/finance_bot'); from sheets import SheetsManager; import config; s = SheetsManager(); sheet = s.get_worksheet(config.SHEET_USDT); data = sheet.get_all_values(); print(f'Количество колонок: {len(data[0]) if data else 0}')\"", timeout=15)
        result = stdout.read().decode('utf-8', errors='replace')
        print(result)

        ssh.close()

        print("\n" + "="*70)
        print("✓ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
        print("\nТеперь можно создавать USDT заявки с сохранением author_id")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_usdt_sheet()
