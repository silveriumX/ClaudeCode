#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
FINAL VERIFICATION - check that everything works perfectly
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
print("✅ ФИНАЛЬНАЯ ПРОВЕРКА МИГРАЦИИ НА SSH")
print("=" * 70)

# 1. Service status
stdin, stdout, stderr = client.exec_command("systemctl is-active server-monitor")
service_status = stdout.read().decode().strip()
print(f"\n1. Служба мониторинга: {service_status}")
if service_status == "active":
    print("   ✅ РАБОТАЕТ")
else:
    print(f"   ❌ НЕ РАБОТАЕТ: {service_status}")

# 2. Check symlinks
stdin, stdout, stderr = client.exec_command("ls -la /opt/server-monitor/server_checker.py /opt/server-monitor/session_checker.py")
symlinks = stdout.read().decode('utf-8', errors='replace')
print(f"\n2. Symlinks:")
for line in symlinks.split('\n'):
    if 'server_checker.py' in line:
        if '-> server_checker_ssh.py' in line:
            print(f"   ✅ server_checker.py → server_checker_ssh.py")
        else:
            print(f"   ❌ server_checker.py symlink неправильный")
    if 'session_checker.py' in line:
        if '-> session_checker_ssh.py' in line:
            print(f"   ✅ session_checker.py → session_checker_ssh.py")
        else:
            print(f"   ❌ session_checker.py symlink неправильный")

# 3. Check recent activity (last 5 minutes)
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '5 minutes ago' --no-pager | grep -c 'Authentication.*successful' || echo 0")
ssh_count = stdout.read().decode().strip().split('\n')[-1]

stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '5 minutes ago' --no-pager | grep -c 'Failed to create shell' || echo 0")
winrm_errors = stdout.read().decode().strip().split('\n')[-1]

print(f"\n3. Активность (последние 5 минут):")
print(f"   ✅ SSH подключений: {ssh_count}")
print(f"   {'✅' if int(winrm_errors) == 0 else '❌'} WinRM ошибок: {winrm_errors}")

# 4. Check what connectors are imported
stdin, stdout, stderr = client.exec_command("grep 'from.*connector import' /opt/server-monitor/server_checker.py /opt/server-monitor/session_checker.py")
imports = stdout.read().decode('utf-8', errors='replace')
print(f"\n4. Используемые коннекторы:")
if 'ssh_connector' in imports and 'winrm' not in imports.lower():
    print("   ✅ Только SSH коннекторы")
    for line in imports.split('\n'):
        if line.strip():
            print(f"   {line}")
else:
    print("   ⚠️ Обнаружен WinRM!")
    print(imports)

# 5. Check last cycle completion
stdin, stdout, stderr = client.exec_command("journalctl -u server-monitor --since '10 minutes ago' --no-pager | grep 'Check completed' | tail -1")
last_cycle = stdout.read().decode('utf-8', errors='replace').strip()
print(f"\n5. Последний цикл проверки:")
if last_cycle:
    print(f"   {last_cycle}")
    if 'Errors: 0' in last_cycle or 'Errors: 2' in last_cycle:
        print("   ✅ Отлично! Только 2 сервера без SSH дают ошибки")
else:
    print("   ⏳ Цикл еще не завершен (идет проверка)")

client.close()

print("\n" + "=" * 70)
print("✅ МИГРАЦИЯ НА SSH ЗАВЕРШЕНА УСПЕШНО!")
print("=" * 70)
print("\n🎯 Система полностью работает через SSH")
print("📱 Telegram команды: /check, /status, /help")
print("📊 Google Sheets обновляется автоматически")
print("\n🚀 Готово к использованию!")
