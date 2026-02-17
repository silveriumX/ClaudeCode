#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Расследование массового отказа серверов
Проверяем что случилось за последние 24 часа
"""
from pathlib import Path
import paramiko
from datetime import datetime

def load_credentials():
    creds_file = Path(__file__).resolve().parent / ".credentials"
    creds = {}
    if not creds_file.exists():
        return creds
    with creds_file.open('r', encoding='utf-8') as f:
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

def exec_cmd(client, cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='ignore')

def main():
    print("=" * 80)
    print("РАССЛЕДОВАНИЕ: МАССОВЫЙ ОТКАЗ СЕРВЕРОВ")
    print("=" * 80)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("[*] Подключение к VPS...")
        client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER,
                      password=VPS_PASSWORD, timeout=30)
        print("[OK] Подключено\n")

        # ========================================================================
        # 1. КОГДА НАЧАЛИСЬ ПРОБЛЕМЫ?
        # ========================================================================
        print("=" * 80)
        print("1. ВРЕМЕННАЯ ШКАЛА ПРОБЛЕМЫ")
        print("=" * 80)

        print("\n[*] Ищем когда начались ошибки 'Failed to create shell'...")
        output = exec_cmd(client,
            "journalctl -u server-monitor --since '24 hours ago' --no-pager | grep 'Failed to create shell' | head -20"
        )

        if output.strip():
            lines = output.splitlines()
            print(f"    Первая ошибка: {lines[0][:80]}...")
            print(f"    Всего ошибок за 24ч: {len(lines)}+")
        else:
            print("    Нет ошибок за последние 24 часа!")

        # Последняя успешная проверка
        print("\n[*] Последняя успешная проверка всех серверов...")
        output = exec_cmd(client,
            "journalctl -u server-monitor --since '48 hours ago' --no-pager | grep 'Check completed. Errors: 0' | tail -5"
        )

        if output.strip():
            for line in output.splitlines():
                print(f"    {line}")
        else:
            print("    НЕТ успешных проверок без ошибок за последние 48ч!")

        # История ошибок
        print("\n[*] Статистика ошибок по времени (последние 24ч)...")
        output = exec_cmd(client,
            "journalctl -u server-monitor --since '24 hours ago' --no-pager | grep 'Check completed' | tail -20"
        )

        for line in output.splitlines()[-10:]:
            print(f"    {line}")

        # ========================================================================
        # 2. КАКИЕ ИМЕННО СЕРВЕРЫ НЕДОСТУПНЫ?
        # ========================================================================
        print("\n" + "=" * 80)
        print("2. АНАЛИЗ ПРОБЛЕМНЫХ СЕРВЕРОВ")
        print("=" * 80)

        print("\n[*] Подсчет ошибок по IP адресам за последние 2 часа...")
        output = exec_cmd(client,
            "journalctl -u server-monitor --since '2 hours ago' --no-pager | grep 'Failed to create shell on'"
        )

        error_count = {}
        for line in output.splitlines():
            if 'Failed to create shell on' in line:
                parts = line.split('Failed to create shell on')
                if len(parts) > 1:
                    ip = parts[1].strip()
                    error_count[ip] = error_count.get(ip, 0) + 1

        if error_count:
            print("\n    Проблемные серверы (сортировка по количеству ошибок):")
            for ip, count in sorted(error_count.items(), key=lambda x: x[1], reverse=True):
                print(f"      {ip}: {count} ошибок")

        # ========================================================================
        # 3. ПРОВЕРКА КОНФИГУРАЦИИ
        # ========================================================================
        print("\n" + "=" * 80)
        print("3. ПРОВЕРКА КОНФИГУРАЦИИ СИСТЕМЫ")
        print("=" * 80)

        # Проверяем изменения в .env
        print("\n[*] Последнее изменение .env файла...")
        output = exec_cmd(client, "stat /opt/server-monitor/.env | grep Modify")
        print(f"    {output.strip()}")

        # Проверяем изменения в Python модулях
        print("\n[*] Последние изменения Python модулей...")
        output = exec_cmd(client,
            "ls -lt /opt/server-monitor/*.py | head -5"
        )
        for line in output.splitlines():
            if line.strip():
                print(f"    {line}")

        # ========================================================================
        # 4. ПРОВЕРКА СЕТИ С VPS
        # ========================================================================
        print("\n" + "=" * 80)
        print("4. ПРОВЕРКА СЕТЕВОЙ ДОСТУПНОСТИ")
        print("=" * 80)

        print("\n[*] Проверяем доступность проблемных серверов с VPS...")

        # Берем топ 3 проблемных сервера
        if error_count:
            test_servers = list(error_count.keys())[:3]

            for ip in test_servers:
                print(f"\n    Сервер {ip}:")

                # Ping
                output = exec_cmd(client, f"ping -c 2 -W 2 {ip} 2>&1")
                if "2 received" in output or "2 packets received" in output:
                    print(f"      PING: ОК")
                else:
                    print(f"      PING: НЕДОСТУПЕН")

                # Telnet на порт 5985
                output = exec_cmd(client,
                    f"timeout 3 bash -c 'cat < /dev/null > /dev/tcp/{ip}/5985' 2>&1 && echo 'OPEN' || echo 'CLOSED'"
                )
                if "OPEN" in output:
                    print(f"      Порт 5985: ОТКРЫТ")
                else:
                    print(f"      Порт 5985: ЗАКРЫТ или недоступен")

        # ========================================================================
        # 5. ПРОВЕРКА ДАННЫХ ИЗ GOOGLE SHEETS
        # ========================================================================
        print("\n" + "=" * 80)
        print("5. ПРОВЕРКА ДАННЫХ ИЗ GOOGLE SHEETS")
        print("=" * 80)

        print("\n[*] Последняя загрузка данных из Google Sheets...")
        output = exec_cmd(client,
            "journalctl -u server-monitor --no-pager | grep 'Loaded.*servers' | tail -5"
        )

        for line in output.splitlines():
            print(f"    {line}")

        # Проверяем есть ли проблемы с Google Sheets API
        print("\n[*] Ошибки Google Sheets API...")
        output = exec_cmd(client,
            "journalctl -u server-monitor --since '24 hours ago' --no-pager | grep -i 'sheets\\|google\\|api' | grep -i 'error\\|failed' | tail -10"
        )

        if output.strip():
            print("    ОБНАРУЖЕНЫ ОШИБКИ:")
            for line in output.splitlines():
                if len(line) > 120:
                    line = line[:117] + "..."
                print(f"    {line}")
        else:
            print("    Нет ошибок Google Sheets API")

        # ========================================================================
        # 6. ПРОВЕРКА СИСТЕМНЫХ ИЗМЕНЕНИЙ
        # ========================================================================
        print("\n" + "=" * 80)
        print("6. СИСТЕМНЫЕ ИЗМЕНЕНИЯ НА VPS")
        print("=" * 80)

        # Перезапуски сервиса
        print("\n[*] Перезапуски server-monitor за последние 24ч...")
        output = exec_cmd(client,
            "journalctl -u server-monitor --since '24 hours ago' --no-pager | grep 'Started\\|Stopped\\|Restart' | tail -10"
        )

        if output.strip():
            for line in output.splitlines():
                print(f"    {line}")

        # Проверка системных обновлений
        print("\n[*] Системные обновления...")
        output = exec_cmd(client,
            "grep -i 'upgraded\\|installed' /var/log/apt/history.log 2>/dev/null | tail -5"
        )

        if output.strip():
            print("    Последние обновления:")
            for line in output.splitlines():
                print(f"    {line[:100]}")
        else:
            print("    Нет информации об обновлениях")

        # ========================================================================
        # 7. ТЕСТ ПОДКЛЮЧЕНИЯ К ОДНОМУ СЕРВЕРУ
        # ========================================================================
        print("\n" + "=" * 80)
        print("7. ТЕСТОВОЕ ПОДКЛЮЧЕНИЕ К ПРОБЛЕМНОМУ СЕРВЕРУ")
        print("=" * 80)

        if error_count:
            test_ip = list(error_count.keys())[0]
            print(f"\n[*] Пробуем подключиться к {test_ip} вручную...")

            # Создаем тестовый скрипт
            test_script = f"""
