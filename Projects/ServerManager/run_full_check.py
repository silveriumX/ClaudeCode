#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

"""
Run full check on all servers and show results
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS = (os.getenv("VPS_DOWNLOAD_HOST"), "root", os.getenv("VPS_DOWNLOAD_PASSWORD"))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS[0], username=VPS[1], password=VPS[2], timeout=15)
print("[OK] Connected to VPS\n")

print("Running full server check (this may take 2-3 minutes)...\n")

stdin, stdout, stderr = client.exec_command('''
cd /opt/server-monitor
python3 -c "
import sys
sys.path.insert(0, '/opt/server-monitor')
from server_checker import ServerChecker
from server_monitor import get_servers_from_sheets

checker = ServerChecker()
servers = get_servers_from_sheets()

print('Checking %d servers...' % len(servers))
print('')
print('%-18s %-6s %-12s %-12s %-18s %-15s' % ('IP', 'Shop', 'Status', 'Proxy', 'Current IP', 'City'))
print('-' * 95)

for server in servers:
    ip = server['ip']
    store = server['store']

    try:
        result = checker.check_full_status(ip, server['username'], server['password'])

        status = 'OK' if result['success'] else 'FAIL'
        proxy = str(result.get('statusProxy', 'N/A'))[:12]
        current_ip = str(result.get('currentIp', 'N/A'))[:18]
        city = str(result.get('currentCity', 'N/A'))[:15]

        marker = ''
        if not result['success'] or result.get('currentIp') in ['N/A', 'ERROR', None]:
            marker = ' [!]'

        print('%-18s %-6s %-12s %-12s %-18s %-15s%s' % (ip, store, status, proxy, current_ip, city, marker))

    except Exception as e:
        print('%-18s %-6s ERROR        -            -                  - [!] %s' % (ip, store, str(e)[:30]))

print('')
print('Done!')
"
''', timeout=600)

output = stdout.read().decode('utf-8', errors='replace')
print(output)

err = stderr.read().decode('utf-8', errors='replace')
if err and 'Traceback' in err:
    print(f"STDERR: {err[:1000]}")

client.close()
