#!/usr/bin/env python3
"""
Комплексная проверка и запуск Proxifier + тест прокси
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
    print("❌ Установите paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = 10001
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


def execute_ssh(ps_command, timeout=60):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False, allow_agent=False)

        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)

        output = stdout.read().decode("utf-8", errors="ignore").strip()
        return output
    except Exception as e:
        return f"ERROR:{e}"
    finally:
        if client:
            client.close()


print("="*80)
print("🔍 ДИАГНОСТИКА И ВОССТАНОВЛЕНИЕ PROXIFIER")
print("="*80)

# ШАГ 1: Проверить статус Proxifier
print("\n📋 Шаг 1: Проверка статуса Proxifier")

status_cmd = r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STATUS:✅ Запущен (PID=$($proc.Id), Session=$($proc.SessionId))"
} else {
    Write-Output "STATUS:❌ НЕ ЗАПУЩЕН - нужно запустить"
}
'''

result = execute_ssh(status_cmd)
print(result)

proxifier_running = "STATUS:✅" in result

if not proxifier_running:
    print("\n⚠️ Proxifier не запущен! Запускаю...")

    start_cmd = r'''
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
if (!(Test-Path $exePath)) {
    Write-Output "ERROR:Proxifier.exe не найден"
    exit 1
}

$taskName = "StartProxifier_$(Get-Date -Format 'HHmmss')"
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals>
    <Principal>
      <UserId>administrator</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
  </Settings>
  <Actions>
    <Exec>
      <Command>$exePath</Command>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\$taskName.xml"
[IO.File]::WriteAllText($xmlPath, $xml)
schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
schtasks /Run /TN $taskName 2>&1 | Out-Null

Write-Output "STARTING:Запуск..."
Start-Sleep -Seconds 4

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STARTED:✅ Запущен (PID=$($proc.Id))"
} else {
    Write-Output "FAILED:❌ Не запустился"
}

schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''

    result = execute_ssh(start_cmd)
    print(result)

    if "STARTED:✅" not in result:
        print("\n❌ Не удалось запустить Proxifier!")
    else:
        print("\n✅ Proxifier запущен, ждём 2 секунды...")
        time.sleep(2)

# ШАГ 2: Проверить профиль
print("\n📋 Шаг 2: Проверка профиля Proxifier")

check_profile_cmd = f'''
$profilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"
if (Test-Path $profilePath) {{
    $content = [IO.File]::ReadAllText($profilePath)

    if ($content -match '<Port>(\\d+)</Port>') {{
        Write-Output "PROFILE_PORT:$($Matches[1])"
    }}
    if ($content -match '<Address>(.*?)</Address>') {{
        Write-Output "PROFILE_ADDRESS:$($Matches[1])"
    }}

    $proxyCount = ([regex]::Matches($content, '<Proxy id=')).Count
    Write-Output "PROXY_COUNT:$proxyCount"

    # Проверить соответствие с нашими реквизитами
    if ($content -match '{PROXY_HOST}') {{
        Write-Output "HOST_MATCH:✅ Хост совпадает"
    }} else {{
        Write-Output "HOST_MATCH:❌ Хост не совпадает"
    }}

    if ($content -match '{PROXY_PORT}') {{
        Write-Output "PORT_MATCH:✅ Порт {PROXY_PORT} найден"
    }} else {{
        Write-Output "PORT_MATCH:❌ Порт {PROXY_PORT} не найден"
    }}
}} else {{
    Write-Output "ERROR:Профиль не найден"
}}
'''

result = execute_ssh(check_profile_cmd)
print(result)

# ШАГ 3: ПРЯМОЙ ТЕСТ ПРОКСИ через curl
print("\n" + "="*80)
print("📋 Шаг 3: ПРЯМОЙ ТЕСТ ПРОКСИ (через curl с SOCKS5)")
print("="*80)

test_proxy_cmd = f'''
Write-Output "Тестирование прокси {PROXY_HOST}:{PROXY_PORT}..."
Write-Output ""

# Прямое подключение (без прокси)
Write-Output "=== БЕЗ ПРОКСИ ==="
$directIp = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
if ($directIp) {{
    Write-Output "DIRECT_IP:$directIp (IP сервера)"
}} else {{
    Write-Output "DIRECT_IP:Ошибка"
}}

Write-Output ""
Write-Output "=== С ПРОКСИ (SOCKS5) ==="

# С прокси
$proxyUrl = "socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
Write-Output "Подключение через прокси..."

$output = curl.exe -x $proxyUrl -s --max-time 40 https://api.ipify.org 2>&1 | Out-String

if ($output -match '(\\d+\\.\\d+\\.\\d+\\.\\d+)') {{
    $proxyIp = $Matches[1]
    Write-Output "PROXY_IP:$proxyIp"

    if ($proxyIp -ne $directIp) {{
        Write-Output "RESULT:✅✅✅ УСПЕХ! IP изменился! Прокси РАБОТАЕТ!"
    }} else {{
        Write-Output "RESULT:❌ IP не изменился"
    }}
}} else {{
    Write-Output "PROXY_ERROR:$($output.Trim())"
    Write-Output "RESULT:❌ Прокси НЕ работает или неправильные реквизиты"
}}

Write-Output ""
Write-Output "=== АКТИВНЫЕ СОЕДИНЕНИЯ К ПРОКСИ ==="
$connections = Get-NetTCPConnection -RemoteAddress {PROXY_HOST} -ErrorAction SilentlyContinue
if ($connections) {{
    Write-Output "CONNECTIONS:$($connections.Count) активных"
    $connections | Select-Object -First 3 | ForEach-Object {{
        Write-Output "  RemotePort=$($_.RemotePort), State=$($_.State)"
    }}
}} else {{
    Write-Output "CONNECTIONS:Нет активных соединений"
}}
'''

print("Выполнение теста (до 40 секунд)...\n")
result = execute_ssh(test_proxy_cmd, timeout=90)
print(result)

# ШАГ 4: Проверка IP через Proxifier
print("\n" + "="*80)
print("📋 Шаг 4: Проверка IP через Proxifier (с его настройками)")
print("="*80)

check_proxifier_ip = r'''
Write-Output "Проверка IP с учётом Proxifier..."

# Дать Proxifier время применить настройки
Start-Sleep -Seconds 2

$ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
if ($ip) {
    if ($ip -eq "62.84.101.97") {
        Write-Output "PROXIFIER_IP:$ip ❌ (Proxifier НЕ применяет прокси)"
    } else {
        Write-Output "PROXIFIER_IP:$ip ✅ (Proxifier работает!)"
    }
} else {
    Write-Output "PROXIFIER_IP:Нет ответа"
}

# Статус процесса
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:✅ Работает (PID=$($proc.Id))"
} else {
    Write-Output "PROCESS:❌ Остановлен"
}
'''

result = execute_ssh(check_proxifier_ip)
print(result)

print("\n" + "="*80)
print("📊 ИТОГОВЫЙ АНАЛИЗ")
print("="*80)
print("\nСмотрите результаты выше:")
print("1. Если 'ПРЯМОЙ ТЕСТ ПРОКСИ' показал ✅ УСПЕХ")
print("   → Прокси работает, реквизиты правильные")
print("")
print("2. Если 'Proxifier IP' = 62.84.101.97 (IP сервера)")
print("   → Proxifier не применяет прокси")
print("   → Причины: неправильные Rules, профиль не загружен, или прокси не может подключиться")
print("")
print("3. Если 'ПРЯМОЙ ТЕСТ' ❌ не работает")
print("   → Проблема с самим прокси (реквизиты, доступность)")
