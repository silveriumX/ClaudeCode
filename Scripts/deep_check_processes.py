"""
Глубокая проверка всех процессов бота на VPS
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

def deep_check():
    """Глубокая проверка процессов"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ГЛУБОКАЯ ПРОВЕРКА ПРОЦЕССОВ ===\n")

        # 1. ВСЕ процессы с bot.py
        print("1. ВСЕ процессы bot.py на сервере:\n")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'bot.py' | grep -v grep")
        all_bots = stdout.read().decode('utf-8', errors='replace')
        print(all_bots if all_bots.strip() else "   Процессов не найдено\n")

        # 2. Конкретно finance_bot процессы
        print("\n2. Процессы Finance Bot (/root/finance_bot/):\n")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '/root/finance_bot/bot.py' | grep -v grep")
        finance_bots = stdout.read().decode('utf-8', errors='replace')

        if finance_bots.strip():
            count = len([line for line in finance_bots.split('\n') if line.strip()])
            print(f"Найдено процессов: {count}\n")
            print(finance_bots)
        else:
            print("   Finance Bot НЕ ЗАПУЩЕН!\n")

        # 3. Проверка на токен бота в других местах
        print("\n3. Поиск других мест с токеном бота (возможные дубли):\n")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '8094294100' | grep -v grep")
        token_processes = stdout.read().decode('utf-8', errors='replace')
        print(token_processes if token_processes.strip() else "   Процессов с токеном не найдено\n")

        # 4. Systemd статус
        print("\n4. Systemd статус:\n")
        stdin, stdout, stderr = ssh.exec_command("systemctl status finance_bot --no-pager -l")
        systemd_status = stdout.read().decode('utf-8', errors='replace')
        print(systemd_status[:1000] if systemd_status else "   Статус недоступен\n")

        # 5. Проверка других ботов которые могут конфликтовать
        print("\n" + "="*70)
        print("5. Проверка других Python ботов на сервере:\n")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'python.*bot' | grep -v grep | grep -v finance_bot")
        other_bots = stdout.read().decode('utf-8', errors='replace')
        if other_bots.strip():
            print(other_bots)
        else:
            print("   Других ботов не найдено\n")

        ssh.close()

        print("\n" + "="*70)
        print("ДЕЙСТВИЯ:")
        print("1. Убить ВСЕ процессы finance_bot")
        print("2. Подождать 5 секунд")
        print("3. Запустить ТОЛЬКО через systemd")
        print("4. Убедиться что запущен ОДИН процесс")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deep_check()
