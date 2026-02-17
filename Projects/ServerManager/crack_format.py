#!/usr/bin/env python3
"""Use scheduled task to run DPAPI in interactive session"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(os.getenv("VPS_DOWNLOAD_HOST"), port=22, username='root', password=os.getenv("VPS_DOWNLOAD_PASSWORD"), timeout=30)

# Create a script file and run it via scheduled task in user's session
test_script = r'''
import sys
sys.path.insert(0, '/opt/server-monitor')
from winrm_connector import WinRMConnector
connector = WinRMConnector(timeout=180)

# Step 1: Create PowerShell script on remote machine
# Step 2: Run it via scheduled task in interactive session
# Step 3: Read result

cmd = r"""
$password = "wH5N44Ju8L4AzTcK9lofWkjuvPksSHWH"
$username = "nwpcRT59wwpdd2HkFM4A"
$address = os.getenv("PROXY_HOST")
$port = "10000"

# Create script that will run in interactive session
$script = @'
Add-Type -AssemblyName System.Security
$password = "wH5N44Ju8L4AzTcK9lofWkjuvPksSHWH"
$passBytes = [Text.Encoding]::UTF8.GetBytes($password)
$encrypted = [Security.Cryptography.ProtectedData]::Protect($passBytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
$header = [byte[]](0, 0, 2, 115)
$result = [Convert]::ToBase64String($header + $encrypted)
$result | Out-File "C:\Temp\encrypted_pass.txt" -Encoding UTF8
'@

# Save script
$script | Out-File "C:\Temp\encrypt_pass.ps1" -Encoding UTF8
Write-Output "Script saved to C:\Temp\encrypt_pass.ps1"

# Create and run scheduled task in interactive session
$taskName = "EncryptProxyPass"
schtasks /Delete /TN $taskName /F 2>$null

# Create task that runs in current user's interactive session
schtasks /Create /TN $taskName /TR "powershell -ExecutionPolicy Bypass -File C:\Temp\encrypt_pass.ps1" /SC ONCE /ST 00:00 /RU Administrator /RP $env:VPS_WIN_PASSWORD /IT /F

Write-Output "Task created, running..."
schtasks /Run /TN $taskName

# Wait for completion
Start-Sleep 5

# Check if result file exists
if (Test-Path "C:\Temp\encrypted_pass.txt") {
    $encPass = (gc "C:\Temp\encrypted_pass.txt" -Raw).Trim()
    Write-Output "Encrypted password: $encPass"
    Write-Output "Length: $($encPass.Length)"

    # Now create the profile
    $pp = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
    $xml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxifierProfile version="102" platform="Windows" product_id="0" product_minver="400">
<Options><Resolve><AutoModeDetection enabled="true" /><ViaProxy enabled="false" /><BlockNonATypes enabled="false" /><ExclusionList OnlyFromListMode="false">%ComputerName%; localhost; *.local</ExclusionList><DnsUdpMode>0</DnsUdpMode></Resolve><Encryption mode="basic" /><ConnectionLoopDetection enabled="true" resolve="true" /><Udp mode="mode_bypass" /><LeakPreventionMode enabled="false" /><ProcessOtherUsers enabled="false" /><ProcessServices enabled="false" /><HandleDirectConnections enabled="false" /><HttpProxiesSupport enabled="false" /></Options>
<ProxyList><Proxy id="100" type="SOCKS5"><Address>{os.getenv("PROXY_HOST")}</Address><Port>10000</Port><Options>0</Options><Authentication enabled="true"><Username>nwpcRT59wwpdd2HkFM4A</Username><Password>$encPass</Password></Authentication></Proxy></ProxyList>
<ChainList />
<RuleList><Rule enabled="true"><Action type="Direct" /><Targets>localhost; 127.0.0.1; %ComputerName%; ::1</Targets><Name>Localhost</Name></Rule><Rule enabled="true"><Action type="Proxy" id="100" /><Name>Default</Name></Rule></RuleList>
</ProxifierProfile>
"@
    $enc = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($pp, $xml, $enc)
    Write-Output "Profile saved with encrypted password"

    # Cleanup
    Remove-Item "C:\Temp\encrypted_pass.txt" -Force -EA 0
    Remove-Item "C:\Temp\encrypt_pass.ps1" -Force -EA 0

    # Start Proxifier
    Stop-Process -Name Proxifier -Force -EA 0
    Start-Sleep 2
    Start-Process "C:\Program Files (x86)\Proxifier\Proxifier.exe"
    Start-Sleep 5

    if (Get-Process Proxifier -EA 0) {
        Write-Output "SUCCESS: Proxifier is running!"
    } else {
        Write-Output "FAILED: Proxifier not running"
    }
} else {
    Write-Output "FAILED: No encrypted password file created"
    Write-Output "Task might not have run in interactive session"
}

schtasks /Delete /TN $taskName /F 2>$null
"""

result = connector.execute_command('109.107.190.66', 'Administrator', os.getenv("VPS_WIN_PASSWORD"), cmd)
print(result if result else 'No output')
'''

sftp = client.open_sftp()
with sftp.open('/tmp/schtask.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = client.exec_command('python3 /tmp/schtask.py', timeout=240)
stdout.channel.recv_exit_status()
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
