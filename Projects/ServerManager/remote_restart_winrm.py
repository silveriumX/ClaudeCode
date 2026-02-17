#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Попытка удалённо перезапустить WinRM на проблемных серверах
"""
import paramiko

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

# Серверы с HTTP 500
PROBLEM_SERVERS = [
    ("89.124.71.240", "ALEX"),
    ("89.124.72.242", "ALEX"),
    ("91.201.113.127", "HUB"),
    ("62.84.101.97", "HUB"),
    ("5.35.32.68", "HUB"),
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

# Скрипт который попытается перезапустить WinRM через WinRM
script = '''
import sys
sys.path.insert(0, "/opt/server-monitor")
from winrm_connector import WinRMConnector

servers = %s

for ip, shop in servers:
    print(f"\\n[*] Trying {ip} ({shop})...")
    try:
        wc = WinRMConnector(ip, "Administrator", os.getenv("VPS_WIN_PASSWORD"))
        # Попытка выполнить команду перезапуска
        result = wc.execute_command("Restart-Service WinRM -Force; Write-Host OK")
        print(f"    Result: {result}")
    except Exception as e:
        print(f"    Error: {str(e)[:100]}")
'''

script = script % str(PROBLEM_SERVERS)

stdin, stdout, stderr = client.exec_command(f'cat > /tmp/restart_winrm.py << \'ENDSCRIPT\'\n{script}\nENDSCRIPT')
stdout.read()

print("Attempting to restart WinRM remotely on problem servers...")
print("=" * 60)

stdin, stdout, stderr = client.exec_command('python3 /tmp/restart_winrm.py', timeout=300)
print(stdout.read().decode())
print(stderr.read().decode())

# Также проверим логи для MN сервера
print("\n" + "=" * 60)
print("Checking MN server (194.59.31.156) monitoring logs...")
print("=" * 60)

stdin, stdout, stderr = client.exec_command(
    "journalctl -u server-monitor --since '10 min ago' 2>/dev/null | grep -i '194.59.31.156' | tail -10"
)
print(stdout.read().decode() or "No recent logs for MN")

client.close()
