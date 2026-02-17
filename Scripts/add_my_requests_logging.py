"""
Добавить логирование user_id в my_requests
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

def add_my_requests_logging():
    """Добавить логирование в my_requests"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДОБАВЛЕНИЕ ЛОГИРОВАНИЯ В my_requests")
        print("="*70 + "\n")

        patch_script = """
# Бэкап
cp /root/finance_bot/handlers/request.py /root/finance_bot/handlers/request.py.backup3

# Добавляем логирование после строки 317 (user = update.effective_user)
sed -i '318i\\    import logging\\n    logger = logging.getLogger(__name__)\\n    logger.error(f"[DEBUG_MY_REQUESTS] user.id={user.id}, username={user.username}, full_name={user.full_name}")' /root/finance_bot/handlers/request.py

echo "Патч применён"
"""

        stdin, stdout, stderr = ssh.exec_command(patch_script)
        output = stdout.read().decode('utf-8', errors='replace')

        print(output)

        # Перезапускаем
        print("Перезапуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot && sleep 2 && systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"Статус: {status}\n")

        ssh.close()

        print("="*70)
        print("ТЕПЕРЬ:")
        print("1. Откройте 'Мои заявки' в боте")
        print("2. Выполните: python Scripts\\check_my_requests_logs.py")
        print("="*70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_my_requests_logging()
