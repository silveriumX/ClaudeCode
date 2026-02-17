#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Анализ HTTP 500 ошибок детально
"""
import paramiko
import os

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
    print("ДЕТАЛЬНЫЙ АНАЛИЗ HTTP 500 ОШИБОК")
    print("=" * 80)
    print()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER,
                      password=VPS_PASSWORD, timeout=30)

        # Получаем детальные ошибки
        print("[1/3] Полные сообщения ошибок HTTP 500...")
        stdin, stdout, stderr = client.exec_command(
            "journalctl -u server-monitor --since '2 hours ago' --no-pager | grep -A 2 -B 2 'status: 500' | head -50"
        )
        output = stdout.read().decode('utf-8', errors='ignore')

        print(output[:2000])

        # Проверяем точную ошибку на одном сервере
        print("\n[2/3] Тестовое подключение с детальными логами...")
        stdin, stdout, stderr = client.exec_command("""
cd /opt/server-monitor
python3 << 'EOF'
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from winrm_connector import WinRMConnector

connector = WinRMConnector(timeout=10)

# Пробуем подключиться к проблемному серверу
result = connector.execute_command(
    '89.124.71.240',
    'Administrator',
    'testpass123',
    'echo test'
)

if result:
    print(f"SUCCESS: {result}")
else:
    print("FAILED: No result")
EOF
""")

        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')

        print("Вывод:")
        print(output[-1000:])
        if error:
            print("\nОшибки:")
            print(error[-1000:])

        # Проверяем работающий сервер для сравнения
        print("\n[3/3] Для сравнения - тест на РАБОТАЮЩЕМ сервере...")
        stdin, stdout, stderr = client.exec_command(
            "journalctl -u server-monitor --since '30 minutes ago' --no-pager | grep 'Checking' | grep -v 'Failed' | head -3"
        )
        output = stdout.read().decode('utf-8', errors='ignore')

        working_servers = []
        for line in output.splitlines():
            if 'Checking' in line:
                parts = line.split('Checking')
                if len(parts) > 1:
                    ip = parts[1].strip()
                    working_servers.append(ip)

        if working_servers:
            test_ip = working_servers[0]
            print(f"\nТестируем работающий сервер: {test_ip}")

            stdin, stdout, stderr = client.exec_command(
                f"timeout 5 bash -c 'cat < /dev/null > /dev/tcp/{test_ip}/5985' 2>&1 && echo 'WinRM OPEN' || echo 'WinRM CLOSED'"
            )
            output = stdout.read().decode('utf-8', errors='ignore')
            print(f"Результат: {output.strip()}")

        print("\n" + "=" * 80)
        print("ВЫВОДЫ")
        print("=" * 80)

        print("\nВОЗМОЖНЫЕ ПРИЧИНЫ HTTP 500:")
        print("1. WinRM сервис запущен, но настроен неправильно")
        print("2. Неверные credentials (username/password)")
        print("3. WinRM не разрешает подключения по HTTP (требует HTTPS)")
        print("4. Quota/лимиты WinRM превышены")
        print("5. Windows Firewall заблокировал WinRM")

        print("\nЧТО НУЖНО ПРОВЕРИТЬ НА ПРОБЛЕМНЫХ СЕРВЕРАХ:")
        print("1. Запущен ли сервис WinRM:")
        print("   Get-Service WinRM")
        print("\n2. Настройки WinRM:")
        print("   winrm get winrm/config")
        print("\n3. Разрешен ли HTTP трафик:")
        print("   winrm get winrm/config/service")
        print("\n4. Firewall правила:")
        print("   Get-NetFirewallRule -DisplayName '*WinRM*'")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
