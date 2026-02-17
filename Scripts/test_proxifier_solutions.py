#!/usr/bin/env python3
"""
Проверка различных способов управления Proxifier
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64
import io
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")


def ssh(ps_command, timeout=60):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False, allow_agent=False)

        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)

        return stdout.read().decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"ERROR:{e}"
    finally:
        if client:
            client.close()


print("="*80)
print("🔬 ПРОВЕРКА СПОСОБОВ УПРАВЛЕНИЯ PROXIFIER")
print("="*80)

# 1. Проверка CLI Proxifier
print("\n📋 Тест 1: Проверка CLI параметров Proxifier")

cli_test = r'''
$exe = "C:\Program Files (x86)\Proxifier\Proxifier.exe"

Write-Output "Проверка параметров командной строки..."
Write-Output ""

# Попробовать --help
$help = & $exe --help 2>&1 | Out-String
if ($help -match "error|not recognized|unknown") {
    Write-Output "CLI_HELP:Не поддерживается"
} else {
    Write-Output "CLI_HELP:$($help.Substring(0, [Math]::Min(200, $help.Length)))"
}

# Проверить версию
$ver = (Get-Item $exe).VersionInfo.FileVersion
Write-Output "VERSION:$ver"
'''

result = ssh(cli_test)
print(result)

# 2. Проверка реестра
print("\n📋 Тест 2: Проверка реестра Proxifier")

registry_test = r'''
Write-Output "Поиск настроек Proxifier в реестре..."
Write-Output ""

$paths = @(
    "HKCU:\Software\Initex",
    "HKCU:\Software\Proxifier",
    "HKLM:\Software\Initex",
    "HKLM:\Software\Proxifier",
    "HKLM:\Software\WOW6432Node\Initex"
)

foreach ($path in $paths) {
    if (Test-Path $path) {
        Write-Output "FOUND:$path"
        Get-ChildItem $path -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Output "  Key: $($_.Name)"
        }
    }
}
'''

result = ssh(registry_test)
print(result)

# 3. Проверка запуска с профилем как аргументом
print("\n📋 Тест 3: Запуск Proxifier с профилем как аргумент")

profile_arg_test = r'''
# Сначала остановим
Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$exe = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$profile = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"

Write-Output "Запуск: $exe `"$profile`""

# Попробовать запустить с профилем как аргументом
try {
    Start-Process -FilePath $exe -ArgumentList "`"$profile`"" -ErrorAction Stop
    Start-Sleep 3

    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "RESULT:✅ Proxifier запустился (PID=$($proc.Id))"
    } else {
        Write-Output "RESULT:❌ Не запустился"
    }
} catch {
    Write-Output "ERROR:$($_.Exception.Message)"
}
'''

result = ssh(profile_arg_test)
print(result)

# 4. Попробовать SendKeys для Proxifier (если есть окно)
print("\n📋 Тест 4: Проверка управления через SendKeys")

sendkeys_test = r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Output "PROCESS:❌ Proxifier не запущен"
    exit
}

# Проверить есть ли у процесса MainWindowHandle
if ($proc.MainWindowHandle -eq 0) {
    Write-Output "WINDOW:❌ Нет GUI окна (возможно в трее)"
} else {
    Write-Output "WINDOW:✅ Есть GUI окно (Handle=$($proc.MainWindowHandle))"
}

# Попробовать найти окно по заголовку
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll", CharSet=CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
}
"@

$hwnd = [WinAPI]::FindWindow($null, "Proxifier")
if ($hwnd -ne [IntPtr]::Zero) {
    Write-Output "WINDOW_FOUND:Handle=$hwnd"
} else {
    # Поиск по частичному имени через EnumWindows слишком сложен
    Write-Output "WINDOW_SEARCH:Окно 'Proxifier' не найдено напрямую"
}
'''

result = ssh(sendkeys_test)
print(result)

# 5. Финальная проверка состояния
print("\n📋 Тест 5: Текущее состояние")

final_check = r'''
Write-Output "=== Статус ==="
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROXIFIER:✅ PID=$($proc.Id), Session=$($proc.SessionId)"
} else {
    Write-Output "PROXIFIER:❌ Не запущен"
}

Write-Output ""
Write-Output "=== IP Check ==="
$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
if ($ip) {
    if ($ip -eq "62.84.101.97") {
        Write-Output "CURRENT_IP:$ip (прокси НЕ работает)"
    } else {
        Write-Output "CURRENT_IP:$ip (прокси работает!)"
    }
} else {
    Write-Output "CURRENT_IP:Нет ответа"
}
'''

result = ssh(final_check)
print(result)

print("\n" + "="*80)
print("📊 ВЫВОДЫ")
print("="*80)
