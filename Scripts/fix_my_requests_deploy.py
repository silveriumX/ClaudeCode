"""
Быстрый деплой исправления sheets.py на VPS
Исправляет ошибку "Мои заявки"
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import os
from pathlib import Path

# VPS данные
VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")
VPS_PATH = "/root/finance_bot"

# Локальный путь
LOCAL_FILE = Path("C:/Users/Admin/Documents/Cursor/Projects/FinanceBot/sheets.py")

def deploy_fix():
    """Загрузить исправленный sheets.py и перезапустить бота"""
    print("=== Деплой исправления 'Мои заявки' ===")

    if not LOCAL_FILE.exists():
        print(f"ERROR: Файл не найден: {LOCAL_FILE}")
        return False

    try:
        # Подключение к VPS
        print(f"\n1. Подключение к VPS {VPS_HOST}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)
        print("   OK: Подключено")

        # Создание backup
        print("\n2. Создание backup...")
        backup_cmd = f"cp {VPS_PATH}/sheets.py {VPS_PATH}/sheets.py.backup_$(date +%Y%m%d_%H%M%S)"
        stdin, stdout, stderr = ssh.exec_command(backup_cmd)
        stdout.channel.recv_exit_status()
        print("   OK: Backup создан")

        # Загрузка файла
        print("\n3. Загрузка исправленного sheets.py...")
        sftp = ssh.open_sftp()
        sftp.put(str(LOCAL_FILE), f"{VPS_PATH}/sheets.py")
        sftp.close()
        print("   OK: Файл загружен")

        # Проверка синтаксиса
        print("\n4. Проверка синтаксиса Python...")
        check_cmd = f"cd {VPS_PATH} && python3 -m py_compile sheets.py"
        stdin, stdout, stderr = ssh.exec_command(check_cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            error = stderr.read().decode()
            print(f"   ERROR: Синтаксическая ошибка!\n{error}")
            return False
        print("   OK: Синтаксис корректен")

        # Перезапуск бота
        print("\n5. Перезапуск Finance Bot...")
        restart_cmd = "systemctl restart finance_bot"
        stdin, stdout, stderr = ssh.exec_command(restart_cmd)
        stdout.channel.recv_exit_status()
        print("   OK: Бот перезапущен")

        # Проверка статуса
        print("\n6. Проверка статуса...")
        status_cmd = "systemctl is-active finance_bot"
        stdin, stdout, stderr = ssh.exec_command(status_cmd)
        status = stdout.read().decode().strip()

        if status == "active":
            print("   ✓ OK: Бот работает!")
        else:
            print(f"   WARNING: Статус бота: {status}")
            # Показать последние логи
            print("\n   Последние 10 строк логов:")
            logs_cmd = "journalctl -u finance_bot -n 10 --no-pager"
            stdin, stdout, stderr = ssh.exec_command(logs_cmd)
            logs = stdout.read().decode()
            print(logs)

        ssh.close()

        print("\n=== ДЕПЛОЙ ЗАВЕРШЁН ===")
        print("\nИсправление применено:")
        print("- Удалён дубликат метода get_requests_by_status")
        print("- Теперь используется правильная версия с get_all_values()")
        print("\nПротестируйте кнопку '📋 Мои заявки' в боте!")

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    deploy_fix()
