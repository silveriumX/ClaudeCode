#!/usr/bin/env python3
"""
Установка ProxiFyre на удалённый сервер через SSH
Заменяет Proxifier с полным CLI управлением
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64
import io
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

# Конфигурация
SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = "10001"
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

# URLs для скачивания
NDISAPI_URL = "https://github.com/wiresock/ndisapi/releases/download/v3.6.0/Windows.Packet.Filter.3.6.0.0-x64.msi"
PROXIFYRE_URL = "https://github.com/wiresock/proxifyre/releases/download/v2.2.1/ProxiFyre.2.2.1.zip"


def ssh(cmd, timeout=120):
    """Выполнить PowerShell команду через SSH"""
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)

        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, e = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)

        out = o.read().decode('utf-8', errors='ignore').strip()
        err = e.read().decode('utf-8', errors='ignore').strip()
        c.close()

        if err and not out:
            return f"ERROR: {err}"
        return out
    except Exception as ex:
        return f"SSH_ERROR: {ex}"


def main():
    print("="*70)
    print("🚀 УСТАНОВКА PROXIFYRE НА СЕРВЕР")
    print("="*70)
    print(f"\nСервер: {SSH_HOST}")
    print(f"Прокси: {PROXY_HOST}:{PROXY_PORT}")

    # Шаг 0: Проверка текущего состояния
    print("\n" + "="*70)
    print("📋 Шаг 0: Проверка текущего состояния")
    print("="*70)

    result = ssh(r'''
# Проверить есть ли уже ProxiFyre
$proxifyre = Get-Service ProxiFyre -ErrorAction SilentlyContinue
if ($proxifyre) {
    Write-Output "PROXIFYRE_SERVICE:$($proxifyre.Status)"
} else {
    Write-Output "PROXIFYRE_SERVICE:NotInstalled"
}

# Проверить есть ли WinpkFilter
$driver = Get-Service ndisapi -ErrorAction SilentlyContinue
if ($driver) {
    Write-Output "WINPKFILTER:$($driver.Status)"
} else {
    Write-Output "WINPKFILTER:NotInstalled"
}

# Текущий IP
$ip = curl.exe -s --max-time 5 https://api.ipify.org 2>$null
Write-Output "CURRENT_IP:$ip"
''')
    print(result)

    if "PROXIFYRE_SERVICE:Running" in result:
        print("\n✅ ProxiFyre уже установлен и запущен!")
        print("Используйте manage_proxifyre.py для управления")
        return

    # Шаг 1: Скачать и установить WinpkFilter (если не установлен)
    if "WINPKFILTER:NotInstalled" in result:
        print("\n" + "="*70)
        print("📋 Шаг 1: Установка Windows Packet Filter драйвера")
        print("="*70)
        print("⚠️  ВНИМАНИЕ: Установка драйвера может потребовать перезагрузки!")

        result = ssh(f'''
$msiUrl = "{NDISAPI_URL}"
$msiPath = "$env:TEMP\\ndisapi.msi"

Write-Output "Скачивание WinpkFilter..."
Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath -UseBasicParsing

if (Test-Path $msiPath) {{
    Write-Output "DOWNLOADED:$((Get-Item $msiPath).Length) bytes"

    Write-Output "Установка..."
    Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /qn /norestart" -Wait -NoNewWindow

    Start-Sleep 5

    $svc = Get-Service ndisapi -ErrorAction SilentlyContinue
    if ($svc) {{
        Write-Output "INSTALLED:$($svc.Status)"
    }} else {{
        Write-Output "INSTALL_STATUS:CheckManually"
    }}
}} else {{
    Write-Output "ERROR:Download failed"
}}
''', timeout=180)
        print(result)

        if "ERROR" in result:
            print("\n❌ Ошибка установки драйвера. Установите вручную:")
            print(f"   {NDISAPI_URL}")
            return
    else:
        print("\n✅ WinpkFilter уже установлен")

    # Шаг 2: Скачать ProxiFyre
    print("\n" + "="*70)
    print("📋 Шаг 2: Скачивание ProxiFyre")
    print("="*70)

    result = ssh(f'''
$zipUrl = "{PROXIFYRE_URL}"
$zipPath = "$env:TEMP\\proxifyre.zip"
$installDir = "C:\\ProxiFyre"

# Создать директорию
if (!(Test-Path $installDir)) {{
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}}

Write-Output "Скачивание ProxiFyre..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

if (Test-Path $zipPath) {{
    Write-Output "DOWNLOADED:$((Get-Item $zipPath).Length) bytes"

    Write-Output "Распаковка..."
    Expand-Archive -Path $zipPath -DestinationPath $installDir -Force

    # Проверить файлы
    $exe = Get-ChildItem $installDir -Filter "ProxiFyre.exe" -Recurse | Select-Object -First 1
    if ($exe) {{
        Write-Output "EXE_FOUND:$($exe.FullName)"
    }} else {{
        Write-Output "ERROR:ProxiFyre.exe not found"
    }}
}} else {{
    Write-Output "ERROR:Download failed"
}}
''', timeout=120)
    print(result)

    if "ERROR" in result:
        print("\n❌ Ошибка скачивания. Скачайте вручную:")
        print(f"   {PROXIFYRE_URL}")
        return

    # Шаг 3: Создать конфигурацию
    print("\n" + "="*70)
    print("📋 Шаг 3: Создание конфигурации")
    print("="*70)

    config_json = f'''{{
    "logLevel": "Info",
    "bypassLan": true,
    "proxies": [
        {{
            "appNames": [""],
            "socks5ProxyEndpoint": "{PROXY_HOST}:{PROXY_PORT}",
            "username": "{PROXY_USER}",
            "password": "{PROXY_PASS}",
            "supportedProtocols": ["TCP", "UDP"]
        }}
    ],
    "excludes": [
        "ProxiFyre.exe",
        "svchost.exe"
    ]
}}'''

    # Кодируем конфиг в base64
    config_b64 = base64.b64encode(config_json.encode('utf-8')).decode('ascii')

    result = ssh(f'''
$configB64 = "{config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$configText = [System.Text.Encoding]::UTF8.GetString($configBytes)

# Найти директорию с ProxiFyre.exe
$exeDir = (Get-ChildItem "C:\\ProxiFyre" -Filter "ProxiFyre.exe" -Recurse | Select-Object -First 1).DirectoryName
$configPath = "$exeDir\\app-config.json"

[IO.File]::WriteAllText($configPath, $configText, [System.Text.Encoding]::UTF8)

if (Test-Path $configPath) {{
    Write-Output "CONFIG_CREATED:$configPath"
    Write-Output "SIZE:$((Get-Item $configPath).Length) bytes"
}} else {{
    Write-Output "ERROR:Config not created"
}}
''')
    print(result)

    # Шаг 4: Установить и запустить сервис
    print("\n" + "="*70)
    print("📋 Шаг 4: Установка и запуск сервиса")
    print("="*70)

    result = ssh(r'''
# Найти ProxiFyre.exe
$exe = (Get-ChildItem "C:\ProxiFyre" -Filter "ProxiFyre.exe" -Recurse | Select-Object -First 1).FullName

if (!$exe) {
    Write-Output "ERROR:ProxiFyre.exe not found"
    exit 1
}

Write-Output "EXE:$exe"

# Перейти в директорию
$dir = Split-Path $exe
Set-Location $dir

# Установить сервис
Write-Output "Installing service..."
& $exe install 2>&1 | Out-String

Start-Sleep 2

# Запустить сервис
Write-Output "Starting service..."
& $exe start 2>&1 | Out-String

Start-Sleep 5

# Проверить статус
$svc = Get-Service ProxiFyre -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output "SERVICE_STATUS:$($svc.Status)"
} else {
    Write-Output "SERVICE_STATUS:NotFound"
}
''', timeout=60)
    print(result)

    # Шаг 5: Проверка
    print("\n" + "="*70)
    print("📋 Шаг 5: Финальная проверка")
    print("="*70)

    time.sleep(5)

    result = ssh(r'''
$serverIp = "62.84.101.97"

# Статус сервиса
$svc = Get-Service ProxiFyre -ErrorAction SilentlyContinue
Write-Output "SERVICE:$($svc.Status)"

# Проверить IP
$ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
Write-Output "EXTERNAL_IP:$ip"

if ($ip -and $ip -ne $serverIp) {
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "SUCCESS! ProxiFyre is working!"
    Write-Output "IP changed from $serverIp to $ip"
    Write-Output "=========================================="
} else {
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "WARNING: IP not changed yet"
    Write-Output "May need a few more seconds or reboot"
    Write-Output "=========================================="
}
''')
    print(result)

    # Шаг 6: Остановить Proxifier (опционально)
    print("\n" + "="*70)
    print("📋 Шаг 6: Остановка Proxifier (если запущен)")
    print("="*70)

    result = ssh(r'''
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Stop-Process -Name Proxifier -Force
    Write-Output "PROXIFIER:Stopped"
} else {
    Write-Output "PROXIFIER:Not running"
}
''')
    print(result)

    print("\n" + "="*70)
    print("✅ УСТАНОВКА ЗАВЕРШЕНА")
    print("="*70)
    print("""
Управление ProxiFyre через SSH:

  # Статус
  Get-Service ProxiFyre

  # Перезапуск
  Restart-Service ProxiFyre

  # Остановка
  Stop-Service ProxiFyre

  # Запуск
  Start-Service ProxiFyre

  # Изменить прокси - отредактировать app-config.json и перезапустить
""")


if __name__ == "__main__":
    main()
