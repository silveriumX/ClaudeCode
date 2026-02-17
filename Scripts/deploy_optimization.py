"""
Деплой оптимизированного кода на сервер
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

def deploy_optimization():
    """Загрузить оптимизированный код на сервер"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДЕПЛОЙ ОПТИМИЗИРОВАННОГО КОДА")
        print("="*70 + "\n")

        # Создаём папку utils на сервере если её нет
        print("1. Создание структуры папок...")
        ssh.exec_command("mkdir -p /root/finance_bot/utils")
        print("   OK: mkdir utils\n")

        # Загружаем файлы через SFTP
        sftp = ssh.open_sftp()

        files_to_upload = [
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\utils\formatters.py",
             "/root/finance_bot/utils/formatters.py"),
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\sheets.py",
             "/root/finance_bot/sheets.py"),
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\handlers\request.py",
             "/root/finance_bot/handlers/request.py"),
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\handlers\payment.py",
             "/root/finance_bot/handlers/payment.py"),
            (r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\handlers\edit_handlers.py",
             "/root/finance_bot/handlers/edit_handlers.py"),
        ]

        print("2. Загрузка файлов...")
        for local, remote in files_to_upload:
            print(f"   Uploading {local.split('\\')[-1]}...")
            sftp.put(local, remote)

        print("   OK: Все файлы загружены\n")

        sftp.close()

        # Проверяем что utils/__init__.py существует на сервере
        print("3. Проверка utils/__init__.py...")
        stdin, stdout, stderr = ssh.exec_command("[ -f /root/finance_bot/utils/__init__.py ] && echo 'EXISTS' || echo 'NOT_EXISTS'")
        result = stdout.read().decode().strip()

        if result == 'NOT_EXISTS':
            print("   Creating utils/__init__.py...")
            ssh.exec_command("touch /root/finance_bot/utils/__init__.py")
        else:
            print("   OK: utils/__init__.py exists")

        # Перезапускаем бота
        print("\n4. Перезапуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot")
        stdout.read()

        import time
        time.sleep(3)

        # Проверяем статус
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()

        if status == "active":
            print(f"   OK: Бот запущен ({status})\n")
        else:
            print(f"   ERROR: Бот не запустился ({status})\n")

            # Показываем логи при ошибке
            print("   Последние логи:")
            stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 20 --no-pager")
            logs = stdout.read().decode('utf-8', errors='replace')
            print(logs)

            ssh.close()
            return

        # Проверяем логи на наличие ошибок
        print("5. Проверка логов...")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u finance_bot -n 30 --no-pager | grep -E '(ERROR|Exception|Traceback)' || echo 'No errors found'"
        )
        log_check = stdout.read().decode('utf-8', errors='replace')
        print(f"   {log_check}\n")

        ssh.close()

        print("="*70)
        print("ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО")
        print("="*70)
        print("""
ПРОВЕРЬТЕ В TELEGRAM:
1. Создайте новую заявку (любая валюта)
2. Откройте "Мои заявки"
3. Откройте заявку и отредактируйте её
4. Отмените заявку
5. Проверьте что список "Мои заявки" пуст

Все функции должны работать как раньше!
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_optimization()
