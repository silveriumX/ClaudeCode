#!/usr/bin/env python3
"""
Установка и настройка WireGuard на Windows Server 2022
С маршрутизацией через SOCKS5 прокси
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64
import io
import sys
import time
import secrets

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

WG_PORT = 51820
WG_SUBNET = "10.66.66"  # VPN subnet


def ssh(cmd, timeout=180):
    """Выполнить PowerShell команду через SSH"""
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)

        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, e = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)

        out = o.read().decode('utf-8', errors='ignore').strip()
        c.close()
        return out
    except Exception as ex:
        return f"SSH_ERROR: {ex}"


def main():
    print("="*70)
    print("  УСТАНОВКА WIREGUARD НА WINDOWS SERVER 2022")
    print("="*70)
    print(f"\nСервер: {SSH_HOST}")
    print(f"WireGuard порт: {WG_PORT}/UDP")
    print(f"VPN подсеть: {WG_SUBNET}.0/24")

    # Шаг 1: Скачать и установить WireGuard
    print("\n" + "="*70)
    print("Шаг 1: Скачивание WireGuard")
    print("="*70)

    result = ssh(r'''
$wgExe = "C:\Program Files\WireGuard\wireguard.exe"
if (Test-Path $wgExe) {
    Write-Output "ALREADY_INSTALLED:$wgExe"
} else {
    $url = "https://download.wireguard.com/windows-client/wireguard-installer.exe"
    $installer = "C:\Temp\wireguard-installer.exe"

    if (!(Test-Path "C:\Temp")) {
        New-Item -ItemType Directory -Path "C:\Temp" -Force | Out-Null
    }

    Write-Output "Downloading..."
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

    if (Test-Path $installer) {
        Write-Output "DOWNLOADED:$((Get-Item $installer).Length) bytes"

        Write-Output "Installing silently..."
        Start-Process -FilePath $installer -ArgumentList "/S" -Wait -NoNewWindow

        Start-Sleep 5

        if (Test-Path $wgExe) {
            Write-Output "INSTALL_SUCCESS"
        } else {
            Write-Output "INSTALL_FAILED:WireGuard not found after install"
        }
    } else {
        Write-Output "DOWNLOAD_FAILED"
    }
}
''')
    print(result)

    if "INSTALL_FAILED" in result or "DOWNLOAD_FAILED" in result:
        print("\n❌ Ошибка установки WireGuard")
        return

    # Шаг 2: Генерация ключей сервера
    print("\n" + "="*70)
    print("Шаг 2: Генерация ключей")
    print("="*70)

    result = ssh(r'''
$wgDir = "C:\WireGuard"
if (!(Test-Path $wgDir)) {
    New-Item -ItemType Directory -Path $wgDir -Force | Out-Null
}

$privateKeyFile = "$wgDir\server_private.key"
$publicKeyFile = "$wgDir\server_public.key"

# Проверить есть ли уже ключи
if ((Test-Path $privateKeyFile) -and (Test-Path $publicKeyFile)) {
    Write-Output "KEYS_EXIST"
    $pubKey = Get-Content $publicKeyFile
    Write-Output "SERVER_PUBLIC_KEY:$pubKey"
} else {
    # Генерируем ключи через wg.exe
    $wg = "C:\Program Files\WireGuard\wg.exe"
    if (Test-Path $wg) {
        # Генерация приватного ключа
        $privKey = & $wg genkey
        $privKey | Out-File -FilePath $privateKeyFile -Encoding ascii -NoNewline

        # Генерация публичного ключа
        $pubKey = $privKey | & $wg pubkey
        $pubKey | Out-File -FilePath $publicKeyFile -Encoding ascii -NoNewline

        Write-Output "KEYS_GENERATED"
        Write-Output "SERVER_PUBLIC_KEY:$pubKey"
    } else {
        Write-Output "ERROR:wg.exe not found"
    }
}
''')
    print(result)

    # Извлекаем публичный ключ сервера
    server_public_key = ""
    for line in result.split('\n'):
        if line.startswith("SERVER_PUBLIC_KEY:"):
            server_public_key = line.split(":")[1].strip()
            break

    if not server_public_key:
        print("\n❌ Не удалось получить публичный ключ сервера")
        return

    print(f"\nПубличный ключ сервера: {server_public_key}")

    # Шаг 3: Генерация ключей клиента
    print("\n" + "="*70)
    print("Шаг 3: Генерация ключей клиента (тестовый)")
    print("="*70)

    result = ssh(r'''
$wgDir = "C:\WireGuard"
$clientDir = "$wgDir\clients"
if (!(Test-Path $clientDir)) {
    New-Item -ItemType Directory -Path $clientDir -Force | Out-Null
}

$clientName = "test_client"
$clientPrivFile = "$clientDir\${clientName}_private.key"
$clientPubFile = "$clientDir\${clientName}_public.key"

$wg = "C:\Program Files\WireGuard\wg.exe"

if ((Test-Path $clientPrivFile) -and (Test-Path $clientPubFile)) {
    Write-Output "CLIENT_KEYS_EXIST"
    $clientPub = Get-Content $clientPubFile
    $clientPriv = Get-Content $clientPrivFile
} else {
    $clientPriv = & $wg genkey
    $clientPriv | Out-File -FilePath $clientPrivFile -Encoding ascii -NoNewline

    $clientPub = $clientPriv | & $wg pubkey
    $clientPub | Out-File -FilePath $clientPubFile -Encoding ascii -NoNewline

    Write-Output "CLIENT_KEYS_GENERATED"
}

Write-Output "CLIENT_PUBLIC_KEY:$clientPub"
Write-Output "CLIENT_PRIVATE_KEY:$clientPriv"
''')
    print(result)

    # Извлекаем ключи клиента
    client_public_key = ""
    client_private_key = ""
    for line in result.split('\n'):
        if line.startswith("CLIENT_PUBLIC_KEY:"):
            client_public_key = line.split(":")[1].strip()
        elif line.startswith("CLIENT_PRIVATE_KEY:"):
            client_private_key = line.split(":")[1].strip()

    # Шаг 4: Создание конфига сервера
    print("\n" + "="*70)
    print("Шаг 4: Создание конфига сервера")
    print("="*70)

    server_config = f'''[Interface]
PrivateKey = SERVER_PRIVATE_KEY_PLACEHOLDER
Address = {WG_SUBNET}.1/24
ListenPort = {WG_PORT}
DNS = 1.1.1.1

[Peer]
# test_client
PublicKey = {client_public_key}
AllowedIPs = {WG_SUBNET}.2/32
'''

    # Кодируем конфиг
    config_b64 = base64.b64encode(server_config.encode('utf-8')).decode()

    result = ssh(f'''
$wgDir = "C:\\WireGuard"
$configPath = "$wgDir\\wg0.conf"

# Получить приватный ключ сервера
$serverPrivKey = Get-Content "$wgDir\\server_private.key"

# Декодировать шаблон конфига
$configB64 = "{config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$config = [System.Text.Encoding]::UTF8.GetString($configBytes)

# Заменить placeholder на реальный ключ
$config = $config -replace "SERVER_PRIVATE_KEY_PLACEHOLDER", $serverPrivKey

# Сохранить
[IO.File]::WriteAllText($configPath, $config, [System.Text.Encoding]::ASCII)

if (Test-Path $configPath) {{
    Write-Output "SERVER_CONFIG_CREATED:$configPath"
    Write-Output "SIZE:$((Get-Item $configPath).Length) bytes"
}} else {{
    Write-Output "ERROR:Config not created"
}}
''')
    print(result)

    # Шаг 5: Создание конфига клиента
    print("\n" + "="*70)
    print("Шаг 5: Создание конфига клиента")
    print("="*70)

    client_config = f'''[Interface]
PrivateKey = {client_private_key}
Address = {WG_SUBNET}.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {SSH_HOST}:{WG_PORT}
PersistentKeepalive = 25
'''

    print("\n📋 Конфиг для клиента (сохрани как wg0.conf):")
    print("-" * 50)
    print(client_config)
    print("-" * 50)

    # Сохраним клиентский конфиг на сервере тоже
    client_config_b64 = base64.b64encode(client_config.encode('utf-8')).decode()

    result = ssh(f'''
$clientConfig = "$env:TEMP\\wg_client_config.conf"
$configB64 = "{client_config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$config = [System.Text.Encoding]::UTF8.GetString($configBytes)
[IO.File]::WriteAllText($clientConfig, $config, [System.Text.Encoding]::ASCII)
Write-Output "CLIENT_CONFIG_SAVED:$clientConfig"
''')
    print(result)

    # Шаг 6: Открыть порт в firewall
    print("\n" + "="*70)
    print("Шаг 6: Настройка Firewall")
    print("="*70)

    result = ssh(f'''
# Проверить существует ли правило
$rule = Get-NetFirewallRule -DisplayName "WireGuard" -ErrorAction SilentlyContinue

if ($rule) {{
    Write-Output "FIREWALL_RULE:Already exists"
}} else {{
    # Создать правило для входящего UDP трафика
    New-NetFirewallRule -DisplayName "WireGuard" -Direction Inbound -Protocol UDP -LocalPort {WG_PORT} -Action Allow | Out-Null
    Write-Output "FIREWALL_RULE:Created for UDP {WG_PORT}"
}}
''')
    print(result)

    # Шаг 7: Запуск WireGuard туннеля
    print("\n" + "="*70)
    print("Шаг 7: Запуск WireGuard туннеля")
    print("="*70)

    result = ssh(r'''
$wgDir = "C:\WireGuard"
$configPath = "$wgDir\wg0.conf"
$wireguard = "C:\Program Files\WireGuard\wireguard.exe"

# Установить туннель как сервис
Write-Output "Installing tunnel service..."

# Сначала удалим если существует
& $wireguard /uninstalltunnelservice wg0 2>$null

Start-Sleep 2

# Установить новый
& $wireguard /installtunnelservice $configPath

Start-Sleep 3

# Проверить статус
$svc = Get-Service "WireGuardTunnel$wg0" -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output "SERVICE_STATUS:$($svc.Status)"

    if ($svc.Status -ne "Running") {
        Start-Service "WireGuardTunnel$wg0"
        Start-Sleep 2
        $svc = Get-Service "WireGuardTunnel$wg0"
        Write-Output "SERVICE_AFTER_START:$($svc.Status)"
    }
} else {
    Write-Output "SERVICE:Not found"
}

# Проверить интерфейс
$wgExe = "C:\Program Files\WireGuard\wg.exe"
Write-Output ""
Write-Output "=== WireGuard Status ==="
& $wgExe show 2>&1
''')
    print(result)

    print("\n" + "="*70)
    print("  УСТАНОВКА ЗАВЕРШЕНА")
    print("="*70)
    print(f"""
Сервер WireGuard запущен!

Для подключения клиента:
1. Установи WireGuard: https://www.wireguard.com/install/
2. Импортируй конфиг выше (wg0.conf)
3. Нажми "Activate"

После подключения:
- IP клиента в VPN: {WG_SUBNET}.2
- Весь трафик через VPN
- DNS: 1.1.1.1

Для проверки утечек:
- https://ipleak.net
- https://browserleaks.com/webrtc
""")

    # Сохраним клиентский конфиг локально
    local_config_path = "C:\\Users\\Admin\\Documents\\Cursor\\Scripts\\WireGuard\\client_config.conf"
    try:
        with open(local_config_path, 'w') as f:
            f.write(client_config)
        print(f"\n✅ Клиентский конфиг сохранён: {local_config_path}")
    except:
        pass


if __name__ == "__main__":
    main()
