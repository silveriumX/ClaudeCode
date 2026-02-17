#!/usr/bin/env python3
"""
Поиск лицензии Proxifier и восстановление реестра
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
print("🔍 ПОИСК ЛИЦЕНЗИИ PROXIFIER")
print("="*70)

# Поиск в реестре (может быть в других местах)
print("\n📋 Поиск лицензии в реестре:")
print(ssh(r'''
# Поиск в других ветках реестра
$paths = @(
    "HKLM:\Software\Initex",
    "HKLM:\Software\WOW6432Node\Initex",
    "HKCU:\Software\Initex"
)

foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Output "FOUND: $p"
        Get-ChildItem $p -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Output "  $($_.PSPath)"
            Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue | Select-Object * | Format-List
        }
    }
}
'''))

# Поиск файлов с лицензией
print("\n📋 Поиск файлов лицензии:")
print(ssh(r'''
$searchPaths = @(
    "$env:APPDATA\Proxifier*",
    "$env:ProgramData\Proxifier*",
    "C:\Program Files (x86)\Proxifier\*"
)

foreach ($sp in $searchPaths) {
    Get-ChildItem $sp -Recurse -ErrorAction SilentlyContinue |
        Where-Object {$_.Name -match "license|key|reg|serial"} |
        ForEach-Object {
            Write-Output "FOUND: $($_.FullName)"
        }
}
'''))

# Проверка reg файлов
print("\n📋 Поиск .reg файлов:")
print(ssh(r'''
Get-ChildItem "C:\Users" -Recurse -Filter "*.reg" -ErrorAction SilentlyContinue |
    Where-Object {$_.Name -match "proxifier"} |
    Select-Object FullName, Length, LastWriteTime
'''))

# Попробуем восстановить из System Restore
print("\n📋 Проверка System Restore Points:")
print(ssh(r'''
Get-ComputerRestorePoint -ErrorAction SilentlyContinue | Select-Object SequenceNumber, Description, CreationTime | Format-Table
'''))

print("\n" + "="*70)
print("""
📊 ВАРИАНТЫ:
1. Если найден .reg файл — импортировать его
2. Если есть Restore Point — можно восстановить реестр
3. Если ничего нет — нужен лицензионный ключ для активации
4. Или попробовать подключиться по RDP и ввести ключ вручную
""")
