#!/usr/bin/env python3
"""
Установка WinpkFilter альтернативным методом
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import base64
import io
import sys
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import paramiko

SSH_HOST = os.getenv("VPS_WIN_HOST")
SSH_USER = "Administrator"
SSH_PASS = os.getenv("VPS_WIN_PASSWORD")


def ssh(cmd, timeout=300):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)
        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
        return o.read().decode('utf-8', errors='ignore').strip()
    except Exception as ex:
        return f"SSH_ERROR: {ex}"


print("="*70)
print("  УСТАНОВКА WINPKFILTER")
print("="*70)

# Попробуем разные URL
urls = [
    "https://github.com/wiresock/ndisapi/releases/download/v3.6.0/Windows.Packet.Filter.3.6.0.0-x64.msi",
    "https://github.com/wiresock/ndisapi/releases/latest/download/Windows.Packet.Filter.3.6.0.0-x64.msi",
]

result = ssh(r'''
# Проверить уже установлен
$svc = Get-Service ndisapi -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output "ALREADY_INSTALLED:$($svc.Status)"
    exit 0
}

# Попробовать скачать
$urls = @(
    "https://github.com/wiresock/ndisapi/releases/download/v3.6.0/Windows.Packet.Filter.3.6.0.0-x64.msi"
)

$msiPath = "$env:TEMP\ndisapi.msi"

foreach ($url in $urls) {
    Write-Output "Trying: $url"
    try {
        # Использовать WebClient вместо Invoke-WebRequest
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $msiPath)

        if (Test-Path $msiPath) {
            $size = (Get-Item $msiPath).Length
            if ($size -gt 100000) {
                Write-Output "DOWNLOADED:$size bytes"
                break
            }
        }
    } catch {
        Write-Output "ERROR:$($_.Exception.Message)"
    }
}

# Проверить скачался ли
if (!(Test-Path $msiPath)) {
    Write-Output "DOWNLOAD_FAILED:All URLs failed"

    # Альтернатива - скачать через curl
    Write-Output "Trying curl..."
    $curlUrl = "https://github.com/wiresock/ndisapi/releases/download/v3.6.0/Windows.Packet.Filter.3.6.0.0-x64.msi"
    curl.exe -L -o $msiPath $curlUrl 2>&1

    if (Test-Path $msiPath) {
        $size = (Get-Item $msiPath).Length
        Write-Output "CURL_DOWNLOADED:$size bytes"
    }
}

if (Test-Path $msiPath) {
    $size = (Get-Item $msiPath).Length
    if ($size -gt 100000) {
        Write-Output "Installing MSI..."
        Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /qn /norestart" -Wait -NoNewWindow

        Start-Sleep 5

        $svc = Get-Service ndisapi -ErrorAction SilentlyContinue
        if ($svc) {
            Write-Output "INSTALL_SUCCESS:$($svc.Status)"
            if ($svc.Status -ne "Running") {
                Start-Service ndisapi
                $svc = Get-Service ndisapi
            }
            Write-Output "SERVICE:$($svc.Status)"
        } else {
            Write-Output "INSTALL_CHECK:Service not found, may need reboot"
        }
    } else {
        Write-Output "DOWNLOAD_INCOMPLETE:$size bytes"
    }
} else {
    Write-Output "FINAL_STATUS:Download failed"
}
''')
print(result)

# Если не удалось, попробуем альтернативу без WinpkFilter
if "DOWNLOAD_FAILED" in result or "failed" in result.lower():
    print("\n" + "="*70)
    print("  АЛЬТЕРНАТИВНЫЙ МЕТОД: tun2socks")
    print("="*70)
    print("""
WinpkFilter не удалось установить.

Альтернатива: использовать tun2socks для маршрутизации
через SOCKS5 прокси. Это более простое решение.
""")

    # Установим tun2socks
    result = ssh(r'''
$tun2socksDir = "C:\tun2socks"
if (!(Test-Path $tun2socksDir)) {
    New-Item -ItemType Directory -Path $tun2socksDir -Force | Out-Null
}

$exePath = "$tun2socksDir\tun2socks.exe"

if (Test-Path $exePath) {
    Write-Output "TUN2SOCKS:Already installed"
} else {
    Write-Output "Downloading tun2socks..."

    $url = "https://github.com/xjasonlyu/tun2socks/releases/download/v2.5.2/tun2socks-windows-amd64.zip"
    $zipPath = "$env:TEMP\tun2socks.zip"

    try {
        curl.exe -L -o $zipPath $url 2>&1

        if (Test-Path $zipPath) {
            $size = (Get-Item $zipPath).Length
            Write-Output "DOWNLOADED:$size bytes"

            Expand-Archive -Path $zipPath -DestinationPath $tun2socksDir -Force

            # Найти exe
            $exe = Get-ChildItem $tun2socksDir -Filter "*.exe" -Recurse | Select-Object -First 1
            if ($exe) {
                # Переименовать если нужно
                if ($exe.Name -ne "tun2socks.exe") {
                    Move-Item $exe.FullName "$tun2socksDir\tun2socks.exe" -Force
                }
                Write-Output "TUN2SOCKS_INSTALLED:$tun2socksDir\tun2socks.exe"
            }
        }
    } catch {
        Write-Output "ERROR:$($_.Exception.Message)"
    }
}
''')
    print(result)
