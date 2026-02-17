"""
Диагностика: почему оплаченные заявки не находятся
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def diagnose_paid_requests():
    """Проверить поиск оплаченных заявок"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДИАГНОСТИКА: Поиск оплаченных заявок")
        print("="*70 + "\n")

        # Проверяем config.SHEET_USDT_SALARIES
        print("1. Проверка config.SHEET_USDT_SALARIES...")
        stdin, stdout, stderr = ssh.exec_command(
            "cd /root/finance_bot && python3 -c \"import config; print('SHEET_USDT_SALARIES:', config.SHEET_USDT_SALARIES)\""
        )
        print(f"   {stdout.read().decode('utf-8', errors='replace')}")

        # Проверяем список листов в sheets_to_search
        print("2. Проверка sheets_to_search в get_request_by_request_id()...")
        stdin, stdout, stderr = ssh.exec_command(
            "cd /root/finance_bot && grep -A 10 'def get_request_by_request_id' sheets.py | grep -A 6 'sheets_to_search'"
        )
        result = stdout.read().decode('utf-8', errors='replace')
        print(f"   {result}\n")

        # Тестовый поиск заявки
        print("3. Тестовый поиск оплаченной заявки...")
        stdin, stdout, stderr = ssh.exec_command("""
cd /root/finance_bot && python3 << 'EOF'
from sheets import SheetsManager
import config

sheets = SheetsManager()

# Получаем оплаченные заявки
paid = sheets.get_requests_by_status(config.STATUS_PAID, author_id='8127547204')
print(f"Оплаченных заявок: {len(paid)}")

if paid:
    req = paid[0]
    print(f"\\nПервая заявка:")
    print(f"  ID: {req.get('request_id')}")
    print(f"  Дата: {req.get('date')}")
    print(f"  Сумма: {req.get('amount')}")
    print(f"  Лист: {req.get('sheet_name')}")

    # Пытаемся найти эту же заявку
    print(f"\\nПоиск по request_id...")
    found = sheets.get_request_by_request_id(req.get('request_id'))
    if found:
        print(f"  Найдена! Лист: {found.get('sheet_name')}")
    else:
        print(f"  НЕ НАЙДЕНА!")
EOF
        """)
        result = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        print(result)
        if error:
            print(f"   Ошибки: {error}\n")

        ssh.close()

        print("="*70)
        print("ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("="*70)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_paid_requests()
