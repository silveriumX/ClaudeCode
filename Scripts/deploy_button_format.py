"""
Деплой обновлённого формата кнопок "Мои заявки"
Изменение: добавлены эмоджи статусов (⏳ для Создана, ✅ для Оплачена)
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")

def deploy_button_format():
    """Загрузить обновлённый handlers/request.py"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ДЕПЛОЙ: Обновление формата кнопок 'Мои заявки'")
        print("="*70 + "\n")

        # Загружаем обновлённый файл
        sftp = ssh.open_sftp()

        print("1. Загрузка handlers/request.py...")
        sftp.put(
            r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\handlers\request.py",
            "/root/finance_bot/handlers/request.py"
        )
        print("   OK: Файл загружен\n")

        sftp.close()

        # Перезапускаем бота
        print("2. Перезапуск бота...")
        ssh.exec_command("systemctl restart finance_bot")

        import time
        time.sleep(3)

        # Проверяем статус
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active finance_bot")
        status = stdout.read().decode().strip()

        if status == "active":
            print(f"   OK: Бот запущен ({status})\n")
        else:
            print(f"   ERROR: Бот не запустился ({status})\n")
            stdin, stdout, stderr = ssh.exec_command("journalctl -u finance_bot -n 20 --no-pager")
            print(stdout.read().decode('utf-8', errors='replace'))
            ssh.close()
            return

        # Проверяем логи
        print("3. Проверка логов...")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u finance_bot -n 10 --no-pager | grep -E '(ERROR|Exception)' || echo 'No errors'"
        )
        print(f"   {stdout.read().decode('utf-8', errors='replace')}\n")

        ssh.close()

        print("="*70)
        print("ДЕПЛОЙ ЗАВЕРШЕН")
        print("="*70)
        print("""
ИЗМЕНЕНИЯ:
- Формат кнопок: статус_эмоджи - дата - сумма - получатель
- Эмоджи: ⏳ (Создана), ✅ (Оплачена)

ПРОВЕРЬТЕ В TELEGRAM:
1. Откройте "Мои заявки"
2. Кнопки должны начинаться с эмоджи статуса
3. Формат: ⏳ - 30.01.2026 - 50 000 ₽ - Иван Иванов
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_button_format()
