"""
Добавление debug логирования для отслеживания callbacks
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

def add_debug_logging():
    """Добавить debug логирование"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ДОБАВЛЕНИЕ DEBUG ЛОГИРОВАНИЯ ===\n")

        # Создаём патч для view_request_callback
        patch_script = """
# Создаём резервную копию
cp /root/finance_bot/handlers/request.py /root/finance_bot/handlers/request.py.backup

# Добавляем debug логирование в view_request_callback
sed -i '/async def view_request_callback/a\\    import logging\\n    logger = logging.getLogger(__name__)\\n    logger.error(f"[DEBUG] view_request_callback called with data: {update.callback_query.data}")' /root/finance_bot/handlers/request.py

# Добавляем debug логирование в cancel_request_callback
sed -i '/async def cancel_request_callback/a\\    import logging\\n    logger = logging.getLogger(__name__)\\n    logger.error(f"[DEBUG] cancel_request_callback called with data: {update.callback_query.data}")' /root/finance_bot/handlers/request.py

echo "Debug логирование добавлено"
"""

        print("Добавление debug логов...\n")
        stdin, stdout, stderr = ssh.exec_command(patch_script)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        if output:
            print(output)
        if error:
            print(f"Stderr: {error}")

        # Перезапускаем бота
        print("\nПерезапуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot")
        stdout.read()

        import time
        time.sleep(3)

        # Проверяем статус
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"Статус: {status}\n")

        ssh.close()

        print("="*70)
        print("✓ Debug логирование добавлено и бот перезапущен")
        print("\nТеперь:")
        print("1. Откройте 'Мои заявки' в Telegram")
        print("2. Нажмите на кнопку заявки")
        print("3. Выполните: python Scripts\\get_debug_logs.py")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_debug_logging()
