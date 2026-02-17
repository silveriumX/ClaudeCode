"""
Скрипт для деплоя Finance Bot на VPS
Загружает файлы через SFTP и выполняет команды
"""
import paramiko
import os
import sys
import getpass
from pathlib import Path

# Данные VPS
VPS_IP = "45.12.72.147"
VPS_USER = "root"
VPS_PROJECT_PATH = "/root/finance_bot"

# Запрос пароля
VPS_PASSWORD = os.getenv("VPS_PASSWORD") or getpass.getpass("Введите пароль VPS: ")

# Локальная директория
LOCAL_PROJECT = Path(r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot")

# Файлы для загрузки
FILES_TO_UPLOAD = [
    ("sheets.py", "sheets.py"),
    ("handlers/request.py", "handlers/request.py"),
    ("handlers/start.py", "handlers/start.py"),
    ("config.py", "config.py")
]

def connect_ssh(ip: str, username: str, password: str):
    """Подключение к VPS по SSH"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"🔌 Подключаюсь к {ip}...")
    client.connect(ip, username=username, password=password)
    print("✅ Подключено!")

    return client

def upload_file(sftp, local_path: Path, remote_path: str):
    """Загрузить файл через SFTP"""
    print(f"📤 Загружаю {local_path.name}...")
    try:
        sftp.put(str(local_path), remote_path)
        print(f"✅ {local_path.name} загружен")
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки {local_path.name}: {e}")
        return False

def execute_command(ssh_client, command: str):
    """Выполнить команду на VPS"""
    print(f"⚙️ Выполняю: {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command)

    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if output:
        print(output)
    if error:
        print(f"⚠️ {error}")

    return stdout.channel.recv_exit_status()

def main():
    try:
        # Подключение
        ssh_client = connect_ssh(VPS_IP, VPS_USER, VPS_PASSWORD)
        sftp = ssh_client.open_sftp()

        # Загрузка файлов
        print("\n📦 Загрузка файлов...")
        for local_file, remote_file in FILES_TO_UPLOAD:
            local_path = LOCAL_PROJECT / local_file
            remote_path = f"{VPS_PROJECT_PATH}/{remote_file}"

            if not local_path.exists():
                print(f"⚠️ Файл не найден: {local_path}")
                continue

            upload_file(sftp, local_path, remote_path)

        sftp.close()

        # Перезапуск бота
        print("\n🔄 Перезапуск бота...")
        execute_command(ssh_client, "systemctl restart financebot")

        print("\n⏳ Ожидание запуска...")
        import time
        time.sleep(3)

        # Проверка статуса
        print("\n📊 Проверка статуса...")
        execute_command(ssh_client, "systemctl status financebot")

        # Проверка логов
        print("\n📋 Последние логи:")
        execute_command(ssh_client, "journalctl -u financebot -n 50 --no-pager")

        ssh_client.close()

        print("\n✅ Деплой завершен!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
