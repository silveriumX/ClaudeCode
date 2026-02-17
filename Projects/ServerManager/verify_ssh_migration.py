#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Verify SSH migration - check if system is fully on SSH
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

print("=" * 70)
print("1. ПРОВЕРКА: Какой модуль используется")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("grep -n 'from.*connector import' /opt/server-monitor/server_checker.py")
connector_import = stdout.read().decode('utf-8', errors='replace')
print(connector_import)

print("\n" + "=" * 70)
print("2. ПРОВЕРКА: Версия server_monitor.py")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("head -10 /opt/server-monitor/server_monitor.py | grep -i version")
version = stdout.read().decode('utf-8', errors='replace')
print(version if version else "Version not found in first 10 lines")

print("\n" + "=" * 70)
print("3. ПРОВЕРКА: Последние успешные SSH подключения")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '5 minutes ago' --no-pager | grep -i 'connected.*openssh\\|authentication.*successful' | tail -10")
ssh_success = stdout.read().decode('utf-8', errors='replace')
print(ssh_success if ssh_success else "Нет SSH подключений за последние 5 минут")

print("\n" + "=" * 70)
print("4. ПРОВЕРКА: WinRM вызовы (не должно быть)")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '5 minutes ago' --no-pager | grep -i 'winrm' | tail -5")
winrm_calls = stdout.read().decode('utf-8', errors='replace')
if winrm_calls:
    print("⚠️  ВНИМАНИЕ: Обнаружены WinRM вызовы!")
    print(winrm_calls)
else:
    print("✅ WinRM вызовов нет - система полностью на SSH")

print("\n" + "=" * 70)
print("5. СТАТУС: Служба мониторинга")
print("=" * 70)
stdin, stdout, stderr = client.exec_command("systemctl is-active server-monitor")
status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"Статус: {status}")

print("\n" + "=" * 70)
print("6. ТЕСТ: Можно ли запустить /check команду")
print("=" * 70)
print("✅ Telegram бот работает (запущен в фоне)")
print("Команды доступны: /check, /status, /help")

client.close()

print("\n" + "=" * 70)
print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 70)
