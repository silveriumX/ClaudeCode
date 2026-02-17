#!/usr/bin/env python3
"""
Управление ProxiFyre через SSH
Простые команды: status, start, stop, restart, set_proxy
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import argparse
import base64
import io
import json
import sys

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

# Конфигурация по умолчанию
DEFAULT_HOST = os.getenv("VPS_WIN_HOST")
DEFAULT_USER = "Administrator"
DEFAULT_PASS = os.getenv("VPS_WIN_PASSWORD")


def ssh(host, user, password, cmd, timeout=60):
    """Выполнить PowerShell команду через SSH"""
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(host, username=user, password=password, timeout=15, look_for_keys=False)

        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)

        result = o.read().decode('utf-8', errors='ignore').strip()
        c.close()
        return result
    except Exception as ex:
        return f"ERROR: {ex}"


def cmd_status(host, user, password):
    """Показать статус ProxiFyre"""
    result = ssh(host, user, password, r'''
$svc = Get-Service ProxiFyre -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output "SERVICE:$($svc.Status)"
} else {
    Write-Output "SERVICE:NotInstalled"
}

$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "EXTERNAL_IP:$ip"

# Конфиг
$config = Get-ChildItem "C:\ProxiFyre" -Filter "app-config.json" -Recurse | Select-Object -First 1
if ($config) {
    $json = Get-Content $config.FullName | ConvertFrom-Json
    $proxy = $json.proxies[0].socks5ProxyEndpoint
    Write-Output "PROXY:$proxy"
}
''')
    print(result)


def cmd_start(host, user, password):
    """Запустить ProxiFyre"""
    result = ssh(host, user, password, r'''
Start-Service ProxiFyre -ErrorAction SilentlyContinue
Start-Sleep 2
$svc = Get-Service ProxiFyre
Write-Output "STATUS:$($svc.Status)"
''')
    print(result)


def cmd_stop(host, user, password):
    """Остановить ProxiFyre"""
    result = ssh(host, user, password, r'''
Stop-Service ProxiFyre -ErrorAction SilentlyContinue
$svc = Get-Service ProxiFyre
Write-Output "STATUS:$($svc.Status)"
''')
    print(result)


def cmd_restart(host, user, password):
    """Перезапустить ProxiFyre"""
    result = ssh(host, user, password, r'''
Restart-Service ProxiFyre -ErrorAction SilentlyContinue
Start-Sleep 3
$svc = Get-Service ProxiFyre
Write-Output "STATUS:$($svc.Status)"

$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "IP:$ip"
''')
    print(result)


def cmd_set_proxy(host, user, password, proxy_host, proxy_port, proxy_user, proxy_pass):
    """Установить новый прокси"""
    config = {
        "logLevel": "Info",
        "bypassLan": True,
        "proxies": [
            {
                "appNames": [""],
                "socks5ProxyEndpoint": f"{proxy_host}:{proxy_port}",
                "username": proxy_user,
                "password": proxy_pass,
                "supportedProtocols": ["TCP", "UDP"]
            }
        ],
        "excludes": ["ProxiFyre.exe", "svchost.exe"]
    }

    config_json = json.dumps(config, indent=4)
    config_b64 = base64.b64encode(config_json.encode('utf-8')).decode('ascii')

    result = ssh(host, user, password, f'''
$configB64 = "{config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$configText = [System.Text.Encoding]::UTF8.GetString($configBytes)

# Найти app-config.json
$configFile = Get-ChildItem "C:\\ProxiFyre" -Filter "app-config.json" -Recurse | Select-Object -First 1
if ($configFile) {{
    [IO.File]::WriteAllText($configFile.FullName, $configText, [System.Text.Encoding]::UTF8)
    Write-Output "CONFIG:Updated"

    # Перезапустить сервис
    Restart-Service ProxiFyre -ErrorAction SilentlyContinue
    Start-Sleep 5

    $svc = Get-Service ProxiFyre
    Write-Output "SERVICE:$($svc.Status)"

    $ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
    Write-Output "IP:$ip"
}} else {{
    Write-Output "ERROR:Config not found"
}}
''')
    print(result)


def cmd_check_ip(host, user, password):
    """Проверить текущий IP"""
    result = ssh(host, user, password, r'''
$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output $ip
''')
    print(f"External IP: {result}")


def main():
    parser = argparse.ArgumentParser(description='Управление ProxiFyre через SSH')
    parser.add_argument('action', choices=['status', 'start', 'stop', 'restart', 'set_proxy', 'ip'],
                        help='Действие')
    parser.add_argument('--host', default=DEFAULT_HOST, help='SSH хост')
    parser.add_argument('--user', default=DEFAULT_USER, help='SSH пользователь')
    parser.add_argument('--password', default=DEFAULT_PASS, help='SSH пароль')

    # Для set_proxy
    parser.add_argument('--proxy-host', help='Хост прокси')
    parser.add_argument('--proxy-port', help='Порт прокси')
    parser.add_argument('--proxy-user', help='Логин прокси')
    parser.add_argument('--proxy-pass', help='Пароль прокси')

    args = parser.parse_args()

    if args.action == 'status':
        cmd_status(args.host, args.user, args.password)
    elif args.action == 'start':
        cmd_start(args.host, args.user, args.password)
    elif args.action == 'stop':
        cmd_stop(args.host, args.user, args.password)
    elif args.action == 'restart':
        cmd_restart(args.host, args.user, args.password)
    elif args.action == 'ip':
        cmd_check_ip(args.host, args.user, args.password)
    elif args.action == 'set_proxy':
        if not all([args.proxy_host, args.proxy_port, args.proxy_user, args.proxy_pass]):
            print("Для set_proxy требуются: --proxy-host, --proxy-port, --proxy-user, --proxy-pass")
            sys.exit(1)
        cmd_set_proxy(args.host, args.user, args.password,
                      args.proxy_host, args.proxy_port, args.proxy_user, args.proxy_pass)


if __name__ == "__main__":
    main()
