#!/usr/bin/env python3
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


print("="*60)
print("CHECK PROXIFIER DRIVER")
print("="*60)

# Проверка службы драйвера
print("\n1. Proxifier Driver Service:")
print(ssh(r'''
$drv = Get-Service ProxifierDrv -ErrorAction SilentlyContinue
if ($drv) {
    Write-Output "Found: $($drv.DisplayName)"
    Write-Output "Status: $($drv.Status)"
    Write-Output "StartType: $($drv.StartType)"
} else {
    Write-Output "Service ProxifierDrv not found"
}
'''))

# driverquery
print("\n2. Driver Query (Proxifier):")
print(ssh('driverquery /v | findstr -i "proxifier"'))

# Файл драйвера
print("\n3. Driver File:")
print(ssh(r'''
$path = "C:\Program Files (x86)\Proxifier\ProxifierDrv.sys"
if (Test-Path $path) {
    $f = Get-Item $path
    Write-Output "EXISTS: $($f.Length) bytes"
} else {
    Write-Output "NOT FOUND"
}
'''))

# Проверка загруженных драйверов
print("\n4. Loaded kernel modules (prox):")
print(ssh(r'''
Get-WmiObject Win32_SystemDriver | Where-Object {$_.Name -like "*prox*"} | Select-Object Name, State, Status | Format-Table
'''))

print("\n" + "="*60)
