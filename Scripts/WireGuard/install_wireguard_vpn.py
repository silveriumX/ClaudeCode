#!/usr/bin/env python3
"""
Установка WireGuard VPN + wg-easy веб-панели на Windows Server
С маршрутизацией через SOCKS5 прокси
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64
import io
import sys
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

# Конфигурация
SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = "10001"
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

WG_PORT = 51820
WG_EASY_PORT = 51821


def ssh(cmd, timeout=120):
    """Выполнить PowerShell команду через SSH"""
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)

        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, e = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)

        out = o.read().decode('utf-8', errors='ignore').strip()
        err = e.read().decode('utf-8', errors='ignore').strip()
        c.close()

        return out if out else err
    except Exception as ex:
        return f"SSH_ERROR: {ex}"


def main():
    print("="*70)
    print("  УСТАНОВКА WIREGUARD VPN + WG-EASY")
    print("="*70)
    print(f"\nСервер: {SSH_HOST}")
    print(f"Прокси: {PROXY_HOST}:{PROXY_PORT}")
    print(f"WireGuard порт: {WG_PORT}")
    print(f"Веб-панель порт: {WG_EASY_PORT}")

    # Проверка ОС
    print("\n" + "="*70)
    print("Шаг 0: Проверка системы")
    print("="*70)

    result = ssh(r'''
$os = (Get-WmiObject Win32_OperatingSystem).Caption
Write-Output "OS:$os"

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    $ver = docker --version 2>$null
    Write-Output "DOCKER:$ver"
} else {
    Write-Output "DOCKER:NotInstalled"
}

$wg = Get-Service WireGuardTunnel* -ErrorAction SilentlyContinue
if ($wg) {
    Write-Output "WIREGUARD:Installed"
} else {
    Write-Output "WIREGUARD:NotInstalled"
}
''')
    print(result)

    # На Windows Server нужен другой подход - WireGuard напрямую, без Docker
    # wg-easy работает только на Linux

    print("\n" + "="*70)
    print("ВНИМАНИЕ: Windows Server")
    print("="*70)
    print("""
wg-easy работает только на Linux (Docker с kernel modules).
Для Windows Server используем WireGuard напрямую.

Варианты:
1. Установить WireGuard на этот Windows Server
2. Использовать отдельный Linux VPS для VPN

Рекомендую: Отдельный Linux VPS (даже дешёвый за $3-5/мес)
- Полноценный wg-easy с веб-панелью
- Маршрутизация через SOCKS5 прокси
- Больше гибкости
""")

    # Но для теста можем установить WireGuard на Windows
    print("\n" + "="*70)
    print("Шаг 1: Установка WireGuard на Windows Server")
    print("="*70)

    result = ssh(r'''
# Проверить установлен ли WireGuard
$wg = Get-Command wg -ErrorAction SilentlyContinue
if ($wg) {
    Write-Output "WG_INSTALLED:Yes"
    $ver = wg --version 2>$null
    Write-Output "VERSION:$ver"
} else {
    Write-Output "WG_INSTALLED:No"
    Write-Output "Downloading WireGuard installer..."

    $url = "https://download.wireguard.com/windows-client/wireguard-installer.exe"
    $installer = "$env:TEMP\wireguard-installer.exe"

    try {
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        if (Test-Path $installer) {
            Write-Output "DOWNLOADED:$((Get-Item $installer).Length) bytes"
        }
    } catch {
        Write-Output "DOWNLOAD_ERROR:$($_.Exception.Message)"
    }
}
''')
    print(result)

    if "WG_INSTALLED:No" in result and "DOWNLOADED" in result:
        print("\nWireGuard скачан. Для установки на Windows Server нужно:")
        print("1. Запустить установщик вручную (или через RDP)")
        print("2. Или использовать Linux VPS")

    print("\n" + "="*70)
    print("АЛЬТЕРНАТИВНОЕ РЕШЕНИЕ")
    print("="*70)
    print("""
Для полноценного VPN с веб-панелью на Windows Server
рекомендую использовать один из вариантов:

1. OUTLINE VPN (от Google Jigsaw)
   - Простая установка
   - Веб-панель управления
   - Работает на Windows Server

2. Отдельный Linux VPS
   - wg-easy (веб-панель)
   - Полная автоматизация
   - Маршрутизация через SOCKS5

3. WireGuard напрямую
   - Установить через RDP
   - Настроить вручную
   - Без веб-панели

Какой вариант предпочтительнее?
""")


if __name__ == "__main__":
    main()
