"""
Деплой новой логики распределения по листам
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

def deploy_sheet_logic():
    """Загрузить обновлённые config.py и sheets.py"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДЕПЛОЙ: Новая логика распределения по листам")
        print("="*70 + "\n")

        # Загружаем файлы
        sftp = ssh.open_sftp()

        print("1. Загрузка обновлённых файлов...")

        files = [
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\config.py",
             "/root/finance_bot/config.py"),
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\sheets.py",
             "/root/finance_bot/sheets.py"),
        ]

        for local, remote in files:
            print(f"   Uploading {local.split('\\')[-1]}...")
            sftp.put(local, remote)

        print("   OK: Все файлы загружены\n")

        sftp.close()

        # Перезапускаем бота
        print("2. Перезапуск бота...")
        ssh.exec_command("systemctl restart finance_bot")

        import time
        time.sleep(3)

        # Проверяем статус
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()

        if status == "active":
            print(f"   OK: Бот запущен ({status})\n")
        else:
            print(f"   ERROR: Бот не запустился ({status})\n")
            stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 20 --no-pager")
            print(stdout.read().decode('utf-8', errors='replace'))
            ssh.close()
            return

        # Проверяем логи
        print("3. Проверка логов...")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u finance_bot -n 10 --no-pager | grep -E '(ERROR|Exception)' || echo 'No errors'"
        )
        print(f"   {stdout.read().decode('utf-8', errors='replace')}\n")

        ssh.close()

        print("="*70)
        print("ДЕПЛОЙ ЗАВЕРШЕН")
        print("="*70)
        print("""
НОВАЯ ЛОГИКА РАСПРЕДЕЛЕНИЯ:
- Зарплата (RUB/BYN) → Основные
- Зарплата (USDT) → USDT Зарплаты
- Прочее (RUB/BYN) → Разные выплаты
- Прочее (USDT) → USDT

ВАЖНО:
1. Перед тестированием создайте лист "USDT Зарплаты":
   python Scripts/create_usdt_salaries_sheet.py

2. Протестируйте все 4 сценария:
   - Зарплата в RUB → Основные
   - Зарплата в USDT → USDT Зарплаты
   - Доставка в RUB → Разные выплаты
   - Оплата сервиса в USDT → USDT
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_sheet_logic()
