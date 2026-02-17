"""
Проверка деплоя последнего обновления Finance Bot
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

def verify_deploy():
    """Проверить что последнее обновление было развернуто"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== ПРОВЕРКА ДЕПЛОЯ ОБНОВЛЕНИЯ ОТ 30.01.2026 ===\n")

        # 1. Проверка git
        print("1. Проверка git-репозитория:")
        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && pwd")
        pwd = stdout.read().decode().strip()
        print(f"   Рабочая директория: {pwd}")

        stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && ls -la | grep '.git'")
        git_check = stdout.read().decode().strip()
        if git_check:
            print(f"   Git репозиторий: Найден")

            stdin, stdout, stderr = ssh.exec_command("cd /root/finance_bot && git log -1 --pretty=format:'%h - %s (%cd)' --date=format:'%d.%m.%Y %H:%M'")
            commit = stdout.read().decode('utf-8', errors='replace').strip()
            print(f"   Последний коммит: {commit}")
        else:
            print("   Git репозиторий: НЕ НАЙДЕН (код может быть скопирован напрямую)\n")

        # 2. Проверка изменений в handlers/request.py
        print("\n2. Проверка изменений в handlers/request.py:")

        # Проверяем наличие функции parse_date
        stdin, stdout, stderr = ssh.exec_command("grep -n 'def parse_date' /root/finance_bot/handlers/request.py")
        parse_date = stdout.read().decode('utf-8', errors='replace').strip()
        if parse_date:
            print(f"   ✓ Функция parse_date(): НАЙДЕНА (строка {parse_date.split(':')[0]})")
        else:
            print("   ✗ Функция parse_date(): НЕ НАЙДЕНА")

        # Проверяем наличие функции my_requests_navigation_callback
        stdin, stdout, stderr = ssh.exec_command("grep -n 'def my_requests_navigation_callback' /root/finance_bot/handlers/request.py")
        navigation = stdout.read().decode('utf-8', errors='replace').strip()
        if navigation:
            print(f"   ✓ Функция my_requests_navigation_callback(): НАЙДЕНА (строка {navigation.split(':')[0]})")
        else:
            print("   ✗ Функция my_requests_navigation_callback(): НЕ НАЙДЕНА")

        # Проверяем импорт datetime
        stdin, stdout, stderr = ssh.exec_command("grep -n 'from datetime import datetime' /root/finance_bot/handlers/request.py")
        datetime_import = stdout.read().decode('utf-8', errors='replace').strip()
        if datetime_import:
            print(f"   ✓ Импорт datetime: НАЙДЕН (строка {datetime_import.split(':')[0]})")
        else:
            print("   ✗ Импорт datetime: НЕ НАЙДЕН")

        # 3. Проверка bot.py на наличие handler для навигации
        print("\n3. Проверка bot.py:")

        stdin, stdout, stderr = ssh.exec_command("grep -n 'my_requests_navigation_callback' /root/finance_bot/bot.py")
        bot_handler = stdout.read().decode('utf-8', errors='replace').strip()
        if bot_handler:
            print(f"   ✓ Handler my_requests_navigation_callback: НАЙДЕН")
            print(f"      {bot_handler}")
        else:
            print("   ✗ Handler my_requests_navigation_callback: НЕ НАЙДЕН")

        # 4. Проверка паттерна back_to_list
        stdin, stdout, stderr = ssh.exec_command("grep -n \"pattern=.*back_to_list\" /root/finance_bot/bot.py")
        back_pattern = stdout.read().decode('utf-8', errors='replace').strip()
        if back_pattern:
            print(f"\n   ✓ Pattern для back_to_list: НАЙДЕН")
            for line in back_pattern.split('\n'):
                print(f"      {line}")
        else:
            print("\n   ✗ Pattern для back_to_list: НЕ НАЙДЕН")

        # 5. Проверка sheets.py (должны быть удалены print)
        print("\n4. Проверка sheets.py (отладочные print должны быть удалены):")
        stdin, stdout, stderr = ssh.exec_command("grep -n 'print(' /root/finance_bot/sheets.py | grep -v '#' | head -5")
        prints = stdout.read().decode('utf-8', errors='replace').strip()
        if prints:
            print("   ⚠ Найдены print() в коде:")
            for line in prints.split('\n'):
                print(f"      {line}")
        else:
            print("   ✓ Отладочные print() удалены (или закомментированы)")

        # 6. Проверка формата кнопок в коде
        print("\n5. Проверка формата кнопок (должен быть формат: дата • сумма • получатель):")
        stdin, stdout, stderr = ssh.exec_command("grep -n '•' /root/finance_bot/handlers/request.py | head -3")
        button_format = stdout.read().decode('utf-8', errors='replace').strip()
        if button_format and '•' in button_format:
            print("   ✓ Новый формат кнопок (с •) НАЙДЕН")
        else:
            print("   ✗ Новый формат кнопок НЕ НАЙДЕН (возможно используется старый формат с |)")

        ssh.close()

        print("\n=== ИТОГОВЫЙ CHECKLIST ===")
        print("\nФункции из обновления:")
        print(f"  [{'✓' if parse_date else '✗'}] parse_date() для сортировки по дате")
        print(f"  [{'✓' if navigation else '✗'}] my_requests_navigation_callback() для пагинации")
        print(f"  [{'✓' if datetime_import else '✗'}] Импорт datetime")
        print(f"  [{'✓' if bot_handler else '✗'}] Handler в bot.py для навигации")

        all_ok = parse_date and navigation and datetime_import and bot_handler

        print("\n" + "="*50)
        if all_ok:
            print("✓ ВСЕ ИЗМЕНЕНИЯ ИЗ ОБНОВЛЕНИЯ ПРИСУТСТВУЮТ В КОДЕ")
            print("\nСледующий шаг: Проверить в Telegram:")
            print("  1. Отправить /start боту")
            print("  2. Нажать '📋 Мои заявки'")
            print("  3. Проверить формат кнопок (дата • сумма • получатель)")
            print("  4. Проверить сортировку (новые заявки сверху)")
            print("  5. Если >10 заявок - проверить пагинацию")
        else:
            print("✗ ОБНАРУЖЕНЫ ОТСУТСТВУЮЩИЕ ИЗМЕНЕНИЯ")
            print("\nТребуется дополнительная диагностика или ручной деплой")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_deploy()
