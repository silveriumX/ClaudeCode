"""
РЕАЛЬНАЯ ДИАГНОСТИКА - смотрим логи в момент отмены заявки
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import sys
import time

# Фикс кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def real_time_diagnosis():
    """Диагностика в реальном времени"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("РЕАЛЬНАЯ ДИАГНОСТИКА - ОТМЕНА ЗАЯВКИ")
        print("="*70)

        # 1. Текущие логи (последние 30 строк)
        print("\n1. ПОСЛЕДНИЕ ЛОГИ (до отмены заявки):\n")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u finance_bot -n 30 --no-pager | grep -v 'getUpdates'"
        )
        logs_before = stdout.read().decode('utf-8', errors='replace')
        print(logs_before[-2000:] if len(logs_before) > 2000 else logs_before)

        # 2. Проверяем код функции cancel_request_callback
        print("\n2. КОД ФУНКЦИИ cancel_request_callback (строки 746-752):\n")
        stdin, stdout, stderr = ssh.exec_command(
            "sed -n '746,752p' /root/finance_bot/handlers/request.py"
        )
        code = stdout.read().decode('utf-8', errors='replace')
        print(code)

        # 3. Проверяем код функции update_request_status
        print("\n3. КОД ФУНКЦИИ update_request_status (строки 608-667):\n")
        stdin, stdout, stderr = ssh.exec_command(
            "sed -n '608,667p' /root/finance_bot/sheets.py"
        )
        code2 = stdout.read().decode('utf-8', errors='replace')
        print(code2)

        # 4. Проверяем данные РЕАЛЬНОЙ заявки в таблице
        print("\n4. ДАННЫЕ РЕАЛЬНОЙ ЗАЯВКИ (29.01.2026, 38600):\n")
        test_script = """
cd /root/finance_bot
python3 -c "
from sheets import SheetsManager
import config
sheets = SheetsManager()
request = sheets.get_request_by_id('29.01.2026', 38600, 'RUB')
if request:
    print('request_id:', request.get('request_id'))
    print('date:', request.get('date'))
    print('amount:', request.get('amount'))
    print('currency:', request.get('currency'))
    print('status:', request.get('status'))
    print('sheet_name:', request.get('sheet_name'))
else:
    print('ЗАЯВКА НЕ НАЙДЕНА!')
"
"""
        stdin, stdout, stderr = ssh.exec_command(test_script)
        test_output = stdout.read().decode('utf-8', errors='replace')
        test_error = stderr.read().decode('utf-8', errors='replace')

        if test_output:
            print(test_output)
        if test_error:
            print("ОШИБКИ:")
            print(test_error)

        print("\n" + "="*70)
        print("ТЕПЕРЬ:")
        print("1. Откройте 'Мои заявки' в Telegram")
        print("2. Нажмите на заявку")
        print("3. Нажмите 'Отменить заявку'")
        print("4. СРАЗУ после этого выполните:")
        print("   python Scripts\\check_cancel_logs.py")
        print("="*70)

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    real_time_diagnosis()
