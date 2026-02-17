#!/usr/bin/env python3
"""
Полная замена профиля Proxifier с новыми реквизитами
Удаление всех старых прокси, создание нового профиля, проверка работы
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

# Данные сервера
SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

# НОВЫЕ реквизиты прокси
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = 10001
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")


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
print("🔄 ПОЛНАЯ ЗАМЕНА ПРОФИЛЯ PROXIFIER")
print("="*80)
print(f"\nНовый прокси: {PROXY_HOST}:{PROXY_PORT}")
print(f"Логин: {PROXY_USER}")
print(f"Пароль: {'*' * len(PROXY_PASS)}")

# ШАГ 1: Проверка доступности нового прокси
print("\n" + "="*80)
print("ШАГ 1: Проверка доступности прокси")
print("="*80)

check_proxy_cmd = f'''
Write-Output "Проверка доступности {PROXY_HOST}:{PROXY_PORT}..."
$result = Test-NetConnection -ComputerName {PROXY_HOST} -Port {PROXY_PORT} -WarningAction SilentlyContinue

Write-Output "PING_SUCCESS:$($result.PingSucceeded)"
Write-Output "TCP_SUCCESS:$($result.TcpTestSucceeded)"

if ($result.TcpTestSucceeded) {{
    Write-Output "✅ Прокси доступен на порту {PROXY_PORT}"
}} else {{
    Write-Output "⚠️ ПРЕДУПРЕЖДЕНИЕ: Порт {PROXY_PORT} не отвечает"
    Write-Output "Профиль будет создан, но прокси может не работать"
}}
'''

result = execute_ssh(check_proxy_cmd)
print(result)

# ШАГ 2: Создание полностью нового профиля
print("\n" + "="*80)
print("ШАГ 2: Создание нового профиля (удаление всех старых прокси)")
print("="*80)

create_profile_cmd = f'''
$profilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"

# Бэкап старого профиля
if (Test-Path $profilePath) {{
    $backupPath = "$profilePath.backup_complete_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $profilePath $backupPath -Force
    Write-Output "BACKUP:$backupPath"
}}

# Создать НОВЫЙ профиль с нуля
$newProfile = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxifierProfile version="102" platform="Windows" product_id="0" product_minver="400">
	<Options>
		<Resolve>
			<AutoModeDetection enabled="true" />
			<ViaProxy enabled="false" />
			<BlockNonATypes enabled="false" />
			<ExclusionList OnlyFromListMode="false">%ComputerName%; localhost; *.local</ExclusionList>
			<DnsUdpMode>0</DnsUdpMode>
		</Resolve>
		<Encryption mode="basic" />
		<ConnectionLoopDetection enabled="true" resolve="true" />
		<Udp mode="mode_bypass" />
		<LeakPreventionMode enabled="false" />
		<ProcessOtherUsers enabled="false" />
		<ProcessServices enabled="false" />
		<HandleDirectConnections enabled="false" />
		<HttpProxiesSupport enabled="false" />
	</Options>
	<ProxyList>
		<Proxy id="100" type="SOCKS5">
			<Address>{PROXY_HOST}</Address>
			<Port>{PROXY_PORT}</Port>
			<Options>0</Options>
			<Authentication enabled="true">
				<Username>{PROXY_USER}</Username>
				<Password>{PROXY_PASS}</Password>
			</Authentication>
		</Proxy>
	</ProxyList>
	<ChainList />
	<RuleList>
		<Rule enabled="true">
			<Name>Localhost</Name>
			<Targets>localhost; 127.0.0.1; %ComputerName%; ::1</Targets>
			<Action type="Direct" />
		</Rule>
		<Rule enabled="true">
			<Name>Default</Name>
			<Action type="Proxy">100</Action>
		</Rule>
	</RuleList>
</ProxifierProfile>
"@

# Записать новый профиль
$encoding = New-Object System.Text.UTF8Encoding `$false
[IO.File]::WriteAllText($profilePath, $newProfile, $encoding)
Write-Output "PROFILE_CREATED:Новый профиль создан"

# Проверка
$content = [IO.File]::ReadAllText($profilePath)
if ($content -match '<Port>{PROXY_PORT}</Port>' -and $content -match '<Username>{PROXY_USER}</Username>') {{
    Write-Output "VERIFIED:✅ Профиль содержит правильные реквизиты"

    # Подсчитать количество прокси
    $proxyCount = ([regex]::Matches($content, '<Proxy id=')).Count
    Write-Output "PROXY_COUNT:$proxyCount (должен быть 1)"
}} else {{
    Write-Output "ERROR:❌ Проверка профиля не удалась"
}}
'''

result = execute_ssh(create_profile_cmd)
print(result)

if "ERROR:" in result:
    print("\n❌ Не удалось создать профиль!")
    sys.exit(1)

# ШАГ 3: Остановить Proxifier
print("\n" + "="*80)
print("ШАГ 3: Остановка Proxifier")
print("="*80)

stop_cmd = r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STOPPING:Найден процесс PID=$($proc.Id)"
    Stop-Process -Name Proxifier -Force
    Start-Sleep -Seconds 2
    Write-Output "STOPPED:✅ Proxifier остановлен"
} else {
    Write-Output "NOT_RUNNING:Proxifier не запущен"
}
'''

result = execute_ssh(stop_cmd)
print(result)

# ШАГ 4: Запустить Proxifier с новым профилем
print("\n" + "="*80)
print("ШАГ 4: Запуск Proxifier с новым профилем")
print("="*80)

start_cmd = r'''
$exePath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"

if (!(Test-Path $exePath)) {
    Write-Output "ERROR:Proxifier.exe не найден"
    exit 1
}

# Создать задачу для запуска в пользовательской сессии
$taskName = "StartProxifierNew_$(Get-Date -Format 'HHmmss')"
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

Write-Output "STARTING:Запуск Proxifier..."
Start-Sleep -Seconds 3

$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "STARTED:✅ Proxifier запущен (PID=$($proc.Id), Session=$($proc.SessionId))"
} else {
    Write-Output "WARNING:⚠️ Процесс не обнаружен (может запускаться)"
}

# Cleanup
schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
'''

result = execute_ssh(start_cmd)
print(result)

# ШАГ 5: Подождать инициализации
print("\n⏱️  Ждём 5 секунд для инициализации Proxifier...")
time.sleep(5)

# ШАГ 6: Проверка работы прокси
print("\n" + "="*80)
print("ШАГ 5: ПРОВЕРКА РАБОТЫ ПРОКСИ")
print("="*80)

check_working_cmd = r'''
# 1. Проверить процесс
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "PROCESS:✅ Запущен (PID=$($proc.Id), Session=$($proc.SessionId), Memory=$([math]::Round($proc.WorkingSet64/1MB,2))MB)"
} else {
    Write-Output "PROCESS:❌ Не запущен"
}

# 2. Проверить профиль
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$content = [IO.File]::ReadAllText($profilePath)

if ($content -match '<Port>(\d+)</Port>') {
    Write-Output "PROFILE_PORT:$($Matches[1])"
}
if ($content -match '<Address>(.*?)</Address>') {
    Write-Output "PROFILE_ADDRESS:$($Matches[1])"
}

$proxyCount = ([regex]::Matches($content, '<Proxy id=')).Count
Write-Output "PROFILE_PROXIES:$proxyCount"

# 3. Проверить внешний IP
Write-Output ""
Write-Output "Проверка внешнего IP (через прокси)..."
Write-Output "Исходный IP сервера: 62.84.101.97"

try {
    $ip = curl.exe -s --max-time 20 https://api.ipify.org 2>$null
    if ($ip) {
        if ($ip -eq "62.84.101.97") {
            Write-Output "EXTERNAL_IP:$ip ❌ (Прокси НЕ работает - это IP сервера)"
        } else {
            Write-Output "EXTERNAL_IP:$ip ✅ (Прокси РАБОТАЕТ - IP изменился!)"
        }
    } else {
        Write-Output "EXTERNAL_IP:Нет ответа (возможно прокси блокирует или нет соединения)"
    }
} catch {
    Write-Output "EXTERNAL_IP:Ошибка проверки"
}

# 4. Попробовать найти логи Proxifier
Write-Output ""
Write-Output "Поиск логов Proxifier..."

$logPaths = @(
    "$env:APPDATA\Proxifier4\Logs",
    "$env:ProgramData\Proxifier\Logs",
    "C:\ProgramData\Proxifier\Logs"
)

$logsFound = $false
foreach ($logPath in $logPaths) {
    if (Test-Path $logPath) {
        $logs = Get-ChildItem $logPath -Filter "*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($logs) {
            Write-Output "LOG_FILE:$($logs.FullName)"
            Write-Output "LOG_SIZE:$([math]::Round($logs.Length/1KB,2)) KB"
            Write-Output "LOG_MODIFIED:$($logs.LastWriteTime)"

            # Прочитать последние 10 строк
            $logContent = Get-Content $logs.FullName -Tail 10 -ErrorAction SilentlyContinue
            if ($logContent) {
                Write-Output "LOG_LAST_LINES:"
                $logContent | ForEach-Object { Write-Output "  $_" }
            }
            $logsFound = $true
            break
        }
    }
}

if (-not $logsFound) {
    Write-Output "LOG_STATUS:Логи не найдены или логирование отключено"
}
'''

result = execute_ssh(check_working_cmd)
print(result)

# ИТОГ
print("\n" + "="*80)
print("✅ ПРОЦЕСС ЗАВЕРШЁН")
print("="*80)
print(f"\n📋 Создан новый профиль Proxifier:")
print(f"   Прокси: {PROXY_HOST}:{PROXY_PORT}")
print(f"   Все старые прокси удалены")
print(f"   Proxifier перезапущен")
print("\n📊 Проверьте результаты выше:")
print("   - EXTERNAL_IP должен отличаться от 62.84.101.97")
print("   - Если IP изменился = прокси работает ✅")
print("   - Если IP остался тот же = прокси не работает ❌")
