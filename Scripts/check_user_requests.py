"""
Проверка заявок пользователя - какие заявки есть и с каким author_id
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

def check_user_requests():
    """Проверить заявки пользователя"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА ЗАЯВОК ПОЛЬЗОВАТЕЛЯ ===\n")

        # Скрипт для проверки
        check_script = """
import sys
sys.path.insert(0, '/root/finance_bot')
from sheets import SheetsManager
import config

s = SheetsManager()

print("=== ВСЕ ЗАЯВКИ ИЗ ЛИСТА 'Основные' (без фильтра по автору) ===\\n")
sheet = s.get_worksheet(config.SHEET_JOURNAL)
all_data = sheet.get_all_values()

if len(all_data) > 1:
    headers = all_data[0]
    print(f"Всего заявок: {len(all_data) - 1}\\n")

    for i, row in enumerate(all_data[1:], 1):  # Пропускаем заголовок
        if len(row) > 16:  # Есть author_id
            req_id = row[0][:30] if len(row) > 0 else ''
            date = row[1] if len(row) > 1 else ''
            amount = row[2] if len(row) > 2 else ''
            currency = row[3] if len(row) > 3 else ''
            recipient = row[4][:20] if len(row) > 4 else ''
            status = row[10] if len(row) > 10 else ''
            author_id = row[16] if len(row) > 16 else ''
            author_username = row[17] if len(row) > 17 else ''

            print(f"{i}. ID: {req_id}")
            print(f"   Дата: {date}, Сумма: {amount} {currency}")
            print(f"   Получатель: {recipient}, Статус: {status}")
            print(f"   Author ID: '{author_id}', Username: '{author_username}'")
            print()
else:
    print("Лист пуст или только заголовок\\n")

print("="*70)
print("=== УНИКАЛЬНЫЕ AUTHOR_ID ===\\n")

author_ids = set()
for row in all_data[1:]:
    if len(row) > 16 and row[16]:
        author_ids.add(row[16])

if author_ids:
    for aid in sorted(author_ids):
        # Считаем заявки для этого автора
        created = sum(1 for row in all_data[1:] if len(row) > 16 and row[16] == aid and len(row) > 10 and row[10] == config.STATUS_CREATED)
        paid = sum(1 for row in all_data[1:] if len(row) > 16 and row[16] == aid and len(row) > 10 and row[10] == config.STATUS_PAID)
        cancelled = sum(1 for row in all_data[1:] if len(row) > 16 and row[16] == aid and len(row) > 10 and row[10] == config.STATUS_CANCELLED)

        print(f"Author ID: '{aid}'")
        print(f"  Создана: {created}, Оплачена: {paid}, Отменена: {cancelled}")
        print(f"  Всего (Создана + Оплачена): {created + paid}")
        print()
else:
    print("Нет заявок с указанным author_id\\n")

print("="*70)
print("=== ПРОВЕРКА ЧЕРЕЗ get_requests_by_status (без author_id) ===\\n")

# Проверяем функцию get_requests_by_status БЕЗ фильтра по автору
created_all = s.get_requests_by_status(config.STATUS_CREATED)
paid_all = s.get_requests_by_status(config.STATUS_PAID)
cancelled_all = s.get_requests_by_status(config.STATUS_CANCELLED)

print(f"Создана (все): {len(created_all)}")
print(f"Оплачена (все): {len(paid_all)}")
print(f"Отменена (все): {len(cancelled_all)}")

if created_all:
    print(f"\\nПример заявки со статусом 'Создана':")
    req = created_all[0]
    print(f"  Дата: {req['date']}, Сумма: {req['amount']} {req['currency']}")
    print(f"  Получатель: {req['recipient']}, Статус: {req['status']}")
    print(f"  Author ID: '{req['author_id']}', Username: '{req.get('author_username', '')}'")
"""

        # Создаём временный файл
        stdin, stdout, stderr = ssh.exec_command("cat > /tmp/check_requests.py")
        stdin.write(check_script)
        stdin.channel.shutdown_write()

        # Запускаем
        print("Запуск проверки...\n")
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && python3 /tmp/check_requests.py", timeout=20)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)

        if error and 'FutureWarning' not in error:
            print("\n=== ОШИБКИ ===")
            print(error)

        # Удаляем временный файл
        stdin, stdout, stderr = ssh.exec_command("rm /tmp/check_requests.py")

        ssh.close()

        print("\n" + "="*70)
        print("РЕКОМЕНДАЦИИ:")
        print("1. Проверьте какой author_id использует ваш аккаунт в Telegram")
        print("2. Сравните с author_id в заявках выше")
        print("3. Если author_id не совпадают - заявки не будут отображаться")
        print("4. Используйте команду /start в боте чтобы увидеть ваш user ID")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_user_requests()
