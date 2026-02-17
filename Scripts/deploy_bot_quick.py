"""
Быстрое исправление Finance Bot - убивает дубли и перезапускает
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import sys
import time

# Фикс кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def fix_bot():
    """Убить дубли и перезапустить бота"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ИСПРАВЛЕНИЕ FINANCE BOT ===\n")

        # 1. Остановить все процессы finance_bot (только finance_bot!)
        print("1. Остановка всех процессов finance_bot...")
        commands = [
            # Убиваем только процессы из /root/finance_bot/
            "pkill -f '/root/finance_bot/bot.py' || true",
            "sleep 2",
            # Проверяем что не осталось
            "ps aux | grep '/root/finance_bot/bot.py' | grep -v grep || echo 'Процессов не найдено'"
        ]

        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='replace')
            if output.strip():
                print(f"   {output.strip()}")

        print("   OK: Процессы остановлены\n")

        # 2. Обновить код из git
        print("2. Обновление кода из git...")
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && git pull origin main")
        git_output = stdout.read().decode('utf-8', errors='replace')
        git_error = stderr.read().decode('utf-8', errors='replace')

        if "Already up to date" in git_output or "Already up-to-date" in git_output:
            print("   Код актуален (Already up to date)")
        elif git_output.strip():
            print(f"   {git_output.strip()}")

        if git_error.strip() and "Already up" not in git_error:
            print(f"   Git stderr: {git_error.strip()}")

        # Показать последний коммит
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && git log -1 --oneline")
        commit = stdout.read().decode('utf-8', errors='replace').strip()
        print(f"   Последний коммит: {commit}\n")

        # 3. Запустить бота через systemd
        print("3. Запуск бота через systemd...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot")
        time.sleep(3)  # Даём время на запуск

        # 4. Проверка статуса
        print("\n4. Проверка статуса...\n")

        # Статус systemd
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"   Systemd статус: {status}")

        # Количество процессов
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '/root/finance_bot/bot.py' | grep -v grep | wc -l")
        process_count = int(stdout.read().decode().strip() or 0)
        print(f"   Процессов bot.py: {process_count}")

        if process_count == 1:
            print("   ✓ OK: Запущен ОДИН процесс\n")
        elif process_count == 0:
            print("   ✗ ПРОБЛЕМА: Бот НЕ запущен!\n")
        else:
            print(f"   ✗ ПРОБЛЕМА: Запущено {process_count} процессов (дубли)\n")

        # 5. Последние логи
        print("5. Последние логи (15 строк):")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 15 --no-pager")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        # 6. Проверка на ошибки
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 30 --no-pager | grep -i 'error\\|conflict' | tail -5")
        errors = stdout.read().decode('utf-8', errors='replace').strip()

        print("\n=== ИТОГ ===")
        if process_count == 1 and status == "active" and not errors:
            print("✓ Бот успешно запущен и работает")
            print("✓ Дублей нет")
            print("✓ Ошибок нет")
        elif errors:
            print(f"⚠ Бот запущен, но есть ошибки:\n{errors}")
        else:
            print("⚠ Требуется дополнительная проверка")

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_bot()
