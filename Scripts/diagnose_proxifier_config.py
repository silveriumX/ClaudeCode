#!/usr/bin/env python3
"""
Диагностика конфигурации Proxifier
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

def ssh(cmd, timeout=30):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(os.getenv("VPS_WIN_HOST"), username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=10, look_for_keys=False)
        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
        return o.read().decode('utf-8', errors='ignore').strip()
    except Exception as e:
        return f"ERROR: {e}"


print("="*70)
print("🔍 ДИАГНОСТИКА КОНФИГУРАЦИИ PROXIFIER")
print("="*70)

# 1. Версия Proxifier
print("\n📋 Версия Proxifier:")
print(ssh(r'''
$exe = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$ver = (Get-Item $exe).VersionInfo
Write-Output "ProductName: $($ver.ProductName)"
Write-Output "FileVersion: $($ver.FileVersion)"
Write-Output "ProductVersion: $($ver.ProductVersion)"
'''))

# 2. Полное содержимое профиля
print("\n📋 Содержимое профиля Default.ppx:")
print(ssh(r'''
$profile = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
if (Test-Path $profile) {
    Get-Content $profile
} else {
    Write-Output "Profile not found"
}
'''))

# 3. Реестр Proxifier (после сброса)
print("\n📋 Реестр Proxifier:")
print(ssh(r'''
$path = "HKCU:\Software\Initex\Proxifier"
if (Test-Path $path) {
    Get-ItemProperty $path | Format-List
} else {
    Write-Output "Registry key not found (was deleted)"
}
'''))

# 4. Proxifier процесс детали
print("\n📋 Детали процесса Proxifier:")
print(ssh(r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PID: $($proc.Id)"
    Write-Output "Session: $($proc.SessionId)"
    Write-Output "MainWindowTitle: $($proc.MainWindowTitle)"
    Write-Output "MainWindowHandle: $($proc.MainWindowHandle)"
    Write-Output "Path: $($proc.Path)"
    Write-Output "StartTime: $($proc.StartTime)"
} else {
    Write-Output "Not running"
}
'''))

# 5. Проверим есть ли файл лицензии
print("\n📋 Файлы Proxifier:")
print(ssh(r'''
$paths = @(
    "$env:APPDATA\Proxifier4",
    "C:\Program Files (x86)\Proxifier",
    "$env:ProgramData\Proxifier"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Output "`n=== $p ==="
        Get-ChildItem $p -Recurse -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
    }
}
'''))

print("\n" + "="*70)
