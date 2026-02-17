#!/usr/bin/env python3
"""
Установка ProxifierAgent на удалённый сервер
Агент работает в пользовательской сессии и управляет Proxifier
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64
import io
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")


def ssh(ps_command, timeout=60):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False, allow_agent=False)

        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)

        return stdout.read().decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"ERROR:{e}"
    finally:
        if client:
            client.close()


# PowerShell скрипт агента
AGENT_SCRIPT = r'''
# ProxifierAgent.ps1
# Управляет Proxifier: устанавливает прокси, перезапускает, проверяет IP

param(
    [string]$Action = "status",
    [string]$ProxyHost = "",
    [string]$ProxyPort = "",
    [string]$ProxyUser = "",
    [string]$ProxyPass = ""
)

$ErrorActionPreference = "SilentlyContinue"
$ProxifierPath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$ProfilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$ServerIP = "62.84.101.97"

function Get-ExternalIP {
    $ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
    return $ip
}

function Stop-Proxifier {
    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Name Proxifier -Force
        Start-Sleep -Seconds 2
        return $true
    }
    return $false
}

function Start-ProxifierInSession {
    # Создаём задачу для запуска в интерактивной сессии
    $taskName = "ProxifierAgent_Start_$(Get-Date -Format 'HHmmss')"
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
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec>
      <Command>$ProxifierPath</Command>
    </Exec>
  </Actions>
</Task>
"@

    $xmlPath = "$env:TEMP\$taskName.xml"
    [IO.File]::WriteAllText($xmlPath, $xml)

    schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
    schtasks /Run /TN $taskName 2>&1 | Out-Null

    Start-Sleep -Seconds 5

    schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
    Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue

    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    return ($proc -ne $null)
}

function Update-ProxifierProfile {
    param($Host, $Port, $User, $Pass)

    # Создаём новый профиль
    $newProfile = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxifierProfile version="102" platform="Windows" product_id="0" product_minver="400">
    <Options>
        <Resolve>
            <AutoModeDetection enabled="true" />
            <ViaProxy enabled="false" />
            <ExclusionList OnlyFromListMode="false">%ComputerName%; localhost; *.local</ExclusionList>
        </Resolve>
        <Encryption mode="basic" />
        <ConnectionLoopDetection enabled="true" resolve="true" />
        <HandleDirectConnections enabled="false" />
        <HttpProxiesSupport enabled="false" />
    </Options>
    <ProxyList>
        <Proxy id="100" type="SOCKS5">
            <Address>$Host</Address>
            <Port>$Port</Port>
            <Options>0</Options>
            <Authentication enabled="true">
                <Username>$User</Username>
                <Password>$Pass</Password>
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

    # Бэкап
    if (Test-Path $ProfilePath) {
        $backup = "$ProfilePath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $ProfilePath $backup -Force
    }

    # Записываем
    $encoding = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($ProfilePath, $newProfile, $encoding)

    return $true
}

function Test-ProxyWorking {
    param([int]$MaxAttempts = 3)

    for ($i = 1; $i -le $MaxAttempts; $i++) {
        $ip = Get-ExternalIP
        if ($ip -and $ip -ne $ServerIP) {
            return @{Success=$true; IP=$ip; Attempt=$i}
        }
        Start-Sleep -Seconds 2
    }

    return @{Success=$false; IP=$ip; Attempt=$MaxAttempts}
}

# Основная логика
switch ($Action) {
    "status" {
        $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
        $ip = Get-ExternalIP

        Write-Output "PROXIFIER:$(if($proc){'RUNNING:PID='+$proc.Id}else{'STOPPED'})"
        Write-Output "EXTERNAL_IP:$ip"
        Write-Output "PROXY_ACTIVE:$(if($ip -and $ip -ne $ServerIP){'YES'}else{'NO'})"
    }

    "set_proxy" {
        Write-Output "ACTION:Setting proxy $ProxyHost`:$ProxyPort"

        # 1. Остановить Proxifier
        Write-Output "STEP1:Stopping Proxifier..."
        Stop-Proxifier | Out-Null

        # 2. Обновить профиль
        Write-Output "STEP2:Updating profile..."
        Update-ProxifierProfile -Host $ProxyHost -Port $ProxyPort -User $ProxyUser -Pass $ProxyPass | Out-Null

        # 3. Запустить Proxifier
        Write-Output "STEP3:Starting Proxifier..."
        $started = Start-ProxifierInSession

        if (-not $started) {
            Write-Output "ERROR:Failed to start Proxifier"
            exit 1
        }

        Write-Output "STEP4:Waiting for proxy to initialize..."
        Start-Sleep -Seconds 5

        # 4. Проверить IP
        Write-Output "STEP5:Testing proxy..."
        $result = Test-ProxyWorking -MaxAttempts 5

        if ($result.Success) {
            Write-Output "SUCCESS:Proxy working! IP=$($result.IP)"
        } else {
            Write-Output "FAILED:Proxy not working. IP=$($result.IP)"
        }
    }

    "restart" {
        Write-Output "ACTION:Restarting Proxifier"
        Stop-Proxifier | Out-Null
        Start-Sleep -Seconds 2
        $started = Start-ProxifierInSession
        Write-Output "RESULT:$(if($started){'SUCCESS'}else{'FAILED'})"
    }

    "stop" {
        $stopped = Stop-Proxifier
        Write-Output "RESULT:$(if($stopped){'STOPPED'}else{'NOT_RUNNING'})"
    }

    default {
        Write-Output "Usage: ProxifierAgent.ps1 -Action <status|set_proxy|restart|stop>"
        Write-Output "  set_proxy: -ProxyHost <host> -ProxyPort <port> -ProxyUser <user> -ProxyPass <pass>"
    }
}
'''

print("="*80)
print("📦 УСТАНОВКА PROXIFIERAGENT НА СЕРВЕР")
print("="*80)

# 1. Создать директорию
print("\n📋 Шаг 1: Создание директории")

create_dir = r'''
$agentDir = "C:\ProxifierAgent"
if (!(Test-Path $agentDir)) {
    New-Item -ItemType Directory -Path $agentDir -Force | Out-Null
    Write-Output "CREATED:$agentDir"
} else {
    Write-Output "EXISTS:$agentDir"
}
'''

result = ssh(create_dir)
print(result)

# 2. Записать скрипт агента
print("\n📋 Шаг 2: Установка скрипта агента")

# Экранируем специальные символы для PowerShell
agent_script_escaped = AGENT_SCRIPT.replace('$', '`$').replace('"', '`"')

install_script = f'''
$scriptContent = @'
{AGENT_SCRIPT}
'@

$scriptPath = "C:\\ProxifierAgent\\ProxifierAgent.ps1"
[IO.File]::WriteAllText($scriptPath, $scriptContent)

if (Test-Path $scriptPath) {{
    Write-Output "INSTALLED:$scriptPath"
    Write-Output "SIZE:$((Get-Item $scriptPath).Length) bytes"
}} else {{
    Write-Output "ERROR:Failed to create script"
}}
'''

result = ssh(install_script)
print(result)

# 3. Проверить установку
print("\n📋 Шаг 3: Проверка установки")

verify = r'''
$script = "C:\ProxifierAgent\ProxifierAgent.ps1"
if (Test-Path $script) {
    Write-Output "VERIFIED:✅ Агент установлен"
    Write-Output "PATH:$script"
} else {
    Write-Output "ERROR:❌ Агент не найден"
}
'''

result = ssh(verify)
print(result)

print("\n" + "="*80)
print("✅ УСТАНОВКА ЗАВЕРШЕНА")
print("="*80)
print("\nТеперь можно использовать агента:")
print("  powershell -File C:\\ProxifierAgent\\ProxifierAgent.ps1 -Action status")
print("  powershell -File C:\\ProxifierAgent\\ProxifierAgent.ps1 -Action set_proxy -ProxyHost ... -ProxyPort ... -ProxyUser ... -ProxyPass ...")
