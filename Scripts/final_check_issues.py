"""
Финальная проверка и диагностика проблем
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

def final_check():
    """Финальная проверка после очистки"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ФИНАЛЬНАЯ ПРОВЕРКА ПОСЛЕ ОЧИСТКИ ===\n")

        # 1. Проверка что нет новых Conflict
        print("1. Проверка на новые Conflict ошибки:\n")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot --since '2 minutes ago' --no-pager | grep -i 'conflict' || echo 'Conflict ошибок НЕТ'")
        conflicts = stdout.read().decode('utf-8', errors='replace').strip()
        print(f"   {conflicts}\n")

        # 2. Последние логи
        print("2. Последние 15 строк логов:\n")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 15 --no-pager")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        # 3. Статус процессов
        print("\n3. Статус процессов:")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '/root/finance_bot/bot.py' | grep -v grep | wc -l")
        count = int(stdout.read().decode().strip() or 0)
        print(f"   Процессов Finance Bot: {count}")

        if count == 1:
            print("   ✓ OK\n")
        else:
            print(f"   ✗ ПРОБЛЕМА: {count} процессов\n")

        print("\n" + "="*70)
        print("ДИАГНОСТИКА ПРОБЛЕМ ПОЛЬЗОВАТЕЛЯ")
        print("="*70 + "\n")

        # Проблема 1: Зависание при выборе валюты
        print("ПРОБЛЕМА 1: Зависание при выборе валюты\n")
        print("Проверка ConversationHandler states:")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'REQUEST_CURRENCY' /root/finance_bot/handlers/request.py | head -5")
        currency_state = stdout.read().decode('utf-8', errors='replace')
        print(currency_state if currency_state.strip() else "   State REQUEST_CURRENCY не найден")

        print("\nПроверка callback для валюты:")
        stdin, stdout, stderr = ssh.exec_command("grep -B 3 -A 10 'def request_currency' /root/finance_bot/handlers/request.py | head -20")
        currency_callback = stdout.read().decode('utf-8', errors='replace')
        print(currency_callback if currency_callback.strip() else "   Функция не найдена")

        # Проблема 2: Отображается только одна заявка (отменена)
        print("\n" + "="*70)
        print("ПРОБЛЕМА 2: Только одна заявка (отменена)\n")
        print("Проверка фильтра статусов:")
        stdin, stdout, stderr = ssh.exec_command("grep -B 2 -A 8 'STATUS_CREATED\\|STATUS_PAID' /root/finance_bot/handlers/request.py | grep -A 5 'my_requests' | head -15")
        status_check = stdout.read().decode('utf-8', errors='replace')
        print(status_check if status_check.strip() else "   Фильтр не найден")

        print("\nПроверка config.py (статусы):")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'STATUS_' /root/finance_bot/config.py")
        config_status = stdout.read().decode('utf-8', errors='replace')
        print(config_status if config_status.strip() else "   Константы статусов не найдены")

        # Проблема 3: Кнопка "Назад к списку" не работает
        print("\n" + "="*70)
        print("ПРОБЛЕМА 3: Кнопка 'Назад к списку' не работает\n")
        print("Проверка callback back_to_list:")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'def back_to_list_callback' /root/finance_bot/handlers/request.py")
        back_callback = stdout.read().decode('utf-8', errors='replace')
        print(back_callback if back_callback.strip() else "   Функция не найдена")

        print("\nПроверка handler в bot.py:")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'back_to_list' /root/finance_bot/bot.py")
        back_handler = stdout.read().decode('utf-8', errors='replace')
        print(back_handler if back_handler.strip() else "   Handler не найден")

        print("\nПроверка callback_data в кнопке:")
        stdin, stdout, stderr = ssh.exec_command("grep -B 5 -A 5 'Назад к списку' /root/finance_bot/handlers/request.py | grep -A 3 'InlineKeyboardButton'")
        button_data = stdout.read().decode('utf-8', errors='replace')
        print(button_data if button_data.strip() else "   Кнопка не найдена")

        ssh.close()

        print("\n" + "="*70)
        print("РЕКОМЕНДАЦИИ:")
        print("1. Бот должен работать без Conflict ошибок")
        print("2. Проверьте код выше на наличие проблем в handlers")
        print("3. Возможно нужно посмотреть реальный код функций")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_check()
