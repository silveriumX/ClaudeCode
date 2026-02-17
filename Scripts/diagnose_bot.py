"""
Диагностика Finance Bot - проверка дублей процессов
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

def diagnose():
    """Полная диагностика бота"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ДИАГНОСТИКА FINANCE BOT ===\n")

        # 1. Количество процессов bot.py
        print("1. Проверка процессов bot.py:")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep bot.py | grep -v grep")
        processes = stdout.read().decode('utf-8', errors='replace')
        process_count = len([line for line in processes.split('\n') if line.strip()])

        print(f"Найдено процессов: {process_count}")
        if process_count == 0:
            print("   СТАТУС: Бот НЕ ЗАПУЩЕН")
        elif process_count == 1:
            print("   СТАТУС: OK (один процесс)")
        else:
            print(f"   СТАТУС: ПРОБЛЕМА! Найдено {process_count} дублей")

        if processes.strip():
            print("\nПроцессы:")
            print(processes)

        # 2. Статус systemd
        print("\n2. Статус systemd service:")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"   Статус: {status}")

        # 3. Последние ошибки в логах
        print("\n3. Последние ошибки в логах:")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 30 --no-pager | grep -i 'error\\|conflict\\|exception' | tail -10")
        errors = stdout.read().decode('utf-8', errors='replace')
        if errors.strip():
            print(errors)
        else:
            print("   Ошибок не найдено")

        # 4. Git статус
        print("\n4. Git статус:")
        stdin, stdout, stderr = ssh.exec_command("cd /root/FinanceBot && git log -1 --oneline")
        git_info = stdout.read().decode('utf-8', errors='replace').strip()
        print(f"   Последний коммит: {git_info}")

        stdin, stdout, stderr = ssh.exec_command("cd /root/FinanceBot && git status --short")
        git_status = stdout.read().decode('utf-8', errors='replace').strip()
        if git_status:
            print(f"   Изменения: {git_status}")
        else:
            print("   Изменений нет (clean)")

        ssh.close()

        # Итоговая рекомендация
        print("\n=== РЕКОМЕНДАЦИЯ ===")
        if process_count > 1:
            print("ТРЕБУЕТСЯ ДЕЙСТВИЕ: Убить все процессы и перезапустить бота!")
            print("\nКоманды:")
            print("  pkill -f 'python.*bot.py'")
            print("  sleep 3")
            print("  systemctl restart finance_bot")
        elif process_count == 0:
            print("ТРЕБУЕТСЯ ДЕЙСТВИЕ: Запустить бота!")
            print("\nКоманда:")
            print("  systemctl start finance_bot")
        else:
            print("Процесс работает, но проверьте логи на наличие ошибок")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()
