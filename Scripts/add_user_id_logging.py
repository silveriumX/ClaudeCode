"""
Добавить временное логирование user_id при создании заявки
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

def add_user_id_logging():
    """Добавить логирование user_id"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДОБАВЛЕНИЕ ЛОГИРОВАНИЯ USER ID")
        print("="*70 + "\n")

        # Создаём патч для логирования
        patch_script = """
# Бэкап
cp /root/finance_bot/handlers/request.py /root/finance_bot/handlers/request.py.backup2

# Добавляем логирование перед строкой 268
sed -i '268i\\    logger = logging.getLogger(__name__)\\n    logger.error(f"[DEBUG_CREATE] user.id={user.id}, user.username={user.username}, user.full_name={user.full_name}")' /root/finance_bot/handlers/request.py

echo "Патч применён"
"""

        stdin, stdout, stderr = ssh.exec_command(patch_script)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)
        if error and 'echo' not in error:
            print(f"Stderr: {error}")

        # Проверяем патч
        print("\nПроверка патча (строки 266-272):")
        stdin, stdout, stderr = ssh.exec_command("sed -n '266,272p' /root/finance_bot/handlers/request.py")
        code = stdout.read().decode('utf-8', errors='replace')
        print(code)

        # Перезапускаем
        print("\nПерезапуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot && sleep 2 && systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"Статус: {status}")

        ssh.close()

        print("\n" + "="*70)
        print("ТЕПЕРЬ:")
        print("1. Создайте новую заявку в боте")
        print("2. Выполните: python Scripts\\check_create_logs.py")
        print("="*70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_user_id_logging()
