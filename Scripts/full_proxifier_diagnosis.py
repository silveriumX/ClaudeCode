#!/usr/bin/env python3
"""
Полная диагностика профиля Proxifier и проверка прокси
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
    print("❌ Установите paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")


def execute_ssh(ps_command):
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
print("🔍 ПОЛНАЯ ДИАГНОСТИКА PROXIFIER")
print("="*80)

# 1. Вывести полный профиль
print("\n📋 Содержимое профиля Default.ppx:")
print("-" * 80)

read_profile = r'''
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
if (Test-Path $profilePath) {
    $content = [IO.File]::ReadAllText($profilePath)
    Write-Output $content
} else {
    Write-Output "ERROR:Profile not found"
}
'''

profile_content = execute_ssh(read_profile)
print(profile_content[:3000])  # Первые 3000 символов
print("-" * 80)

# 2. Проверить доступность прокси
print("\n📋 Проверка доступности прокси {os.getenv("PROXY_HOST")}:10010")

check_proxy = r'''
$result = Test-NetConnection -ComputerName {os.getenv("PROXY_HOST")} -Port 10010 -WarningAction SilentlyContinue
Write-Output "REACHABLE:$($result.TcpTestSucceeded)"
Write-Output "PING:$($result.PingSucceeded)"
'''

result = execute_ssh(check_proxy)
print(result)

# 3. Статус Proxifier
print("\n📋 Статус процесса Proxifier")

status_cmd = r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STATUS:Running"
    Write-Output "PID:$($proc.Id)"
    Write-Output "SESSION:$($proc.SessionId)"
    Write-Output "MEMORY:$([math]::Round($proc.WorkingSet64/1MB,2))MB"
} else {
    Write-Output "STATUS:Not running"
}
'''

result = execute_ssh(status_cmd)
print(result)

print("\n" + "="*80)
print("РЕКОМЕНДАЦИИ:")
print("="*80)
print("1. Проверьте в профиле теги <RuleList> — есть ли правила с type='Direct'")
print("2. Убедитесь что прокси доступен (TcpTestSucceeded должен быть True)")
print("3. Если прокси недоступен — измените порт или реквизиты на рабочие")
print("4. Если Rules указывают Direct — измените Action на Proxy с id прокси")
