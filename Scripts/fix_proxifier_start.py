#!/usr/bin/env python3
"""
Исправление проблемы запуска Proxifier
Используем альтернативные методы запуска
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64
import io
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

try:
    import paramiko
except ImportError:
    print("❌ Установите paramiko: pip install paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")


def execute_ssh(ps_command):
    """Выполнить PowerShell через SSH"""
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False, allow_agent=False)

        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=60)

        output = stdout.read().decode("utf-8", errors="ignore").strip()
        return output
    except Exception as e:
        return f"ERROR:{e}"
    finally:
        if client:
            client.close()


print("="*80)
print("🔍 ДИАГНОСТИКА И ИСПРАВЛЕНИЕ ЗАПУСКА PROXIFIER")
print("="*80)

# Метод 1: Попробуем разные способы запуска
print("\n📋 Попытка 1: Прямой запуск через Start-Process")

cmd1 = r'''
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
if (Test-Path $exePath) {
    try {
        Start-Process -FilePath $exePath -WindowStyle Minimized
        Start-Sleep -Seconds 3
        $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Output "SUCCESS:Proxifier started (PID=$($proc.Id))"
        } else {
            Write-Output "FAILED:Process not found after start"
        }
    } catch {
        Write-Output "ERROR:$($_.Exception.Message)"
    }
} else {
    Write-Output "ERROR:Proxifier.exe not found"
}
'''

result = execute_ssh(cmd1)
print(result)

if "SUCCESS:" not in result:
    print("\n📋 Попытка 2: Запуск с полными правами через WMI")

    cmd2 = r'''
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
try {
    $process = ([wmiclass]"Win32_Process").Create($exePath)
    if ($process.ReturnValue -eq 0) {
        Write-Output "WMI_SUCCESS:ProcessID=$($process.ProcessId)"
        Start-Sleep -Seconds 3
        $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Output "VERIFIED:Proxifier running (PID=$($proc.Id))"
        } else {
            Write-Output "WARNING:Process not in list"
        }
    } else {
        Write-Output "WMI_ERROR:ReturnValue=$($process.ReturnValue)"
    }
} catch {
    Write-Output "ERROR:$($_.Exception.Message)"
}
'''

    result = execute_ssh(cmd2)
    print(result)

if "SUCCESS:" not in result and "VERIFIED:" not in result:
    print("\n📋 Попытка 3: Запуск через cmd.exe start")

    cmd3 = r'''
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
try {
    cmd.exe /c start "" "$exePath"
    Start-Sleep -Seconds 3
    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "CMD_SUCCESS:Proxifier started (PID=$($proc.Id))"
    } else {
        Write-Output "CMD_FAILED:Process not found"
    }
} catch {
    Write-Output "ERROR:$($_.Exception.Message)"
}
'''

    result = execute_ssh(cmd3)
    print(result)

# Проверка финальная
print("\n📋 Финальная проверка состояния:")

check_cmd = r'''
# Проверить процесс
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:Running (PID=$($proc.Id), Memory=$([math]::Round($proc.WorkingSet64/1MB,2))MB)"
} else {
    Write-Output "PROCESS:Not running"
}

# Проверить прокси в профиле
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
if (Test-Path $profilePath) {
    $content = [IO.File]::ReadAllText($profilePath)
    if ($content -match '<Port>(\d+)</Port>') {
        Write-Output "PROFILE_PORT:$($Matches[1])"
    }
    if ($content -match '<Address>(.*?)</Address>') {
        Write-Output "PROFILE_ADDRESS:$($Matches[1])"
    }
}

# Проверить IP
try {
    $ip = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing -TimeoutSec 10).Content
    Write-Output "CURRENT_IP:$ip"
} catch {
    Write-Output "IP_CHECK:Failed"
}
'''

result = execute_ssh(check_cmd)
print(result)

print("\n" + "="*80)
