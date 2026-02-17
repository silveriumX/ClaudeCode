"""
Проверка логов ПОСЛЕ отмены заявки
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

def check_cancel_logs():
    """Проверить логи после отмены"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("\n" + "="*70)
        print("ЛОГИ ПОСЛЕ ОТМЕНЫ ЗАЯВКИ")
        print("="*70 + "\n")

        # Последние 50 строк логов
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u finance_bot -n 50 --no-pager | grep -E '(DEBUG|ERROR|cancel_request|update_request_status|Oshibka|OK:)'"
        )
        logs = stdout.read().decode('utf-8', errors='replace')

        print(logs)

        # Проверяем статус заявки в таблице
        print("\n" + "="*70)
        print("СТАТУС ЗАЯВКИ В ТАБЛИЦЕ:")
        print("="*70 + "\n")

        check_script = """
cd /root/finance_bot
python3 -c "
from sheets import SheetsManager
import config
sheets = SheetsManager()
request = sheets.get_request_by_id('29.01.2026', 38600, 'RUB')
if request:
    print('request_id:', request.get('request_id'))
    print('status:', request.get('status'))
    print('currency:', request.get('currency'))
    print('sheet_name:', request.get('sheet_name'))

    # Проверяем статус через get_requests_by_status
    print('\\n--- Заявки со статусом Отменена для user_id=1047520626:')
    cancelled = sheets.get_requests_by_status(config.STATUS_CANCELLED, author_id='1047520626')
    print(f'Количество: {len(cancelled)}')
    if cancelled:
        for req in cancelled:
            print(f'  - {req[\"date\"]} • {req[\"amount\"]} ₽ • {req[\"status\"]}')
else:
    print('ЗАЯВКА НЕ НАЙДЕНА!')
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
    check_cancel_logs()
