"""
Проверка handlers patterns в bot.py
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

def check_handlers():
    """Проверить handlers в bot.py"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА HANDLERS В BOT.PY ===\n")

        # Проверяем все handler patterns
        print("Все CallbackQueryHandler с pattern:\n")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'CallbackQueryHandler.*pattern=' /root/finance_bot/bot.py")
        patterns = stdout.read().decode('utf-8', errors='replace')
        print(patterns)

        print("\n" + "="*70)
        print("АНАЛИЗ:")
        print("Ищем pattern для view_req_")

        if 'view_req_' in patterns:
            print("✓ Найден pattern для view_req_")
            # Проверяем конкретный pattern
            stdin, stdout, stderr = ssh.exec_command("grep 'view_request_callback.*pattern' /root/finance_bot/bot.py")
            view_pattern = stdout.read().decode('utf-8', errors='replace')
            print(f"\nPattern: {view_pattern.strip() if view_pattern.strip() else 'НЕ НАЙДЕН'}")
        else:
            print("✗ Pattern для view_req_ НЕ НАЙДЕН!")

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_handlers()
