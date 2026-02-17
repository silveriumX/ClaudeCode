#!/usr/bin/env python3
"""
Тест: подключение к 62.84.101.97 и изменение прокси в Proxifier
Меняем порт с 10000 на 10010 и перезапускаем Proxifier
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

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

try:
    import paramiko
except ImportError:
    print("❌ Установите paramiko: pip install paramiko")
    sys.exit(1)

# Данные сервера
SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

# Новые реквизиты прокси (меняем порт с 10000 на 10010)
PROXY_PROTOCOL = "SOCKS5"
PROXY_ADDRESS = os.getenv("PROXY_HOST")
PROXY_PORT = 10010  # Меняем на 10010
PROXY_USER = "1fb08611c4d557ac8f22_c_US_s_Hub62"
PROXY_PASS = "n2yhff6z7fC1VBBKi8QvoGeSr9LYm5Li"


def execute_ssh_command(ps_command):
    """Выполнить PowerShell команду через SSH"""
    client = None
    try:
        print(f"\n🔌 Подключение к {SSH_HOST}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            SSH_HOST,
            username=SSH_USER,
            password=SSH_PASS,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
        print("✅ SSH подключение установлено")

        # Кодируем команду в Base64 UTF-16LE
        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"

        print(f"📝 Выполнение команды...")
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=60)

        output = stdout.read().decode("utf-8", errors="ignore").strip()
        error = stderr.read().decode("utf-8", errors="ignore").strip()

        if error and not output:
            print(f"⚠️ stderr: {error[:500]}")

        return output, error

    except Exception as e:
        print(f"❌ Ошибка SSH: {e}")
        return None, str(e)
    finally:
        if client:
            client.close()


def main():
    print("="*80)
    print("🔧 ТЕСТ ИЗМЕНЕНИЯ PROXIFIER ЧЕРЕЗ SSH")
    print("="*80)
    print(f"\nСервер: {SSH_HOST}")
    print(f"Новый прокси: {PROXY_PROTOCOL}://{PROXY_ADDRESS}:{PROXY_PORT}")

    # Шаг 1: Найти и прочитать профиль
    print("\n" + "="*80)
    print("ШАГ 1: Проверка профиля Proxifier")
    print("="*80)

    check_cmd = r'''
$paths = @(
    "$env:APPDATA\Proxifier4\Profiles\Default.ppx",
    "$env:ProgramData\Proxifier\Default.ppx",
    "C:\ProgramData\Proxifier\Default.ppx"
)
$found = $null
foreach ($p in $paths) {
    if (Test-Path $p) {
        $found = $p
        Write-Output "PROFILE_FOUND:$p"
        break
    }
}
if (-not $found) {
    Write-Output "ERROR:Profile not found"
    exit 1
}

# Проверяем текущее содержимое
$content = [IO.File]::ReadAllText($found)
if ($content -match '<Proxy.*?id="100".*?<Port>(\d+)</Port>') {
    Write-Output "CURRENT_PORT:$($Matches[1])"
}
if ($content -match '<ProxyList>.*?</ProxyList>') {
    Write-Output "HAS_PROXYLIST:YES"
} else {
    Write-Output "HAS_PROXYLIST:NO"
}
'''

    output, error = execute_ssh_command(check_cmd)
    if output:
        print("\n📋 Результат проверки:")
        for line in output.splitlines():
            print(f"   {line}")
        if "ERROR:" in output:
            print("\n❌ Профиль не найден!")
            return 1

    # Шаг 2: Изменить прокси
    print("\n" + "="*80)
    print("ШАГ 2: Изменение прокси в профиле")
    print("="*80)

    change_cmd = f'''
$protocol = "{PROXY_PROTOCOL}"
$address = "{PROXY_ADDRESS}"
$port = {PROXY_PORT}
$user = "{PROXY_USER}"
$pass = "{PROXY_PASS}"

# Найти профиль
$profilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"
if (!(Test-Path $profilePath)) {{
    $profilePath = "$env:ProgramData\\Proxifier\\Default.ppx"
}}
if (!(Test-Path $profilePath)) {{
    Write-Output "ERROR:Profile not found"
    exit 1
}}

Write-Output "PROFILE:$profilePath"

# Создать бэкап
$backupPath = "$profilePath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $profilePath $backupPath -Force
Write-Output "BACKUP:$backupPath"

# Прочитать содержимое
$content = [IO.File]::ReadAllText($profilePath)
Write-Output "FILE_SIZE:$($content.Length) bytes"

# Создать новый ProxyList блок
$newProxyList = @"
<ProxyList><Proxy id="100" type="$protocol"><Address>$address</Address><Port>$port</Port><Options>0</Options><Authentication enabled="true"><Username>$user</Username><Password>$pass</Password></Authentication></Proxy></ProxyList>
"@

Write-Output "NEW_PROXY:$protocol`://$address`:$port"

# Заменить ProxyList
if ($content -match '<ProxyList\\s*/>') {{
    $content = $content -replace '<ProxyList\\s*/>', $newProxyList
    Write-Output "REPLACED:Empty ProxyList tag"
}} elseif ($content -match '<ProxyList>.*?</ProxyList>') {{
    $content = $content -replace '<ProxyList>.*?</ProxyList>', $newProxyList
    Write-Output "REPLACED:Existing ProxyList"
}} else {{
    # ProxyList вообще нет - вставить перед </ProxifierProfile>
    if ($content -match '</ProxifierProfile>') {{
        $content = $content -replace '</ProxifierProfile>', "$newProxyList`n</ProxifierProfile>"
        Write-Output "INSERTED:ProxyList added before closing tag"
    }} else {{
        Write-Output "ERROR:Could not find insertion point"
        exit 1
    }}
}}

# Записать файл (UTF-8 without BOM)
$encoding = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($profilePath, $content, $encoding)
Write-Output "FILE_WRITTEN:$profilePath"

# Проверить что записалось
$newContent = [IO.File]::ReadAllText($profilePath)
if ($newContent -match '<Port>{PROXY_PORT}</Port>') {{
    Write-Output "VERIFY:Port {PROXY_PORT} found in file"
}} else {{
    Write-Output "WARNING:Port {PROXY_PORT} not found in file"
}}
'''

    output, error = execute_ssh_command(change_cmd)
    if output:
        print("\n📋 Результат изменения:")
        for line in output.splitlines():
            if "ERROR:" in line:
                print(f"   ❌ {line}")
            elif any(x in line for x in ["BACKUP:", "REPLACED:", "FILE_WRITTEN:", "VERIFY:"]):
                print(f"   ✅ {line}")
            else:
                print(f"   {line}")

        if "ERROR:" in output:
            print("\n❌ Не удалось изменить файл!")
            return 1

    # Шаг 3: Перезапустить Proxifier
    print("\n" + "="*80)
    print("ШАГ 3: Перезапуск Proxifier")
    print("="*80)

    restart_cmd = r'''
# Проверить запущен ли Proxifier
$running = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($running) {
    Write-Output "PROXIFIER_RUNNING:PID=$($running.Id)"

    # Остановить Proxifier
    Stop-Process -Name Proxifier -Force
    Write-Output "PROXIFIER_STOPPED"
    Start-Sleep -Seconds 2
} else {
    Write-Output "PROXIFIER_NOT_RUNNING"
}

# Найти путь к Proxifier.exe
$paths = @(
    "C:\Program Files (x86)\Proxifier\Proxifier.exe",
    "C:\Program Files\Proxifier\Proxifier.exe",
    "C:\Proxifier\Proxifier.exe"
)

$exePath = $null
foreach ($p in $paths) {
    if (Test-Path $p) {
        $exePath = $p
        Write-Output "PROXIFIER_PATH:$p"
        break
    }
}

if (-not $exePath) {
    Write-Output "ERROR:Proxifier.exe not found"
    exit 1
}

# Запустить Proxifier через Task Scheduler (от SYSTEM)
$taskName = "StartProxifierTest"
schtasks /Delete /TN $taskName /F 2>$null | Out-Null
$result = schtasks /Create /TN $taskName /TR "`"$exePath`"" /SC ONCE /ST 00:00 /RU SYSTEM /F 2>&1
Write-Output "TASK_CREATE:$result"

$result = schtasks /Run /TN $taskName 2>&1
Write-Output "TASK_RUN:$result"

Start-Sleep -Seconds 3

# Проверить запустился ли
$newProcess = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($newProcess) {
    Write-Output "PROXIFIER_STARTED:PID=$($newProcess.Id)"
} else {
    Write-Output "WARNING:Proxifier not detected in process list"
}

# Удалить задачу
schtasks /Delete /TN $taskName /F 2>$null | Out-Null
Write-Output "TASK_CLEANUP:Done"
'''

    output, error = execute_ssh_command(restart_cmd)
    if output:
        print("\n📋 Результат перезапуска:")
        for line in output.splitlines():
            if "ERROR:" in line or "WARNING:" in line:
                print(f"   ⚠️ {line}")
            elif any(x in line for x in ["STARTED:", "STOPPED:", "RUNNING:"]):
                print(f"   ✅ {line}")
            else:
                print(f"   {line}")

    # Шаг 4: Финальная проверка
    print("\n" + "="*80)
    print("ШАГ 4: Проверка текущего IP через прокси")
    print("="*80)

    check_ip_cmd = r'''
try {
    # Попробовать проверить IP через curl (если доступен)
    $ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
    if ($ip) {
        Write-Output "CURRENT_IP:$ip"
    } else {
        Write-Output "IP_CHECK:curl failed"
    }
} catch {
    Write-Output "IP_CHECK:Not available"
}

# Проверить что Proxifier запущен
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROXIFIER_STATUS:Running (PID=$($proc.Id))"
} else {
    Write-Output "PROXIFIER_STATUS:Not running"
}
'''

    output, error = execute_ssh_command(check_ip_cmd)
    if output:
        print("\n📋 Финальная проверка:")
        for line in output.splitlines():
            print(f"   {line}")

    print("\n" + "="*80)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("="*80)
    print(f"\nПрокси изменён на: {PROXY_PROTOCOL}://{PROXY_ADDRESS}:{PROXY_PORT}")
    print("Proxifier перезапущен")

    return 0


if __name__ == "__main__":
    sys.exit(main())
