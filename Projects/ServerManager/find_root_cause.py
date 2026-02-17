#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Поиск реальной причины - сравнение успешных и неуспешных попыток
"""
import paramiko
import os
import re

def load_credentials():
    creds_file = os.path.join(os.path.dirname(__file__), ".credentials")
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
    print("ПОИСК РЕАЛЬНОЙ ПРИЧИНЫ ПРОБЛЕМЫ")
    print("=" * 80)
    print()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER,
                      password=VPS_PASSWORD, timeout=30)

        # Проверяем КОГДА начались ошибки 401 vs 500
        print("[1/4] Анализ типов ошибок по времени...")
        print()

        stdin, stdout, stderr = client.exec_command("""
journalctl -u server-monitor --since '7 days ago' --no-pager | \
grep -E 'Failed to create shell, status: (401|500)' | \
awk '{print $1, $2, $3, $NF}' | tail -50
""")
        errors = stdout.read().decode('utf-8', errors='ignore')

        print("Последние 50 ошибок (дата + код):")
        print(errors)

        # Статистика
        error_401 = errors.count('401')
        error_500 = errors.count('500')

        print(f"\nСтатистика:")
        print(f"  Ошибок 401: {error_401}")
        print(f"  Ошибок 500: {error_500}")

        if error_401 > error_500:
            print("  → Основная проблема: CREDENTIALS (401 = Unauthorized)")
        else:
            print("  → Основная проблема: WinRM CONFIG (500 = Internal Server Error)")

        # Ищем когда ПОСЛЕДНИЙ РАЗ были успешные подключения
        print("\n[2/4] Последние УСПЕШНЫЕ подключения к проблемным серверам...")
        print()

        problem_ips = ['89.124.71.240', '89.124.72.242']

        for ip in problem_ips:
            print(f"Сервер {ip}:")
            stdin, stdout, stderr = client.exec_command(f"""
journalctl -u server-monitor --since '14 days ago' --no-pager | \
grep 'Checking {ip}' | \
grep -v 'ERROR\|Failed' | \
tail -5
""")
            success = stdout.read().decode('utf-8', errors='ignore')

            if success.strip():
                lines = success.splitlines()
                print(f"  Последняя успешная проверка:")
                for line in lines:
                    # Извлекаем дату
                    parts = line.split()
                    if len(parts) >= 3:
                        print(f"    {parts[0]} {parts[1]} {parts[2]}")
            else:
                print("  ❌ Нет успешных проверок за последние 14 дней!")
            print()

        # Проверяем не было ли ИЗМЕНЕНИЙ в системе мониторинга 24-25 января
        print("[3/4] Изменения в системе 24-26 января...")
        print()

        stdin, stdout, stderr = client.exec_command("""
find /opt/server-monitor -name '*.py' -type f -newermt '2026-01-24' ! -newermt '2026-01-27' -exec ls -lh {} \;
""")
        changes = stdout.read().decode('utf-8', errors='ignore')

        if changes.strip():
            print("Измененные файлы:")
            print(changes)
        else:
            print("Нет изменений в Python файлах")

        # Проверяем логи на предмет изменений credentials/username
        print("\n[4/4] Ищем изменения в формате username...")
        print()

        stdin, stdout, stderr = client.exec_command("""
journalctl -u server-monitor --since '14 days ago' --no-pager | \
grep -i 'username\|credential\|auth' | \
grep -v 'NTLM' | \
tail -20
""")
        auth_logs = stdout.read().decode('utf-8', errors='ignore')

        if auth_logs.strip():
            print("Логи связанные с аутентификацией:")
            print(auth_logs)
        else:
            print("Нет специфичных логов об аутентификации")

        print("\n" + "=" * 80)
        print("ГИПОТЕЗЫ")
        print("=" * 80)

        print("\nНа основе анализа, возможные причины:")
        print()

        if error_401 > 0:
            print("1. ПРОБЛЕМА С CREDENTIALS (401 Unauthorized)")
            print("   Возможно:")
            print("   - Windows Policy требует смену пароля каждые N дней")
            print("   - Пароли истекли автоматически")
            print("   - Изменился формат username в Sheets (добавился/убрался IP\\)")
            print("   - Пароль содержит спец.символы которые неправильно эк��апируются")

        if error_500 > 0:
            print("\n2. ПРОБЛЕМА КОНФИГУРАЦИИ WinRM (500 Internal Error)")
            print("   Возможно:")
            print("   - WinRM отключил HTTP (требует только HTTPS)")
            print("   - Изменились лимиты/квоты WinRM")
            print("   - Windows обновился и изменил настройки безопасности")

        print("\nРЕКОМЕНДАЦИИ:")
        print("1. Подключиться к ОДНОМУ проблемному серверу через RDP")
        print("2. Проверить: winrm get winrm/config/service")
        print("3. Проверить: Get-EventLog -LogName Security -Newest 50 | Where-Object {$_.EventID -eq 4625}")
        print("   (Failed login attempts)")
        print("4. Попробовать подключиться локально: Test-WSMan -ComputerName localhost")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
