#!/usr/bin/env python3
"""
Установка GOST для прозрачного проксирования VPN трафика
"""
import base64, io, os, sys, time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")

PROXY = f"socks5://{os.getenv('PROXY_USER')}:{os.getenv('PROXY_PASS')}@{os.getenv('PROXY_HOST')}:{os.getenv('PROXY_PORT')}"


def ssh(cmd, timeout=120):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)
    enc = base64.b64encode(cmd.encode('utf-16le')).decode()
    _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
    return o.read().decode('utf-8', errors='ignore').strip()


print("="*70)
print("  УСТАНОВКА GOST")
print("="*70)

# 1. Скачать GOST
print("\n1. Скачивание GOST...")
result = ssh(r'''
$gostDir = "C:\gost"
$gostExe = "$gostDir\gost.exe"

if (Test-Path $gostExe) {
    Write-Output "GOST:Installed"
} else {
    Write-Output "Downloading..."

    if (!(Test-Path $gostDir)) {
        New-Item -ItemType Directory -Path $gostDir -Force | Out-Null
    }

    $url = "https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-windows-amd64-2.11.5.zip"
    $zipPath = "$env:TEMP\gost.zip"

    curl.exe -L -o $zipPath $url 2>&1

    if (Test-Path $zipPath) {
        Expand-Archive -Path $zipPath -DestinationPath $gostDir -Force

        $exe = Get-ChildItem $gostDir -Filter "gost*.exe" -Recurse | Select-Object -First 1
        if ($exe -and $exe.Name -ne "gost.exe") {
            Rename-Item $exe.FullName "gost.exe"
        }

        if (Test-Path $gostExe) {
            Write-Output "GOST:Installed"
        }
    }
}
''')
print(result)

# 2. Запустить GOST как transparent proxy
print("\n2. Запуск GOST...")

# GOST может работать как transparent proxy с redirect
# Слушаем на порту 1080 и форвардим через SOCKS5
result = ssh(f'''
# Остановить если работает
Stop-Process -Name gost* -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$gostExe = "C:\\gost\\gost.exe"

# Запустить GOST: входящий SOCKS5 на 0.0.0.0:1080 -> исходящий через внешний SOCKS5
$args = "-L=socks5://:1080 -F={PROXY}"

Write-Output "Starting: gost $args"

Start-Process -FilePath $gostExe -ArgumentList $args.Split(" ") -WindowStyle Hidden

Start-Sleep 3

$proc = Get-Process gost* -ErrorAction SilentlyContinue
if ($proc) {{
    Write-Output "GOST:Running PID=$($proc.Id)"
}} else {{
    Write-Output "GOST:Failed to start"
}}
''')
print(result)

# 3. Тест GOST
print("\n3. Тест через локальный GOST...")
result = ssh(r'''
# Тест через локальный GOST прокси
$ip = curl.exe -x "socks5://127.0.0.1:1080" -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "IP via GOST: $ip"
''')
print(result)

# 4. Настроить маршрутизацию
print("\n4. Настройка маршрутизации для VPN...")

# Теперь нужно настроить чтобы трафик от VPN клиентов шёл через GOST
# На Windows это можно сделать через:
# - netsh portproxy (только TCP)
# - или изменив конфиг WireGuard чтобы клиенты использовали сервер как DNS + proxy

result = ssh(r'''
Write-Output "=== WireGuard config ==="
$wgConfig = "C:\WireGuard\wg0.conf"
if (Test-Path $wgConfig) {
    Get-Content $wgConfig
}

Write-Output ""
Write-Output "=== Current server IP ==="
$ip = curl.exe -s --max-time 5 https://api.ipify.org 2>$null
Write-Output "Server IP: $ip"
''')
print(result)

print("\n" + "="*70)
print("  СТАТУС")
print("="*70)
print("""
GOST запущен на порту 1080 — это локальный SOCKS5 прокси,
который форвардит трафик через внешний прокси.

Для VPN клиентов есть 2 варианта:

1. ПРОСТОЙ: В настройках браузера/приложений на клиенте
   указать прокси: socks5://10.66.66.1:1080

2. ПОЛНЫЙ: Настроить transparent proxy через netsh/iptables
   (сложно на Windows, просто на Linux)

Рекомендация: Для полного решения нужен Linux VPS
с iptables + redsocks.
""")
