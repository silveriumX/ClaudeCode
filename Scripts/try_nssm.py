#!/usr/bin/env python3
"""
Попытка запустить Proxifier через NSSM как службу
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.getenv("VPS_WIN_HOST"), username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=10, look_for_keys=False)

cmd = r'''
Write-Output "=== Trying NSSM approach ==="

# Скачать NSSM
$nssmDir = "C:\nssm"
$nssmExe = "$nssmDir\nssm.exe"

if (!(Test-Path $nssmExe)) {
    Write-Output "Downloading NSSM..."

    if (!(Test-Path $nssmDir)) {
        New-Item -ItemType Directory -Path $nssmDir -Force | Out-Null
    }

    $url = "https://nssm.cc/release/nssm-2.24.zip"
    $zipPath = "$env:TEMP\nssm.zip"

    curl.exe -L -o $zipPath $url 2>&1

    if (Test-Path $zipPath) {
        Expand-Archive -Path $zipPath -DestinationPath $nssmDir -Force

        # Найти win64 exe
        $exe = Get-ChildItem $nssmDir -Filter "nssm.exe" -Recurse | Where-Object {$_.DirectoryName -like "*win64*"} | Select-Object -First 1
        if ($exe) {
            Copy-Item $exe.FullName $nssmExe -Force
        }
    }
}

if (Test-Path $nssmExe) {
    Write-Output "NSSM: Installed"

    # Удалить старый сервис если есть
    & $nssmExe stop ProxifierSvc 2>&1 | Out-Null
    & $nssmExe remove ProxifierSvc confirm 2>&1 | Out-Null
    Start-Sleep 2

    # Создать сервис для Proxifier
    $proxifier = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
    $profile = "C:\Users\Administrator\AppData\Roaming\Proxifier\Profiles\Default.ppx"

    Write-Output ""
    Write-Output "Creating service..."

    # Установить сервис
    & $nssmExe install ProxifierSvc $proxifier $profile 2>&1
    & $nssmExe set ProxifierSvc AppDirectory "C:\Program Files (x86)\Proxifier" 2>&1
    & $nssmExe set ProxifierSvc DisplayName "Proxifier Service" 2>&1
    & $nssmExe set ProxifierSvc Description "Proxifier running as service" 2>&1
    & $nssmExe set ProxifierSvc Start SERVICE_AUTO_START 2>&1
    & $nssmExe set ProxifierSvc Type SERVICE_INTERACTIVE_PROCESS 2>&1

    Start-Sleep 2

    # Запустить
    Write-Output ""
    Write-Output "Starting service..."
    & $nssmExe start ProxifierSvc 2>&1

    Start-Sleep 5

    # Проверить
    $svc = Get-Service ProxifierSvc -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Output "Service status: $($svc.Status)"
    }

    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "Proxifier running: PID=$($proc.Id), MainWindow=$($proc.MainWindowHandle)"
    }

} else {
    Write-Output "NSSM: Failed to download"
}

Write-Output ""
Write-Output "=== Testing IP ==="
$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "Current IP: $ip"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=120)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
