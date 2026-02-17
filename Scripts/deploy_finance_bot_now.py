"""
Деплой Finance Bot на VPS - только обновленные файлы для "Мои заявки"
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko
import os
import sys
from pathlib import Path
from datetime import datetime

# Исправление кодировки для Windows консоли
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# VPS данные
VPS_HOST = os.getenv("VPS_LINUX_HOST")
VPS_USER = 'root'
VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD")
VPS_PROJECT_PATH = '/root/finance_bot'

# Локальные файлы для загрузки
BASE_DIR = Path(r'C:\Users\Admin\Documents\Cursor\Projects\FinanceBot')
FILES_TO_UPLOAD = [
    'bot.py',
    'sheets.py',
    'handlers/request.py',
    'handlers/menu.py',
    'handlers/payment.py',
    'handlers/edit_handlers.py'
]

def execute_ssh_command(ssh_client, command, description=""):
    """Выполнить SSH команду и вернуть результат"""
    print(f"\n{'='*60}")
    if description:
        print(f"[*] {description}")
    print(f"[>] Команда: {command}")
    print(f"{'='*60}")

    stdin, stdout, stderr = ssh_client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if output:
        print(f"[OK] Вывод:\n{output}")
    if error:
        print(f"[!] Ошибки:\n{error}")

    return exit_status, output, error

def main():
    print("[START] Начало деплоя Finance Bot на VPS")
    print(f"[INFO] Целевой сервер: {VPS_USER}@{VPS_HOST}")
    print(f"[INFO] Директория: {VPS_PROJECT_PATH}")

    # Создаём SSH клиент
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Подключение к VPS
        print(f"\n[CONNECT] Подключение к VPS...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[OK] Подключение установлено")

        # 1. Создание backup текущих файлов
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_commands = [
            f"cp {VPS_PROJECT_PATH}/bot.py {VPS_PROJECT_PATH}/bot.py.backup_{timestamp}",
            f"cp {VPS_PROJECT_PATH}/sheets.py {VPS_PROJECT_PATH}/sheets.py.backup_{timestamp}",
            f"cp {VPS_PROJECT_PATH}/handlers/request.py {VPS_PROJECT_PATH}/handlers/request.py.backup_{timestamp}"
        ]

        for cmd in backup_commands:
            execute_ssh_command(ssh, cmd, f"Backup: {cmd.split('/')[-1]}")

        print("\n[OK] Backup создан")

        # 2. Загрузка файлов через SFTP
        print(f"\n{'='*60}")
        print("[UPLOAD] Загрузка обновленных файлов")
        print(f"{'='*60}")

        sftp = ssh.open_sftp()

        uploaded_count = 0
        for file_path in FILES_TO_UPLOAD:
            local_file = BASE_DIR / file_path
            remote_file = f"{VPS_PROJECT_PATH}/{file_path}"

            if not local_file.exists():
                print(f"[ERROR] Локальный файл не найден: {local_file}")
                continue

            try:
                print(f"[UPLOAD] Загружаю: {file_path}")
                sftp.put(str(local_file), remote_file)
                print(f"[OK] Загружено: {file_path}")
                uploaded_count += 1
            except Exception as e:
                print(f"[ERROR] Ошибка загрузки {file_path}: {e}")

        sftp.close()
        print(f"\n[OK] Загружено файлов: {uploaded_count}/{len(FILES_TO_UPLOAD)}")

        # 3. Остановка бота
        print(f"\n{'='*60}")
        print("[STOP] Остановка текущего бота")
        print(f"{'='*60}")

        execute_ssh_command(
            ssh,
            "pkill -f 'python.*finance_bot/bot.py' || pkill -f 'python3.*finance_bot/bot.py'",
            "Остановка процесса бота"
        )

        # Подождём 3 секунды
        import time
        print("[WAIT] Ожидание 3 секунды...")
        time.sleep(3)

        # 4. Запуск бота
        execute_ssh_command(
            ssh,
            f"cd {VPS_PROJECT_PATH} && nohup python3 bot.py > bot.log 2>&1 &",
            "Запуск бота"
        )

        # Подождём 3 секунды для запуска
        print("[WAIT] Ожидание запуска бота...")
        time.sleep(3)

        # 5. Проверка что бот запущен
        status, output, error = execute_ssh_command(
            ssh,
            "ps aux | grep 'finance_bot/bot.py' | grep -v grep",
            "Проверка: процесс бота запущен?"
        )

        is_running = 'finance_bot/bot.py' in output

        # 6. Проверка логов
        print(f"\n{'='*60}")
        print("[LOGS] Последние 30 строк логов")
        print(f"{'='*60}")

        log_status, log_output, log_error = execute_ssh_command(
            ssh,
            f"tail -30 {VPS_PROJECT_PATH}/bot.log",
            "Чтение логов бота"
        )

        # Анализ логов на наличие ошибок
        print(f"\n{'='*60}")
        print("[REPORT] ФИНАЛЬНЫЙ ОТЧЕТ")
        print(f"{'='*60}")

        has_errors = False
        if 'error' in log_output.lower() or 'exception' in log_output.lower() or 'traceback' in log_output.lower():
            has_errors = True
            print("[ERROR] В логах обнаружены ошибки!")
            print("\n[CHECK] Критические строки:")
            for line in log_output.split('\n'):
                if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'traceback']):
                    print(f"   {line}")
        else:
            print("[OK] Ошибок в логах не обнаружено")

        print(f"\n{'='*60}")
        if has_errors or not is_running:
            print("[WARNING] Деплой завершен с проблемами. См. детали выше.")
        else:
            print("[SUCCESS] Деплой успешно завершен!")
        print(f"{'='*60}")

        # Итоговая сводка
        print("\n[SUMMARY] СВОДКА:")
        print(f"   * Backup создан: {timestamp}")
        print(f"   * Файлов загружено: {uploaded_count}/{len(FILES_TO_UPLOAD)}")
        print(f"   * Бот перезапущен: Да")
        print(f"   * Статус бота: {'[OK] Работает' if is_running else '[ERROR] Не работает'}")
        print(f"   * Ошибки в логах: {'[ERROR] Есть' if has_errors else '[OK] Нет'}")

        return 0 if (is_running and not has_errors) else 1

    except Exception as e:
        print(f"\n[CRITICAL] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        ssh.close()
        print("\n[CLOSE] Соединение закрыто")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
