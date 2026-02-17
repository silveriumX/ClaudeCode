#!/usr/bin/env python3
"""
Прямой тест прокси через curl с SOCKS5
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64
import io
import sys
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


def execute_ssh(ps_command):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False, allow_agent=False)

        encoded = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=90)

        output = stdout.read().decode("utf-8", errors="ignore").strip()
        return output
    except Exception as e:
        return f"ERROR:{e}"
    finally:
        if client:
            client.close()


print("="*80)
print("🔍 ПРЯМОЙ ТЕСТ ПРОКСИ ЧЕРЕЗ CURL")
print("="*80)

# Тест через curl с SOCKS5
test_cmd = f'''
Write-Output "Тест прокси напрямую через curl (SOCKS5)..."
Write-Output "Прокси: {PROXY_HOST}:{PROXY_PORT}"
Write-Output "Логин: {PROXY_USER}"
Write-Output ""

# 1. Без прокси (должен показать IP сервера)
Write-Output "=== БЕЗ ПРОКСИ ==="
try {{
    $directIp = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
    if ($directIp) {{
        Write-Output "DIRECT_IP:$directIp"
    }} else {{
        Write-Output "DIRECT_IP:Ошибка"
    }}
}} catch {{
    Write-Output "DIRECT_IP:Ошибка"
}}

Write-Output ""
Write-Output "=== С ПРОКСИ (SOCKS5) ==="

# 2. С прокси SOCKS5
$proxyUrl = "socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

try {{
    Write-Output "Подключение к прокси..."
    $output = curl.exe -x $proxyUrl -s --max-time 30 https://api.ipify.org 2>&1

    if ($output -match '^\d+\.\d+\.\d+\.\d+$') {{
        Write-Output "PROXY_IP:$output ✅"
        if ($output -ne "$directIp") {{
            Write-Output "SUCCESS:IP изменился! Прокси работает!"
        }} else {{
            Write-Output "WARNING:IP не изменился"
        }}
    }} else {{
        Write-Output "PROXY_ERROR:$output"
    }}
}} catch {{
    Write-Output "PROXY_ERROR:$($_.Exception.Message)"
}}

Write-Output ""
Write-Output "=== ПРОВЕРКА СОЕДИНЕНИЙ К ПРОКСИ ==="
$conn = Get-NetTCPConnection -RemoteAddress {PROXY_HOST} -ErrorAction SilentlyContinue
if ($conn) {{
    Write-Output "ACTIVE_CONNECTIONS:$($conn.Count)"
    $conn | ForEach-Object {{
        Write-Output "  Port=$($_.RemotePort), State=$($_.State)"
    }}
}} else {{
    Write-Output "ACTIVE_CONNECTIONS:Нет"
}}
'''

print("Выполнение теста (может занять до 30 секунд)...")
result = execute_ssh(test_cmd)
print(result)

print("\n" + "="*80)
print("📊 РЕЗУЛЬТАТЫ")
print("="*80)
print("\nЕсли PROXY_IP показал другой IP:")
print("  ✅ Прокси работает напрямую через curl")
print("  ❌ Но Proxifier его не использует (проблема в настройках Proxifier)")
print("\nЕсли PROXY_ERROR:")
print("  ❌ Прокси не работает (неправильные реквизиты или недоступен)")
