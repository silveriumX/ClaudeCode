#!/usr/bin/env python3
"""
Установка ProxifierAgent v2 - через Base64
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


# PowerShell скрипт агента (ASCII-safe)
AGENT_SCRIPT = '''
param(
    [string]$Action = "status",
    [string]$ProxyHost = "",
    [string]$ProxyPort = "",
    [string]$ProxyUser = "",
    [string]$ProxyPass = ""
)

$ErrorActionPreference = "SilentlyContinue"
$ProxifierPath = "C:\\Program Files (x86)\\Proxifier\\Proxifier.exe"
$ProfilePath = "$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx"
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
    $taskName = "ProxifierAgent_Start"
    $taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals><Principal><UserId>administrator</UserId><LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><AllowStartOnDemand>true</AllowStartOnDemand></Settings>
  <Actions><Exec><Command>$ProxifierPath</Command></Exec></Actions>
</Task>
"@

    $xmlPath = "$env:TEMP\\$taskName.xml"
    [IO.File]::WriteAllText($xmlPath, $taskXml)

    schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
    schtasks /Create /TN $taskName /XML $xmlPath /F 2>&1 | Out-Null
    schtasks /Run /TN $taskName 2>&1 | Out-Null

    Start-Sleep -Seconds 5

    schtasks /Delete /TN $taskName /F 2>&1 | Out-Null
    Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue

    $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
    return ($proc -ne $null)
}

function Update-Profile {
    param($PHost, $PPort, $PUser, $PPass)

    $xml = "<?xml version=`"1.0`" encoding=`"UTF-8`" standalone=`"yes`"?>`n"
    $xml += "<ProxifierProfile version=`"102`" platform=`"Windows`" product_id=`"0`" product_minver=`"400`">`n"
    $xml += "<Options><Resolve><AutoModeDetection enabled=`"true`"/></Resolve><HttpProxiesSupport enabled=`"false`"/></Options>`n"
    $xml += "<ProxyList><Proxy id=`"100`" type=`"SOCKS5`"><Address>$PHost</Address><Port>$PPort</Port><Options>0</Options>"
    $xml += "<Authentication enabled=`"true`"><Username>$PUser</Username><Password>$PPass</Password></Authentication></Proxy></ProxyList>`n"
    $xml += "<ChainList/>`n"
    $xml += "<RuleList><Rule enabled=`"true`"><Name>Localhost</Name><Targets>localhost;127.0.0.1</Targets><Action type=`"Direct`"/></Rule>"
    $xml += "<Rule enabled=`"true`"><Name>Default</Name><Action type=`"Proxy`">100</Action></Rule></RuleList>`n"
    $xml += "</ProxifierProfile>"

    if (Test-Path $ProfilePath) {
        Copy-Item $ProfilePath "$ProfilePath.bak" -Force
    }

    $enc = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($ProfilePath, $xml, $enc)
    return $true
}

switch ($Action) {
    "status" {
        $proc = Get-Process Proxifier -ErrorAction SilentlyContinue
        $ip = Get-ExternalIP
        Write-Output "PROXIFIER:$(if($proc){'RUNNING:PID='+$proc.Id}else{'STOPPED'})"
        Write-Output "EXTERNAL_IP:$ip"
        Write-Output "PROXY_ACTIVE:$(if($ip -and $ip -ne $ServerIP){'YES'}else{'NO'})"
    }

    "set_proxy" {
        Write-Output "ACTION:set_proxy $ProxyHost`:$ProxyPort"

        Write-Output "STEP1:Stopping..."
        Stop-Proxifier | Out-Null

        Write-Output "STEP2:Updating profile..."
        Update-Profile -PHost $ProxyHost -PPort $ProxyPort -PUser $ProxyUser -PPass $ProxyPass | Out-Null

        Write-Output "STEP3:Starting..."
        $started = Start-ProxifierInSession
        if (-not $started) {
            Write-Output "ERROR:Start failed"
            exit 1
        }

        Write-Output "STEP4:Testing (10s)..."
        Start-Sleep -Seconds 10

        $ip = Get-ExternalIP
        if ($ip -and $ip -ne $ServerIP) {
            Write-Output "SUCCESS:IP=$ip"
        } else {
            Write-Output "FAILED:IP=$ip (still server IP)"
        }
    }

    "restart" {
        Stop-Proxifier | Out-Null
        Start-Sleep 2
        $ok = Start-ProxifierInSession
        Write-Output "RESULT:$(if($ok){'OK'}else{'FAIL'})"
    }

    "stop" {
        $ok = Stop-Proxifier
        Write-Output "RESULT:$(if($ok){'STOPPED'}else{'NOT_RUNNING'})"
    }
}
'''


print("="*80)
print("📦 УСТАНОВКА PROXIFIERAGENT V2")
print("="*80)

# Кодируем скрипт в Base64
script_bytes = AGENT_SCRIPT.encode('utf-8')
script_b64 = base64.b64encode(script_bytes).decode('ascii')

print(f"\n📋 Размер скрипта: {len(AGENT_SCRIPT)} символов")
print(f"📋 Размер Base64: {len(script_b64)} символов")

# Создаём директорию и записываем скрипт через Base64
install_cmd = f'''
# Создать директорию
$dir = "C:\\ProxifierAgent"
if (!(Test-Path $dir)) {{
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}}

# Декодировать и записать скрипт
$b64 = "{script_b64}"
$bytes = [Convert]::FromBase64String($b64)
$script = [System.Text.Encoding]::UTF8.GetString($bytes)

$path = "$dir\\ProxifierAgent.ps1"
[IO.File]::WriteAllText($path, $script, [System.Text.Encoding]::UTF8)

# Проверить
if (Test-Path $path) {{
    $size = (Get-Item $path).Length
    Write-Output "INSTALLED:$path ($size bytes)"
}} else {{
    Write-Output "ERROR:Failed"
}}
'''

print("\n📋 Установка скрипта...")
result = ssh(install_cmd)
print(result)

# Проверяем что скрипт работает
print("\n📋 Тестируем агента (status)...")

test_cmd = r'''
powershell.exe -ExecutionPolicy Bypass -File "C:\ProxifierAgent\ProxifierAgent.ps1" -Action status
'''

result = ssh(test_cmd)
print(result)

print("\n" + "="*80)
print("✅ УСТАНОВКА ЗАВЕРШЕНА")
print("="*80)
