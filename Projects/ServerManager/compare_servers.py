#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Сравнение работающего и проблемного сервера
"""
import paramiko
import os

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
    print("СРАВНЕНИЕ РАБОТАЮЩЕГО И ПРОБЛЕМНОГО СЕРВЕРА")
    print("=" * 80)
    print()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER,
                      password=VPS_PASSWORD, timeout=30)

        # Находим работающий сервер
        print("[1/3] Поиск работающего сервера...")
        stdin, stdout, stderr = client.exec_command("""
journalctl -u server-monitor --since '1 hour ago' --no-pager | \
grep 'Checking' | grep -v 'ERROR' | grep -v 'Failed' | \
tail -5
""")
        working_checks = stdout.read().decode('utf-8', errors='ignore')

        working_ip = None
        for line in working_checks.splitlines():
            if 'Checking' in line and 'INFO' in line:
                parts = line.split('Checking')
                if len(parts) > 1:
                    working_ip = parts[1].strip()
                    break

        if working_ip:
            print(f"   Работающий сервер: {working_ip}")
        else:
            print("   [WARNING] Не найден работающий сервер!")
            working_ip = "194.59.30.150"  # Используем по умолчанию
            print(f"   Используем по умолчанию: {working_ip}")

        problem_ip = "89.124.71.240"
        print(f"   Проблемный сервер: {problem_ip}")

        # Сравниваем логи подключения
        print(f"\n[2/3] Детальные логи подключения...")
        print()

        print(f"РАБОТАЮЩИЙ {working_ip}:")
        print("-" * 70)
        stdin, stdout, stderr = client.exec_command(f"""
journalctl -u server-monitor --since '30 minutes ago' --no-pager | \
grep -A 5 'Checking {working_ip}' | head -20
""")
        working_logs = stdout.read().decode('utf-8', errors='ignore')
        print(working_logs[:1000])

        print(f"\nПРОБЛЕМНЫЙ {problem_ip}:")
        print("-" * 70)
        stdin, stdout, stderr = client.exec_command(f"""
journalctl -u server-monitor --since '30 minutes ago' --no-pager | \
grep -A 5 'Checking {problem_ip}' | head -20
""")
        problem_logs = stdout.read().decode('utf-8', errors='ignore')
        print(problem_logs[:1000])

        # Проверяем HTTP ответ детально
        print(f"\n[3/3] HTTP 500 - что отвечает WinRM...")
        print()

        stdin, stdout, stderr = client.exec_command(f"""
cd /opt/server-monitor
python3 << 'PYEOF'
import requests
from requests_ntlm import HttpNtlmAuth
import logging

logging.basicConfig(level=logging.WARNING)

# Тестируем проблемный сервер
ip = "{problem_ip}"
url = f"http://{{ip}}:5985/wsman"

# Используем любые credentials для теста (ошибка 500 не зависит от credentials)
auth = HttpNtlmAuth(f"{{ip}}\\\\Administrator", "test123")

headers = {{'Content-Type': 'application/soap+xml;charset=UTF-8'}}

# Простой SOAP запрос
soap = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
<s:Header/>
<s:Body>
<wsmv:Identify xmlns:wsmv="http://schemas.dmtf.org/wbem/wsman/identity/1/wsmanidentity.xsd"/>
</s:Body>
</s:Envelope>"""

try:
    response = requests.post(url, auth=auth, headers=headers, data=soap, timeout=5)
    print(f"HTTP Status: {{response.status_code}}")
    print(f"Headers: {{dict(response.headers)}}")
    print(f"Body length: {{len(response.text)}}")
    print(f"Body preview: {{response.text[:500]}}")
except Exception as e:
    print(f"Error: {{e}}")
PYEOF
""")

        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')

        print(output)
        if error:
            print("STDERR:", error)

        print("\n" + "=" * 80)
        print("ВЫВОДЫ")
        print("=" * 80)

        print("\nHTTP 500 Internal Server Error означает:")
        print("1. WinRM РАБОТАЕТ (отвечает на запросы)")
        print("2. NTLM аутентификация НЕ ПРИЧИНА (500 ≠ 401)")
        print("3. Проблема ВНУТРИ WinRM сервера на Windows")
        print()
        print("Возможные причины HTTP 500:")
        print("• MaxMemoryPerShellMB превышен")
        print("• MaxShellsPerUser превышен")
        print("• WinRM Quota limits")
        print("• Проблема с PowerShell execution policy")
        print("• Антивирус блокирует WinRM операции")
        print("• Windows EventLog переполнен")
        print()
        print("ЧТО ПРОВЕРИТЬ НА ПРОБЛЕМНОМ СЕРВЕРЕ:")
        print("1. winrm get winrm/config/winrs")
        print("2. Get-EventLog -LogName Microsoft-Windows-WinRM/Operational -Newest 50")
        print("3. winrm get winrm/config/service")
        print("4. Get-ExecutionPolicy")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
