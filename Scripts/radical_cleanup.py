"""
Радикальная чистка всех процессов finance bot
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

def radical_cleanup():
    """Убить все процессы и чисто перезапустить"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("=== РАДИКАЛЬНАЯ ЧИСТКА FINANCE BOT ===\n")

        # 1. Остановить systemd service
        print("1. Остановка systemd service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl stop finance_bot")
        time.sleep(2)
        print("   OK\n")

        # 2. Убить ВСЕ старые процессы по PID
        print("2. Убийство ВСЕХ старых процессов...")
        old_pids = [421334, 421335, 421348, 422335, 422336, 422698, 422699, 422932, 422933]

        for pid in old_pids:
            stdin, stdout, stderr = ssh.exec_command(f"kill -9 {pid} 2>/dev/null || true")
            print(f"   Убит PID {pid}")

        time.sleep(2)
        print("\n3. Убийство всех процессов с именем bot.py в /root/finance_bot...")
        stdin, stdout, stderr = ssh.exec_command("pkill -9 -f '/root/finance_bot/bot.py' || true")
        time.sleep(2)

        # Дополнительно убиваем по имени файла
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'cd /root/finance_bot' | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true")
        time.sleep(1)
        print("   OK\n")

        # 4. Проверка что НЕТ процессов
        print("4. Проверка что процессов НЕТ...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'bot.py|finance_bot' | grep -v grep | grep -v 'media_download\\|voice_bot\\|universal_cursor'")
        remaining = stdout.read().decode('utf-8', errors='replace').strip()

        if remaining:
            print(f"   ⚠ Остались процессы:\n{remaining}\n")
        else:
            print("   ✓ Все процессы Finance Bot убиты\n")

        # 5. Запуск через systemd
        print("5. Запуск через systemd...")
        stdin, stdout, stderr = ssh.exec_command("systemctl start finance_bot")
        time.sleep(4)
        print("   OK\n")

        # 6. Финальная проверка
        print("6. Финальная проверка:\n")

        # Systemd статус
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"   Systemd статус: {status}")

        # Количество процессов
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '/root/finance_bot/bot.py' | grep -v grep | wc -l")
        count = int(stdout.read().decode().strip() or 0)
        print(f"   Процессов Finance Bot: {count}")

        if count == 1:
            print("   ✓ OK: ОДИН процесс\n")
        elif count == 0:
            print("   ✗ ОШИБКА: Процессов НЕТ\n")
        else:
            print(f"   ✗ ОШИБКА: {count} процессов (дубли)\n")

        # PID нового процесса
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep '/root/finance_bot/bot.py' | grep -v grep")
        process_info = stdout.read().decode('utf-8', errors='replace').strip()
        if process_info:
            print(f"   Процесс:\n   {process_info}\n")

        # 7. Проверка логов (ждём пару секунд для инициализации)
        print("7. Ожидание инициализации (5 сек)...")
        time.sleep(5)

        print("\n8. Последние логи:\n")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 20 --no-pager")
        logs = stdout.read().decode('utf-8', errors='replace')
        print(logs)

        # 9. Проверка на ошибки Conflict
        stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 50 --no-pager | grep -i 'conflict' | tail -5")
        conflicts = stdout.read().decode('utf-8', errors='replace').strip()

        print("\n" + "="*70)
        print("ИТОГ:")
        if count == 1 and status == "active" and not conflicts:
            print("✓✓✓ БОТ УСПЕШНО ЗАПУЩЕН БЕЗ КОНФЛИКТОВ ✓✓✓")
            print("\nТеперь можно тестировать функционал:")
            print("1. Создание заявки")
            print("2. Просмотр 'Мои заявки'")
            print("3. Кнопка 'Назад к списку'")
        elif conflicts:
            print("⚠ Бот запущен, но всё ещё есть Conflict!")
            print("Возможно нужно подождать ~30 секунд для очистки старых соединений")
            print("\nПоследние Conflict:")
            print(conflicts)
        else:
            print("✗ Проблема с запуском. Проверьте логи выше.")

        ssh.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    radical_cleanup()
