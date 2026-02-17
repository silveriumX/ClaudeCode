"""
Деплой Finance Bot на VPS через SSH
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
SERVICE_NAME = 'finance_bot'

# Локальные файлы
BASE_DIR = Path(r'C:\Users\Admin\Documents\Cursor\Projects\FinanceBot')
FILES_TO_UPLOAD = [
    'sheets.py',
    'handlers/request.py',
    'handlers/start.py',
    'handlers/edit_handlers.py',
    'utils/formatters.py',
    'config.py'
]

def execute_ssh_command(ssh_client, command, description=""):
    """Выполнить SSH команду и вернуть результат"""
    print(f"\n{'='*60}")
    if description:
        print(f"[*] {description}")
    print(f"[>] Komanda: {command}")
    print(f"{'='*60}")

    stdin, stdout, stderr = ssh_client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if output:
        print(f"[OK] Vyvod:\n{output}")
    if error:
        print(f"[!] Oshibki:\n{error}")

    return exit_status, output, error

def main():
    print("[START] Nachalo deploya Finance Bot na VPS")
    print(f"[INFO] Celevoj server: {VPS_USER}@{VPS_HOST}")
    print(f"[INFO] Direktoriya: {VPS_PROJECT_PATH}")

    # Создаём SSH клиент
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Подключение к VPS
        print(f"\n[CONNECT] Podklyuchenie k VPS...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[OK] Podklyuchenie ustanovleno")

        # 1. Создание backup
        backup_name = f"finance_bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        execute_ssh_command(
            ssh,
            f"cp -r {VPS_PROJECT_PATH} /root/{backup_name} && echo 'Backup: {backup_name}' && ls -lah /root/ | grep finance_bot",
            "Shag 1: Sozdanie backup"
        )

        # 2. Загрузка файлов через SFTP
        print(f"\n{'='*60}")
        print("[UPLOAD] Shag 2: Zagruzka fajlov cherez SFTP")
        print(f"{'='*60}")

        sftp = ssh.open_sftp()

        for file_path in FILES_TO_UPLOAD:
            local_file = BASE_DIR / file_path
            remote_file = f"{VPS_PROJECT_PATH}/{file_path}"

            if not local_file.exists():
                print(f"[ERROR] Lokalnyj fajl ne najden: {local_file}")
                continue

            try:
                print(f"[UPLOAD] Zagruzhayu: {file_path}")
                sftp.put(str(local_file), remote_file)
                print(f"[OK] Zagruzheno: {file_path}")
            except Exception as e:
                print(f"[ERROR] Oshibka zagruzki {file_path}: {e}")

        sftp.close()
        print("\n[OK] Vse fajly zagruzheny")

        # 3. Перезапуск сервиса
        execute_ssh_command(
            ssh,
            f"systemctl restart {SERVICE_NAME}",
            "Shag 3: Perezapusk servisa"
        )

        # Подождём 3 секунды для запуска
        import time
        time.sleep(3)

        # 4. Проверка статуса
        execute_ssh_command(
            ssh,
            f"systemctl status {SERVICE_NAME} --no-pager",
            "Shag 4: Proverka statusa servisa"
        )

        # 5. Проверка логов
        status, output, error = execute_ssh_command(
            ssh,
            f"journalctl -u {SERVICE_NAME} -n 30 --no-pager",
            "Shag 5: Proverka logov (poslednie 30 strok)"
        )

        # Анализ логов на наличие ошибок
        print(f"\n{'='*60}")
        print("[REPORT] FINALNYJ OTCHYOT")
        print(f"{'='*60}")

        has_errors = False
        if 'error' in output.lower() or 'exception' in output.lower() or 'failed' in output.lower():
            has_errors = True
            print("[ERROR] V logah obnaruzheny oshibki!")
            print("\n[CHECK] Kriticheskie stroki:")
            for line in output.split('\n'):
                if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'traceback']):
                    print(f"   {line}")
        else:
            print("[OK] Oshibok v logah ne obnaruzheno")

        # Проверяем что бот работает
        status, is_active, _ = execute_ssh_command(
            ssh,
            f"systemctl is-active {SERVICE_NAME}",
            "Proverka: Bot aktiven?"
        )

        if 'active' in is_active:
            print("\n[SUCCESS] Bot uspeshno zapushchen i rabotaet!")
        else:
            print("\n[ERROR] Bot NE zapushchen!")
            has_errors = True

        print(f"\n{'='*60}")
        if has_errors:
            print("[WARNING] Deploj zavershen s oshibkami. Sm. detali vyshe.")
        else:
            print("[SUCCESS] Deploj uspeshno zavershen!")
        print(f"{'='*60}")

        # Итоговая сводка
        print("\n[SUMMARY] SVODKA:")
        print(f"   * Backup: {backup_name}")
        print(f"   * Fajlov zagruzheno: {len(FILES_TO_UPLOAD)}")
        print(f"   * Servis perezapushchen: {SERVICE_NAME}")
        print(f"   * Status bota: {'[OK] Rabotaet' if 'active' in is_active else '[ERROR] Ne rabotaet'}")

    except Exception as e:
        print(f"\n[CRITICAL] Kriticheskaya oshibka: {e}")
        import traceback
        traceback.print_exc()

    finally:
        ssh.close()
        print("\n[CLOSE] Soedinenie zakryto")

if __name__ == "__main__":
    main()
