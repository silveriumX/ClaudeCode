"""
Загрузка исправленных файлов на сервер и перезапуск бота
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

def deploy_fixes():
    """Загрузить исправленные файлы и перезапустить бота"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ЗАГРУЗКА ИСПРАВЛЕНИЙ НА СЕРВЕР ===\n")

        # Пути к файлам
        local_base = r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot"
        files_to_upload = [
            "handlers/request.py",
            "handlers/edit_handlers.py"
        ]

        # Загружаем файлы через SFTP
        sftp = ssh.open_sftp()

        for file_path in files_to_upload:
            local_file = os.path.join(local_base, file_path)
            remote_file = f"/root/finance_bot/{file_path}"

            print(f"Загрузка {file_path}...")
            try:
                sftp.put(local_file, remote_file)
                print(f"   ✓ OK\n")
            except Exception as e:
                print(f"   ✗ Ошибка: {e}\n")
                sftp.close()
                ssh.close()
                return False

        sftp.close()

        print("=" * 70)
        print("ПЕРЕЗАПУСК БОТА")
        print("=" * 70 + "\n")

        # Перезапускаем бота
        print("1. Остановка бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl stop finance_bot")
        stdout.read()
        print("   ✓ OK\n")

        import time
        time.sleep(2)

        print("2. Запуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl start finance_bot")
        stdout.read()
        print("   ✓ OK\n")

        time.sleep(3)

        # Проверяем статус
        print("3. Проверка статуса...\n")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"   Статус: {status}")

        if status == "active":
            print("   ✓ Бот работает\n")
        else:
            print("   ✗ Бот не запущен!\n")

        # Проверяем логи
        print("4. Последние логи:\n")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 10 --no-pager")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        ssh.close()

        print("\n" + "="*70)
        if status == "active":
            print("✓✓✓ ИСПРАВЛЕНИЯ ЗАГРУЖЕНЫ И БОТ ПЕРЕЗАПУЩЕН ✓✓✓")
            print("\nТеперь можно тестировать:")
            print("1. Откройте 'Мои заявки' в Telegram")
            print("2. Нажмите на заявку от 29.01.2026 (Арина)")
            print("3. Проверьте что показывается правильный статус (Создана, а не Отменена)")
        else:
            print("✗ ПРОБЛЕМА С ЗАПУСКОМ БОТА!")
            print("Проверьте логи выше")

        return status == "active"

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_fixes()
    sys.exit(0 if success else 1)
