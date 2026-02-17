"""
Деплой исправления sheets.py на сервер
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import sys
import os

# Фикс кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def deploy_sheets_fix():
    """Загрузить исправленный sheets.py и перезапустить бота"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ДЕПЛОЙ ИСПРАВЛЕНИЯ sheets.py ===\n")

        # Загружаем файл через SFTP
        sftp = ssh.open_sftp()

        local_file = r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\sheets.py"
        remote_file = "/root/finance_bot/sheets.py"

        print(f"Загрузка {local_file} -> {remote_file}...")
        sftp.put(local_file, remote_file)
        sftp.close()
        print("✓ Файл загружен\n")

        # Перезапускаем бота
        print("Перезапуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot")
        stdout.read()

        import time
        time.sleep(3)

        # Проверяем статус
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()

        if status == "active":
            print(f"✓ Бот запущен: {status}\n")
        else:
            print(f"✗ Ошибка запуска: {status}\n")

            # Показываем логи
            stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 15 --no-pager")
            logs = stdout.read().decode('utf-8', errors='replace')
            print("Последние логи:")
            print(logs)

        # Проверяем изменение в файле
        print("\nПроверка исправления в коде (строка 559):")
        stdin, stdout, stderr = ssh.exec_command("sed -n '558,560p' /root/finance_bot/sheets.py")
        code = stdout.read().decode('utf-8', errors='replace')
        print(code)

        if "row[3]" in code:
            print("\n✓ Исправление применено!")
        else:
            print("\n✗ Исправление НЕ применено")

        ssh.close()

        print("\n" + "="*70)
        print("ДЕПЛОЙ ЗАВЕРШЁН")
        print("\nТеперь попробуйте:")
        print("1. Открыть 'Мои заявки'")
        print("2. Нажать на кнопку заявки")
        print("3. Нажать 'Отменить заявку'")
        print("4. Проверить статус в таблице - должен стать 'Отменена'!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_sheets_fix()
