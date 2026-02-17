#!/usr/bin/env python3
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.getenv("VPS_WIN_HOST"), username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=10, look_for_keys=False)

cmd = r'''
# Проверить процесс GOST
$proc = Get-Process gost* -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "GOST: Running (PID=$($proc.Id))"
} else {
    Write-Output "GOST: NOT running"
}

# Проверить порт 1080
$listen = netstat -an | Select-String ":1080.*LISTEN"
Write-Output "Port 1080: $listen"

# Тест через локальный прокси
Write-Output ""
Write-Output "Testing via 127.0.0.1:1080..."
$result = curl.exe -x "socks5://127.0.0.1:1080" -s --connect-timeout 10 --max-time 15 https://api.ipify.org 2>&1
Write-Output "Result: $result"

# Если не работает, попробуем перезапустить с другими параметрами
if (!$result -or $result -eq "") {
    Write-Output ""
    Write-Output "Restarting GOST with verbose..."

    Stop-Process -Name gost* -Force -ErrorAction SilentlyContinue
    Start-Sleep 2

    $gost = "C:\gost\gost.exe"

    # Другой формат с явным указанием протокола
    # -L локальный прокси, -F форвард через удалённый
    $args = @("-L", "socks5://:1080", "-F", "socks5://{os.getenv("PROXY_USER")}:{os.getenv("PROXY_PASS")}@{os.getenv("PROXY_HOST")}:10000")

    Start-Process -FilePath $gost -ArgumentList $args -WindowStyle Hidden
    Start-Sleep 5

    $result2 = curl.exe -x "socks5://127.0.0.1:1080" -s --max-time 10 https://api.ipify.org 2>&1
    Write-Output "Result after restart: $result2"
}
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
