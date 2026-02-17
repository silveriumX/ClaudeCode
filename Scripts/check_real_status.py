"""
Проверка РЕАЛЬНОГО статуса заявки в таблице
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

def check_real_status():
    """Проверить реальный статус заявки от 29.01.2026"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА РЕАЛЬНОГО СТАТУСА ЗАЯВКИ ===\n")

        check_script = """
import sys
sys.path.insert(0, '/root/finance_bot')
from sheets import SheetsManager
import config

s = SheetsManager()
sheet = s.get_worksheet(config.SHEET_JOURNAL)
all_data = sheet.get_all_values()

print("=== ЗАЯВКА ОТ 29.01.2026 (детали) ===\\n")

if len(all_data) > 1:
    headers = all_data[0]

    # Ищем заявку от 29.01.2026
    for i, row in enumerate(all_data[1:], 2):  # Начинаем с 2 (1=заголовок, 2=первая строка данных)
        if len(row) > 1 and row[1] == '29.01.2026':  # Колонка B = Дата
            print(f"СТРОКА {i} в таблице:\\n")

            # Показываем ВСЕ колонки
            for j, (header, value) in enumerate(zip(headers, row)):
                col_letter = chr(65 + j) if j < 26 else f'{chr(65 + j // 26 - 1)}{chr(65 + j % 26)}'
                print(f"{col_letter} ({j:2d}) {header:30s}: '{value}'")

            print(f"\\n{'='*70}")
            print(f"ВАЖНО! Статус в колонке K (индекс 10): '{row[10] if len(row) > 10 else 'НЕТ ДАННЫХ'}'")
            print(f"{'='*70}\\n")

print("\\n=== ПРОВЕРКА get_requests_by_status() ===\\n")

# Проверяем что возвращает функция для каждого статуса
for status_name, status_value in [('Создана', config.STATUS_CREATED),
                                   ('Оплачена', config.STATUS_PAID),
                                   ('Отменена', config.STATUS_CANCELLED)]:
    requests = s.get_requests_by_status(status_value, author_id='8127547204')
    print(f"{status_name} (author_id=8127547204): {len(requests)} заявок")

    if requests:
        for req in requests:
            print(f"  - Дата: {req['date']}, Статус в данных: '{req['status']}', Сумма: {req['amount']}")

print("\\n=== ПРОВЕРКА view_request_callback ===\\n")

# Проверяем как формируется callback_data для кнопки
print("Callback data для заявки от 29.01.2026:")
print("Формат: view_req_{date}_{amount}_{currency}_{page}")

# Ищем заявку
created = s.get_requests_by_status(config.STATUS_CREATED, author_id='8127547204')
paid = s.get_requests_by_status(config.STATUS_PAID, author_id='8127547204')
cancelled = s.get_requests_by_status(config.STATUS_CANCELLED, author_id='8127547204')

all_reqs = created + paid + cancelled

for req in all_reqs:
    if '29.01.2026' in req['date']:
        callback = f"view_req_{req['date']}_{req['amount']}_{req.get('currency', 'RUB')}_1"
        print(f"\\nЗаявка: {req['date']}, Статус: '{req['status']}'")
        print(f"Callback: {callback}")
        print(f"Показывается в списке: {'ДА' if req['status'] in [config.STATUS_CREATED, config.STATUS_PAID] else 'НЕТ (отменена)'}")
"""

        # Создаём временный файл
        stdin, stdout, stderr = ssh.exec_command("cat > /tmp/check_status.py")
        stdin.write(check_script)
        stdin.channel.shutdown_write()

        # Запускаем
        print("Запуск проверки...\n")
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && python3 /tmp/check_status.py", timeout=20)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)

        if error and 'FutureWarning' not in error:
            print("\n=== ОШИБКИ ===")
            print(error)

        # Удаляем временный файл
        stdin, stdout, stderr = ssh.exec_command("rm /tmp/check_status.py")

        ssh.close()

        print("\n" + "="*70)
        print("ВЫВОД:")
        print("Если статус в таблице 'Создана', но показывается 'Отменена',")
        print("значит баг в функции view_request_callback() - она читает")
        print("неправильную колонку или данные изменились после чтения.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_real_status()
