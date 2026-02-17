#!/usr/bin/env python3
"""
Прямой тест агента на сервере
"""
import base64
import io
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")


def ssh(ps_command, timeout=90):
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


print("="*80)
print("🔍 ПРОВЕРКА АГЕНТА")
print("="*80)

# 1. Проверить файл
print("\n📋 Проверка файла агента:")
result = ssh(r'''
$path = "C:\ProxifierAgent\ProxifierAgent.ps1"
if (Test-Path $path) {
    $size = (Get-Item $path).Length
    Write-Output "EXISTS:$path"
    Write-Output "SIZE:$size bytes"

    # Показать первые 10 строк
    Write-Output "CONTENT_PREVIEW:"
    Get-Content $path -Head 10 | ForEach-Object { Write-Output "  $_" }
} else {
    Write-Output "NOT_FOUND:$path"
}
''')
print(result)

# 2. Если не найден - создать простую версию
if "NOT_FOUND" in result:
    print("\n📋 Создаём упрощённую версию агента...")

    simple_agent = r'''
$path = "C:\ProxifierAgent\ProxifierAgent.ps1"
$dir = Split-Path $path
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$script = @'
# Simple Proxifier Agent
param([string]$Action = "status", [string]$ProxyHost, [string]$ProxyPort, [string]$ProxyUser, [string]$ProxyPass)

$ProxifierPath = "C:\Program Files (x86)\Proxifier\Proxifier.exe"
$ProfilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
$ServerIP = "62.84.101.97"

switch ($Action) {
    "status" {
        $proc = Get-Process Proxifier -EA 0
        $ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
        Write-Output "PROXIFIER:$(if($proc){'RUNNING:PID='+$proc.Id}else{'STOPPED'})"
        Write-Output "IP:$ip"
        Write-Output "PROXY_OK:$(if($ip -and $ip -ne $ServerIP){'YES'}else{'NO'})"
    }
    "set_proxy" {
        Write-Output "1.STOP"
        Stop-Process -Name Proxifier -Force -EA 0
        Start-Sleep 2

        Write-Output "2.PROFILE"
        $xml = "<?xml version=`"1.0`" encoding=`"UTF-8`"?><ProxifierProfile version=`"102`" platform=`"Windows`"><Options/><ProxyList><Proxy id=`"100`" type=`"SOCKS5`"><Address>$ProxyHost</Address><Port>$ProxyPort</Port><Authentication enabled=`"true`"><Username>$ProxyUser</Username><Password>$ProxyPass</Password></Authentication></Proxy></ProxyList><RuleList><Rule enabled=`"true`"><Name>Direct</Name><Targets>localhost;127.0.0.1</Targets><Action type=`"Direct`"/></Rule><Rule enabled=`"true`"><Name>Proxy</Name><Action type=`"Proxy`">100</Action></Rule></RuleList></ProxifierProfile>"
        $xml | Out-File -FilePath $ProfilePath -Encoding utf8 -Force

        Write-Output "3.START"
        $tn = "StartProx"
        schtasks /Delete /TN $tn /F 2>$null
        schtasks /Create /TN $tn /TR "`"$ProxifierPath`"" /SC ONCE /ST 00:00 /RL HIGHEST /F 2>$null
        schtasks /Run /TN $tn 2>$null
        Start-Sleep 8
        schtasks /Delete /TN $tn /F 2>$null

        Write-Output "4.CHECK"
        $ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
        if ($ip -and $ip -ne $ServerIP) {
            Write-Output "SUCCESS:$ip"
        } else {
            Write-Output "FAILED:$ip"
        }
    }
}
'@

$script | Out-File -FilePath $path -Encoding utf8 -Force

if (Test-Path $path) {
    Write-Output "CREATED:$path"
} else {
    Write-Output "ERROR:failed"
}
'''
    result = ssh(simple_agent)
    print(result)

# 3. Тестируем status
print("\n📋 Тест: status")
result = ssh(r'''
powershell.exe -ExecutionPolicy Bypass -File "C:\ProxifierAgent\ProxifierAgent.ps1" -Action status 2>&1
''')
print(result)

# 4. Тест set_proxy с новыми реквизитами
print("\n📋 Тест: set_proxy с реквизитами")
proxy_host = os.getenv("PROXY_HOST")
proxy_port = os.getenv("PROXY_PORT", "10001")
proxy_user = os.getenv("PROXY_USER")
proxy_pass = os.getenv("PROXY_PASS")
print(f"Прокси: {proxy_host}:{proxy_port}")

result = ssh(f'''
powershell.exe -ExecutionPolicy Bypass -File "C:\\ProxifierAgent\\ProxifierAgent.ps1" -Action set_proxy -ProxyHost "{proxy_host}" -ProxyPort "{proxy_port}" -ProxyUser "{proxy_user}" -ProxyPass "{proxy_pass}" 2>&1
''', timeout=120)
print(result)

print("\n" + "="*80)
