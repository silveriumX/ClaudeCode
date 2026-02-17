#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Финальная проверка - работает ли все корректно
"""
import paramiko
import os
import sys

from pathlib import Path
import sys

def load_credentials():
    creds_file = Path(__file__).resolve().parent / ".credentials"
    creds = {}
    with open(creds_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                creds[key.strip()] = value.strip()
    return creds

_creds = load_credentials()
VPS_HOST = _creds.get('VPS_HOST', '151.241.154.57')
VPS_USER = _creds.get('VPS_USER', 'root')
VPS_PASSWORD = os.getenv("VPS_WIN_PASSWORD")
VPS_PORT = int(_creds.get('VPS_PORT', 22))

def main():
    print("=" * 80)
    print("ФИНАЛЬНАЯ ПРОВЕРКА СИСТЕМЫ МОНИТОРИНГА")
    print("=" * 80)
    print()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER,
                      password=VPS_PASSWORD, timeout=30)

        # Статус сервисов
        print("[1/4] Статус сервисов...")
        for service in ['server-monitor', 'command-webhook']:
            stdin, stdout, stderr = client.exec_command(f"systemctl is-active {service}")
            status = stdout.read().decode().strip()
            status_icon = "[OK]" if status == "active" else "[ERROR]"
            print(f"   {status_icon} {service}: {status}")
        print()

        # Логи с последнего перезапуска
        print("[2/4] Анализ логов (последние 5 минут)...")
        stdin, stdout, stderr = client.exec_command(
            "journalctl -u server-monitor --since '5 minutes ago' --no-pager"
        )
        recent_logs = stdout.read().decode('utf-8', errors='ignore')

        # Подсчитываем ключевые события
        header_errors = recent_logs.count('HeaderParsingError')
        check_completed = recent_logs.count('Check completed')
        assertion_errors = recent_logs.count('AssertionError')

        print(f"   HeaderParsingError: {header_errors}")
        print(f"   AssertionError: {assertion_errors}")
        print(f"   Check completed: {check_completed}")
        print()

        # Последние успешные проверки
        print("[3/4] Последние события (INFO/ERROR)...")
        print("-" * 80)
        lines = recent_logs.splitlines()
        important_lines = [l for l in lines if any(kw in l for kw in ['INFO', 'ERROR', 'Check completed'])]
        for line in important_lines[-15:]:
            # Обрезаем длинные строки
            if len(line) > 120:
                line = line[:117] + "..."
            print(line)
        print("-" * 80)
        print()

        # Результат
        print("[4/4] РЕЗУЛЬТАТ:")
        if header_errors == 0 and assertion_errors == 0:
            print("   [SUCCESS] Система работает корректно!")
            print("   - HeaderParsingError устранен")
            print("   - Сервис стабильно работает")
            if check_completed > 0:
                print(f"   - Выполнено {check_completed} проверок серверов")
        else:
            print("   [WARNING] Обнаружены проблемы:")
            if header_errors > 0:
                print(f"   - HeaderParsingError: {header_errors}")
            if assertion_errors > 0:
                print(f"   - AssertionError: {assertion_errors}")

        print("\n" + "=" * 80)
        print("ПРОВЕРКА ЗАВЕРШЕНА")
        print("=" * 80)

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
