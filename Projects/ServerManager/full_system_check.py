#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Полная проверка системы мониторинга на VPS
Проверяет все аспекты: сервисы, конфигурацию, логи, файлы, производительность
"""
import paramiko
import os
import sys
from datetime import datetime

from pathlib import Path
import sys

def get_creds():
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

def print_section(title):
    """Красивый заголовок секции"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def exec_cmd(client, cmd, description=""):
    """Выполнить команду и вернуть результат"""
    if description:
        print(f"\n[*] {description}")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    return output, error

def main():
    print("=" * 80)
    print("ПОЛНАЯ ДИАГНОСТИКА СИСТЕМЫ МОНИТОРИНГА VPS")
    print("=" * 80)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"VPS: {VPS_HOST}")
    print()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"[*] Подключение к VPS {VPS_HOST}...")
        client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER,
                      password=VPS_PASSWORD, timeout=30)
        print("[OK] Подключено!\n")

        # ========================================================================
        # 1. ИНФОРМАЦИЯ О СИСТЕМЕ
        # ========================================================================
        print_section("1. ИНФОРМАЦИЯ О СИСТЕМЕ")

        # Hostname
        output, _ = exec_cmd(client, "hostname", "Hostname")
        print(f"    {output.strip()}")

        # OS версия
        output, _ = exec_cmd(client, "lsb_release -d 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME", "ОС версия")
        print(f"    {output.strip()}")

        # Uptime
        output, _ = exec_cmd(client, "uptime -p", "Uptime системы")
        print(f"    {output.strip()}")

        # Память
        output, _ = exec_cmd(client, "free -h | grep Mem", "Память")
        print(f"    {output.strip()}")

        # Диск
        output, _ = exec_cmd(client, "df -h /opt/server-monitor", "Диск (/opt/server-monitor)")
        lines = output.strip().split('\n')
        for line in lines:
            print(f"    {line}")

        # ========================================================================
        # 2. СТАТУС СЕРВИСОВ
        # ========================================================================
        print_section("2. СТАТУС СЕРВИСОВ")

        services = ['server-monitor', 'command-webhook', 'proxyma-monitor']

        for service in services:
            output, _ = exec_cmd(client, f"systemctl is-active {service}")
            status = output.strip()

            output, _ = exec_cmd(client, f"systemctl status {service} --no-pager -n 0")

            # Извлекаем uptime и статус
            uptime_line = [line for line in output.split('\n') if 'Active:' in line]
            if uptime_line:
                uptime = uptime_line[0].strip()
                status_icon = "[OK]" if "active (running)" in uptime else "[--]" if "inactive" in uptime else "[ERROR]"
                print(f"\n{status_icon} {service}")
                print(f"    {uptime}")
            else:
                print(f"\n[?] {service}: {status}")

        # ========================================================================
        # 3. КОНФИГУРАЦИЯ (.env)
        # ========================================================================
        print_section("3. КОНФИГУРАЦИЯ (.env)")

        output, _ = exec_cmd(client, "cat /opt/server-monitor/.env", "Содержимое .env файла")
        for line in output.split('\n'):
            # Скрываем токены частично
            if 'TOKEN' in line or 'KEY' in line or 'PASSWORD' in line:
                parts = line.split('=')
                if len(parts) == 2:
                    key, value = parts
                    if len(value) > 8:
                        masked = value[:4] + "***" + value[-4:]
                        print(f"    {key}={masked}")
                    else:
                        print(f"    {line}")
            else:
                print(f"    {line}")

        # ========================================================================
        # 4. ФАЙЛЫ СИСТЕМЫ
        # ========================================================================
        print_section("4. ФАЙЛЫ СИСТЕМЫ")

        output, _ = exec_cmd(client, "ls -lh /opt/server-monitor/*.py", "Python модули")
        for line in output.split('\n'):
            if line.strip():
                print(f"    {line}")

        # Версия модулей
        print("\n[*] Версии модулей (из комментариев):")
        for module in ['winrm_connector.py', 'server_checker.py', 'server_monitor.py', 'command_handler.py']:
            output, _ = exec_cmd(client, f"head -20 /opt/server-monitor/{module} | grep -i 'version\\|версия' | head -1")
            if output.strip():
                print(f"    {module}: {output.strip()}")

        # ========================================================================
        # 5. ЛОГИ (ПОСЛЕДНИЕ 10 МИНУТ)
        # ========================================================================
        print_section("5. АНАЛИЗ ЛОГОВ (последние 10 минут)")

        output, _ = exec_cmd(client, "journalctl -u server-monitor --since '10 minutes ago' --no-pager")

        # Статистика ошибок
        header_errors = output.count('HeaderParsingError')
        assertion_errors = output.count('AssertionError')
        check_completed = output.count('Check completed')
        error_count = output.count('ERROR')
        warning_count = output.count('WARNING')
        info_count = output.count('INFO')

        print(f"\n[*] Статистика:")
        print(f"    INFO сообщений: {info_count}")
        print(f"    WARNING: {warning_count}")
        print(f"    ERROR: {error_count}")
        print(f"    HeaderParsingError: {header_errors}")
        print(f"    AssertionError: {assertion_errors}")
        print(f"    Check completed: {check_completed}")

        # Последние события
        print("\n[*] Последние 15 событий:")
        lines = output.splitlines()
        important = [l for l in lines if any(kw in l for kw in ['INFO', 'ERROR', 'WARNING', 'Check completed'])]
        for line in important[-15:]:
            if len(line) > 120:
                line = line[:117] + "..."
            print(f"    {line}")

        # ========================================================================
        # 6. WEBHOOK СЕРВИС
        # ========================================================================
        print_section("6. WEBHOOK СЕРВИС (command-webhook)")

        output, _ = exec_cmd(client, "journalctl -u command-webhook --since '10 minutes ago' --no-pager | tail -20")

        webhook_requests = output.count('POST')
        webhook_errors = output.count('ERROR')

        print(f"\n[*] Активность webhook за последние 10 минут:")
        print(f"    POST запросов: {webhook_requests}")
        print(f"    Ошибок: {webhook_errors}")

        if output.strip():
            print("\n[*] Последние записи:")
            for line in output.split('\n')[-10:]:
                if line.strip():
                    if len(line) > 120:
                        line = line[:117] + "..."
                    print(f"    {line}")

        # ========================================================================
        # 7. ПРОВЕРКА ЗАВИСИМОСТЕЙ
        # ========================================================================
        print_section("7. PYTHON ЗАВИСИМОСТИ")

        output, _ = exec_cmd(client, "pip3 list 2>/dev/null | grep -E 'paramiko|requests|pywinrm|google|telegram'")
        print("\n[*] Установленные пакеты:")
        for line in output.split('\n'):
            if line.strip():
                print(f"    {line}")

        # ========================================================================
        # 8. ПРОВЕРКА СЕТИ
        # ========================================================================
        print_section("8. СЕТЕВАЯ КОНФИГУРАЦИЯ")

        # IP адрес VPS
        output, _ = exec_cmd(client, "hostname -I", "IP адреса")
        print(f"    {output.strip()}")

        # Активные подключения
        output, _ = exec_cmd(client, "netstat -tuln | grep -E ':8080|:5985' | head -5")
        if output.strip():
            print("\n[*] Активные порты:")
            for line in output.split('\n'):
                if line.strip():
                    print(f"    {line}")

        # ========================================================================
        # 9. ПРОВЕРКА ПРОИЗВОДИТЕЛЬНОСТИ
        # ========================================================================
        print_section("9. ПРОИЗВОДИТЕЛЬНОСТЬ")

        # CPU
        output, _ = exec_cmd(client, "top -bn1 | grep 'Cpu(s)' | head -1")
        print(f"\n[*] CPU: {output.strip()}")

        # Топ процессы Python
        output, _ = exec_cmd(client, "ps aux | grep python3 | grep -v grep | head -5")
        if output.strip():
            print("\n[*] Python процессы:")
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) > 10:
                        print(f"    PID: {parts[1]}, CPU: {parts[2]}%, MEM: {parts[3]}%, CMD: {' '.join(parts[10:])}")

        # ========================================================================
        # 10. ПОСЛЕДНЯЯ ПРОВЕРКА СЕРВЕРОВ
        # ========================================================================
        print_section("10. ПОСЛЕДНЯЯ ПРОВЕРКА СЕРВЕРОВ")

        output, _ = exec_cmd(client, "journalctl -u server-monitor -n 200 --no-pager | grep 'Checking\\|Check completed'")

        lines = output.split('\n')
        checking_lines = [l for l in lines if 'Checking' in l][-10:]
        completed_lines = [l for l in lines if 'Check completed' in l][-3:]

        print("\n[*] Последние проверенные серверы:")
        for line in checking_lines:
            if line.strip():
                # Извлекаем IP
                parts = line.split('Checking')
                if len(parts) > 1:
                    ip = parts[1].strip()
                    print(f"    {ip}")

        print("\n[*] Результаты проверок:")
        for line in completed_lines:
            print(f"    {line}")

        # ========================================================================
        # ИТОГОВЫЙ ОТЧЕТ
        # ========================================================================
        print_section("ИТОГОВЫЙ ОТЧЕТ")

        issues = []
        warnings = []

        # Проверяем сервисы
        output, _ = exec_cmd(client, "systemctl is-active server-monitor")
        if output.strip() != "active":
            issues.append("server-monitor не активен")

        output, _ = exec_cmd(client, "systemctl is-active command-webhook")
        if output.strip() != "active":
            issues.append("command-webhook не активен")

        # Проверяем ошибки в логах
        if header_errors > 0:
            warnings.append(f"HeaderParsingError обнаружен ({header_errors} раз)")

        if assertion_errors > 0:
            issues.append(f"AssertionError обнаружен ({assertion_errors} раз)")

        if check_completed == 0:
            warnings.append("Нет завершенных проверок за последние 10 минут")

        # Выводим результат
        if not issues and not warnings:
            print("\n[SUCCESS] Система работает отлично!")
            print("    - Все сервисы активны")
            print("    - Логи чистые")
            print("    - Проверки серверов выполняются")
            print("    - Нет критических ошибок")
        else:
            if issues:
                print("\n[КРИТИЧНО] Обнаружены проблемы:")
                for issue in issues:
                    print(f"    ! {issue}")

            if warnings:
                print("\n[ВНИМАНИЕ] Предупреждения:")
                for warning in warnings:
                    print(f"    * {warning}")

        print("\n" + "=" * 80)
        print("ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Ошибка подключения: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
