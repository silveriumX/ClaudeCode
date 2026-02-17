#!/usr/bin/env python3
"""
Configure WinRM via SSH
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("Connecting via SSH to 89.110.121.89...\n")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('89.110.121.89', username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=15)
print("✓ SSH Connected\n")

print("Configuring WinRM...\n")

# Configure WinRM
setup_cmd = r'''powershell -Command "
Write-Output '=== Step 1: Enable PSRemoting ==='
Enable-PSRemoting -Force -SkipNetworkProfileCheck | Out-Null
Write-Output 'PSRemoting enabled'

Write-Output ''
Write-Output '=== Step 2: Configure WinRM limits ==='
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB=\"2048\"}' | Out-Null
winrm set winrm/config/winrs '@{MaxShellsPerUser=\"50\"}' | Out-Null
Write-Output 'Limits configured'

Write-Output ''
Write-Output '=== Step 3: Firewall rule ==='
New-NetFirewallRule -Name 'WinRM-HTTP' -DisplayName 'WinRM HTTP' -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5985 -Action Allow -EA 0 | Out-Null
Write-Output 'Firewall rule created'

Write-Output ''
Write-Output '=== Step 4: Restart WinRM ==='
Restart-Service WinRM
Write-Output 'WinRM restarted'

Write-Output ''
Write-Output '=== Step 5: Verify ==='
$svc = Get-Service WinRM
Write-Output \"WinRM Status: $($svc.Status)\"

$listener = winrm enumerate winrm/config/listener 2>&1 | Select-String 'Address.*HTTP' -Quiet
if ($listener) { Write-Output 'HTTP Listener: OK' } else { Write-Output 'HTTP Listener: NOT FOUND' }
"'''

stdin, stdout, stderr = client.exec_command(setup_cmd, timeout=60)

print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print(f"Stderr: {err[:300]}")

print("\n✓ WinRM configured!")

client.close()
