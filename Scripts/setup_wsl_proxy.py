#!/usr/bin/env python3
"""
Установка Ubuntu в WSL и настройка redsocks для прокси
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")


def ssh(cmd, timeout=300):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)
    enc = base64.b64encode(cmd.encode('utf-16le')).decode()
    _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
    return o.read().decode('utf-8', errors='ignore').strip()


print("="*70)
print("  УСТАНОВКА WSL + UBUNTU")
print("="*70)

# Шаг 1: Проверить и установить WSL Ubuntu
print("\n1. Проверка WSL...")

result = ssh(r'''
Write-Output "=== WSL Status ==="
wsl --status 2>&1

Write-Output ""
Write-Output "=== Installed distros ==="
wsl --list --verbose 2>&1 | Select-String -Pattern "NAME|Ubuntu|Debian"

Write-Output ""
Write-Output "=== Online distros ==="
wsl --list --online 2>&1 | Select-String -Pattern "NAME|Ubuntu"
''')
print(result)

# Шаг 2: Установить Ubuntu если не установлен
print("\n2. Установка Ubuntu...")

result = ssh(r'''
# Проверить есть ли Ubuntu
$distros = wsl --list --quiet 2>&1
if ($distros -match "Ubuntu") {
    Write-Output "Ubuntu already installed"
} else {
    Write-Output "Installing Ubuntu..."
    wsl --install -d Ubuntu --no-launch 2>&1
    Write-Output "Installation started"
}
''')
print(result)

# Подождём установки
print("\nОжидание установки (может занять несколько минут)...")
time.sleep(30)

# Шаг 3: Проверить статус
print("\n3. Проверка статуса...")

result = ssh(r'''
wsl --list --verbose 2>&1
''')
print(result)

print("\n" + "="*70)
print("""
ПРИМЕЧАНИЕ:
Установка WSL на Windows Server может требовать:
1. Перезагрузку сервера
2. Включение Hyper-V / Virtual Machine Platform
3. Ручную инициализацию Ubuntu (первый запуск)

Если WSL установлен успешно, следующий шаг:
- Настроить redsocks в Ubuntu для перенаправления трафика через SOCKS5
""")
print("="*70)