python3 << 'EOF'
from winrm_connector import WinRMConnector
import logging
logging.basicConfig(level=logging.DEBUG)

connector = WinRMConnector()

# Пробуем выполнить простую команду
result = connector.execute_command(
    '{test_ip}',
    'Administrator',  # Попробуем стандартного пользователя
    'test_password',
    'echo "test"'
)

print(f"Result: {{result}}")
EOF
"""

            output = exec_cmd(client,
                f"cd /opt/server-monitor && {test_script}"
            )

            print("    Результат тестового подключения:")
            for line in output.splitlines()[-20:]:
                if line.strip():
                    print(f"    {line}")

        # ========================================================================
        # ВЫВОД И РЕКОМЕНДАЦИИ
        # ========================================================================
        print("\n" + "=" * 80)
        print("ВЫВОДЫ И РЕКОМЕНДАЦИИ")
        print("=" * 80)

        issues = []

        if len(error_count) >= 5:
            issues.append("Массовый отказ серверов (5+ серверов недоступны)")

        # Анализируем тип ошибки
        output = exec_cmd(client,
            "journalctl -u server-monitor --since '2 hours ago' --no-pager | grep 'status: 500\\|Connection refused\\|timeout\\|authentication failed' | tail -10"
        )

        if "status: 500" in output:
            issues.append("HTTP 500 ошибки - проблема на стороне WinRM серверов")
        if "Connection refused" in output:
            issues.append("Connection refused - WinRM сервис не запущен")
        if "timeout" in output:
            issues.append("Timeout - сетевая проблема или firewall")
        if "authentication" in output:
            issues.append("Authentication failed - неверные credentials")

        print("\n[ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ]")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")

        print("\n[РЕКОМЕНДАЦИИ]")
        print("1. Проверить Google Sheets - возможно изменились credentials")
        print("2. Проверить сетевую доступность серверов с VPS")
        print("3. Проверить статус WinRM на проблемных серверах")
        print("4. Проверить не было ли массового изменения паролей вчера")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
