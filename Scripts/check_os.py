#!/usr/bin/env python3
import base64, io, os, sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

VPS_WIN_HOST = os.getenv("VPS_WIN_HOST")
VPS_WIN_PASSWORD = os.getenv("VPS_WIN_PASSWORD")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(VPS_WIN_HOST, username='Administrator', password=VPS_WIN_PASSWORD, timeout=10, look_for_keys=False)

cmd = r'''
$os = (Get-WmiObject Win32_OperatingSystem).Caption
Write-Output "OS: $os"

$docker = Get-Command docker -ErrorAction SilentlyContinue
Write-Output "Docker: $(if($docker){'Installed - ' + (docker --version 2>$null)}else{'Not installed'})"

$wsl = Get-Command wsl -ErrorAction SilentlyContinue
Write-Output "WSL: $(if($wsl){'Installed'}else{'Not installed'})"

$wg = Get-Command wg -ErrorAction SilentlyContinue
Write-Output "WireGuard CLI: $(if($wg){'Installed'}else{'Not installed'})"

# Check if Hyper-V is enabled
$hv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -ErrorAction SilentlyContinue
Write-Output "Hyper-V: $(if($hv.State -eq 'Enabled'){'Enabled'}else{'Disabled/Not available'})"
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
