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
Write-Output "=== Proxifier Status ==="
$proc = Get-Process Proxifier -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "Proxifier: RUNNING (PID=$($proc.Id))"
    Write-Output "MainWindowHandle: $($proc.MainWindowHandle)"
} else {
    Write-Output "Proxifier: NOT running"
}

Write-Output ""
Write-Output "=== Current External IP ==="
$ip = curl.exe -s --max-time 10 https://api.ipify.org 2>$null
Write-Output "IP: $ip"

if ($ip -eq "83.239.242.138") {
    Write-Output ""
    Write-Output "=============================================="
    Write-Output "SUCCESS! Traffic is going through proxy!"
    Write-Output "=============================================="
} elseif ($ip -eq "62.84.101.97") {
    Write-Output ""
    Write-Output "IP is server IP - Proxifier may not be routing"
}

Write-Output ""
Write-Output "=== Proxifier Profile ==="
$profilePath = "C:\Users\Administrator\AppData\Roaming\Proxifier\Profiles\Default.ppx"
if (Test-Path $profilePath) {
    Write-Output "Profile exists"
    Write-Output ""
    # Show proxy settings
    [xml]$xml = Get-Content $profilePath
    $proxies = $xml.ProxifierProfile.ProxyList.Proxy
    foreach ($p in $proxies) {
        Write-Output "Proxy: $($p.Address):$($p.Port)"
        Write-Output "  Type: $($p.Options.Type)"
        Write-Output "  Enabled: $($p.Options.Enabled)"
    }
} else {
    Write-Output "Profile not found at default location"
    # Search for profiles
    $profiles = Get-ChildItem "C:\Users\Administrator\AppData\Roaming\Proxifier" -Filter "*.ppx" -Recurse -ErrorAction SilentlyContinue
    if ($profiles) {
        Write-Output "Found profiles:"
        $profiles | ForEach-Object { Write-Output $_.FullName }
    }
}
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
