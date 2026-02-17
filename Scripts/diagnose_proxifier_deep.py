#!/usr/bin/env python3
"""
Углублённая диагностика проблемы Proxifier
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
print("🔍 ГЛУБОКАЯ ДИАГНОСТИКА PROXIFIER")
print("="*80)

# 1. Проверить логи Proxifier
print("\n📋 Шаг 1: Поиск логов Proxifier")

cmd_logs = r'''
$logPaths = @(
    "$env:APPDATA\Proxifier4\Logs",
    "$env:ProgramData\Proxifier\Logs",
    "C:\ProgramData\Proxifier\Logs",
    "$env:LOCALAPPDATA\Proxifier\Logs"
)

foreach ($path in $logPaths) {
    if (Test-Path $path) {
        Write-Output "LOG_DIR:$path"
        $logs = Get-ChildItem $path -Filter "*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 3
        foreach ($log in $logs) {
            Write-Output "LOG_FILE:$($log.FullName) (Size=$($log.Length), Modified=$($log.LastWriteTime))"
        }
    }
}

# Проверить Event Log
$events = Get-WinEvent -LogName Application -MaxEvents 20 -ErrorAction SilentlyContinue | Where-Object {$_.ProviderName -like "*Proxifier*" -or $_.Message -like "*Proxifier*"}
if ($events) {
    Write-Output "EVENT_LOG:Found $($events.Count) Proxifier events"
    $events | Select-Object -First 3 | ForEach-Object {
        Write-Output "EVENT:[$($_.TimeCreated)] Level=$($_.Level) Message=$($_.Message.Substring(0, [Math]::Min(100, $_.Message.Length)))"
    }
}
'''

result = execute_ssh(cmd_logs)
print(result if result else "Логи не найдены")

# 2. Проверить валидность профиля
print("\n📋 Шаг 2: Валидация XML профиля")

cmd_validate = r'''
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
if (Test-Path $profilePath) {
    $content = [IO.File]::ReadAllText($profilePath)

    # Попробовать загрузить как XML
    try {
        $xml = [xml]$content
        Write-Output "XML_VALID:Profile is valid XML"

        # Проверить основные теги
        if ($xml.ProxifierProfile) {
            Write-Output "TAG_ROOT:ProxifierProfile exists"
        }
        if ($xml.ProxifierProfile.ProxyList) {
            Write-Output "TAG_PROXYLIST:Exists"
            $proxyCount = @($xml.ProxifierProfile.ProxyList.Proxy).Count
            Write-Output "PROXY_COUNT:$proxyCount"
        }
    } catch {
        Write-Output "XML_INVALID:$($_.Exception.Message)"
        # Показать первые 500 символов
        Write-Output "CONTENT_PREVIEW:$($content.Substring(0, [Math]::Min(500, $content.Length)))"
    }
} else {
    Write-Output "ERROR:Profile not found"
}
'''

result = execute_ssh(cmd_validate)
print(result)

# 3. Попробовать запуск с выводом ошибок
print("\n📋 Шаг 3: Запуск с захватом ошибок")

cmd_start_debug = r'''
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"

# Создать временный скрипт для запуска и мониторинга
$scriptPath = "$env:TEMP\start_proxifier_debug.ps1"
$scriptContent = @"
`$proc = Start-Process -FilePath '$exePath' -PassThru -ErrorAction Stop
Start-Sleep -Seconds 5
if (Get-Process -Id `$proc.Id -ErrorAction SilentlyContinue) {
    Write-Output "STILL_RUNNING:PID=`$(`$proc.Id)"
} else {
    Write-Output "PROCESS_EXITED:within 5 seconds"
}
"@

[IO.File]::WriteAllText($scriptPath, $scriptContent)

try {
    $output = & powershell.exe -ExecutionPolicy Bypass -File $scriptPath 2>&1
    Write-Output $output
} catch {
    Write-Output "ERROR:$($_.Exception.Message)"
} finally {
    Remove-Item $scriptPath -Force -ErrorAction SilentlyContinue
}
'''

result = execute_ssh(cmd_start_debug)
print(result)

# 4. Проверить, нужна ли активная сессия пользователя
print("\n📋 Шаг 4: Проверка сессий пользователя")

cmd_sessions = r'''
# Проверить активные сессии
$sessions = quser 2>&1
if ($sessions -notlike "*No User*") {
    Write-Output "SESSIONS:$sessions"
} else {
    Write-Output "SESSIONS:No active user sessions"
}

# Проверить, запущен ли explorer (GUI)
$explorer = Get-Process explorer -ErrorAction SilentlyContinue
if ($explorer) {
    Write-Output "EXPLORER:Running (session indicates active GUI)"
} else {
    Write-Output "EXPLORER:Not running (no GUI session)"
}
'''

result = execute_ssh(cmd_sessions)
print(result)

print("\n" + "="*80)
print("📊 ИТОГ ДИАГНОСТИКИ")
print("="*80)
