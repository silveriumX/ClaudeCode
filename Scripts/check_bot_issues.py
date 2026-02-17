"""
Диагностика проблем Finance Bot
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

def diagnose_issues():
    """Проверить логи и код на наличие проблем"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ДИАГНОСТИКА ПРОБЛЕМ FINANCE BOT ===\n")

        # 1. Последние логи (больше строк для контекста)
        print("1. Последние 50 строк логов:\n")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 50 --no-pager")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        # 2. Ошибки и исключения
        print("\n" + "="*70)
        print("2. Ошибки и исключения в логах (последние 20):\n")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 100 --no-pager | grep -i 'error\\|exception\\|traceback\\|failed' | tail -20")
        errors = stdout.read().decode('utf-8', errors='replace')
        if errors.strip():
            print(errors)
        else:
            print("   Ошибок не найдено")

        # 3. Проверка callback handlers
        print("\n" + "="*70)
        print("3. Проверка callback handlers в bot.py:\n")

        # Проверяем все handlers с pattern
        stdin, stdout, stderr = ssh.exec_command("grep -n 'CallbackQueryHandler' /root/finance_bot/bot.py | grep pattern")
        handlers = stdout.read().decode('utf-8', errors='replace')
        print(handlers if handlers.strip() else "   Handlers не найдены")

        # 4. Проверка функции my_requests в handlers/request.py
        print("\n" + "="*70)
        print("4. Проверка фильтра статусов в my_requests():\n")

        # Ищем строку где фильтруются статусы
        stdin, stdout, stderr = ssh.exec_command("grep -A 5 'get_requests_by_status' /root/finance_bot/handlers/request.py | head -15")
        status_filter = stdout.read().decode('utf-8', errors='replace')
        print(status_filter if status_filter.strip() else "   Функция не найдена")

        # 5. Проверка ConversationHandler для создания заявки
        print("\n" + "="*70)
        print("5. Проверка states в ConversationHandler для создания заявки:\n")

        stdin, stdout, stderr = ssh.exec_command("grep -B 2 -A 10 'states.*REQUEST_DATE' /root/finance_bot/handlers/request.py | head -30")
        conv_states = stdout.read().decode('utf-8', errors='replace')
        print(conv_states if conv_states.strip() else "   States не найдены")

        # 6. Проверка bot.log если он есть
        print("\n" + "="*70)
        print("6. Проверка bot.log (если есть - последние 30 строк):\n")

        stdin, stdout, stderr = ssh.exec_command("tail -n 30 /root/finance_bot/bot.log 2>/dev/null")
        bot_log = stdout.read().decode('utf-8', errors='replace')
        if bot_log.strip():
            print(bot_log)
        else:
            print("   bot.log не найден или пуст")

        ssh.close()

        print("\n" + "="*70)
        print("РЕКОМЕНДАЦИИ:")
        print("1. Проверьте логи выше на наличие Traceback или ERROR")
        print("2. Попробуйте создать заявку в Telegram и сразу проверьте логи")
        print("3. Проверьте что в Google Sheets есть заявки со статусами 'Создана' или 'Оплачена'")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_issues()
