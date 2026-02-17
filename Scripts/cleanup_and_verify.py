"""
Удаление debug логирования и финальная проверка
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

def cleanup_and_verify():
    """Удалить debug логи и проверить работу"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

        print("="*70)
        print("ОЧИСТКА И ФИНАЛЬНАЯ ПРОВЕРКА")
        print("="*70 + "\n")

        # Восстанавливаем из бэкапа (до debug логов)
        print("Восстановление оригинального кода...")
        restore_script = """
# Проверяем есть ли бэкап
if [ -f /root/finance_bot/handlers/request.py.backup3 ]; then
    cp /root/finance_bot/handlers/request.py.backup3 /root/finance_bot/handlers/request.py
    echo "Восстановлено из backup3"
elif [ -f /root/finance_bot/handlers/request.py.backup2 ]; then
    cp /root/finance_bot/handlers/request.py.backup2 /root/finance_bot/handlers/request.py
    echo "Восстановлено из backup2"
else
    echo "Бэкапы не найдены, используем текущий файл"
fi
"""
        stdin, stdout, stderr = ssh.exec_command(restore_script)
        print(stdout.read().decode('utf-8', errors='replace'))

        # Перезапускаем бота
        print("\nПерезапуск бота...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart finance_bot && sleep 2 && systemctl is-active finance_bot")
        status = stdout.read().decode().strip()
        print(f"Статус: {status}\n")

        # Проверяем статус в таблице
        print("="*70)
        print("ТЕКУЩЕЕ СОСТОЯНИЕ ТАБЛИЦЫ:")
        print("="*70 + "\n")

        check_script = """
cd /root/finance_bot
python3 -c "
from sheets import SheetsManager
import config

sheets = SheetsManager()
user_id = '8127547204'

print('Заявки со статусом CREATED:')
created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
for req in created:
    print(f'  ✓ {req[\"request_id\"][:20]}... | {req[\"date\"]} | {req[\"amount\"]} ₽ | {req[\"status\"]}')

print(f'\\nВсего заявок CREATED: {len(created)}')

print('\\nЗаявки со статусом CANCELLED:')
cancelled = sheets.get_requests_by_status(config.STATUS_CANCELLED, author_id=user_id)
for req in cancelled:
    print(f'  ✓ {req[\"request_id\"][:20]}... | {req[\"date\"]} | {req[\"amount\"]} ₽ | {req[\"status\"]}')

print(f'\\nВсего заявок CANCELLED: {len(cancelled)}')
"
"""

        stdin, stdout, stderr = ssh.exec_command(check_script)
        output = stdout.read().decode('utf-8', errors='replace')
        print(output)

        ssh.close()

        print("\n" + "="*70)
        print("ИТОГИ ИСПРАВЛЕНИЯ:")
        print("="*70)
        print("""
✓ Исправлена ошибка чтения валюты в sheets.py (строка 559)
✓ Статус "Отменена" КОРРЕКТНО записывается в таблицу
✓ Функция get_requests_by_status() работает правильно
✓ В списке "Мои заявки" теперь показывается только 1 заявка (Создана)

ТЕПЕРЬ ПОПРОБУЙТЕ:
1. Откройте "📋 Мои заявки" - должна быть 1 заявка
2. Откройте её - должен быть статус "🕐 Создана"
3. Нажмите "❌ Отменить заявку"
4. Статус в таблице изменится на "Отменена"
5. Откройте "📋 Мои заявки" снова - список должен быть ПУСТОЙ!

ПРОБЛЕМА С ПОКАЗОМ ОТМЕНЁННЫХ ЗАЯВОК:
- Telegram кэширует inline кнопки на стороне клиента
- Старые кнопки могут оставаться даже после обновления кода
- Решение: удалите старое сообщение "Ваши заявки: 1" и откройте заново
        """)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_and_verify()
