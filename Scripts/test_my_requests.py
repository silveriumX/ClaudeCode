"""
Тест функции my_requests() на сервере
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

def test_my_requests():
    """Тестировать функцию my_requests"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ТЕСТ ФУНКЦИИ MY_REQUESTS ===\n")

        test_script = """
import sys
sys.path.insert(0, '/root/finance_bot')
from sheets import SheetsManager
import config

s = SheetsManager()

author_id = '8127547204'

print("Получение заявок со статусами 'Создана' и 'Оплачена':\\n")

created = s.get_requests_by_status(config.STATUS_CREATED, author_id=author_id)
paid = s.get_requests_by_status(config.STATUS_PAID, author_id=author_id)

print(f"STATUS_CREATED = '{config.STATUS_CREATED}'")
print(f"STATUS_PAID = '{config.STATUS_PAID}'")
print(f"STATUS_CANCELLED = '{config.STATUS_CANCELLED}'\\n")

print(f"Создана (author_id={author_id}): {len(created)} заявок")
for req in created:
    print(f"  - {req['request_id']}: {req['date']}, Статус='{req['status']}', Сумма={req['amount']}")

print(f"\\nОплачена (author_id={author_id}): {len(paid)} заявок")
for req in paid:
    print(f"  - {req['request_id']}: {req['date']}, Статус='{req['status']}', Сумма={req['amount']}")

all_requests = created + paid
print(f"\\nВсего (Создана + Оплачена): {len(all_requests)} заявок")

if all_requests:
    print("\\nПервая заявка в списке (которая будет показана в боте):")
    req = all_requests[0]
    print(f"  Request ID: {req['request_id']}")
    print(f"  Дата: {req['date']}")
    print(f"  Статус: '{req['status']}'")
    print(f"  Сумма: {req['amount']} {req['currency']}")
    print(f"  Получатель: {req['recipient']}")

    # Callback для кнопки
    callback = f"view_req_{req['request_id']}_1"
    print(f"\\n  Callback data: {callback}")
"""

        # Создаём временный файл
        stdin, stdout, stderr = ssh.exec_command("cat > /tmp/test_my_requests.py")
        stdin.write(test_script)
        stdin.channel.shutdown_write()

        # Запускаем
        print("Запуск теста...\n")
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && python3 /tmp/test_my_requests.py", timeout=15)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)

        if error and 'FutureWarning' not in error:
            print("\n=== ОШИБКИ ===")
            print(error)

        # Удаляем временный файл
        stdin, stdout, stderr = ssh.exec_command("rm /tmp/test_my_requests.py")

        ssh.close()

        print("\n" + "="*70)
        print("ВЫВОД:")
        print("Если статус первой заявки 'Создана', но в Telegram показывается")
        print("'Отменена', значит проблема в отображении статуса в view_request_callback()")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_my_requests()
