#!/usr/bin/env python3
import base64, io, json, os, sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

VPS_WIN_HOST = os.getenv("VPS_WIN_HOST")
VPS_WIN_PASSWORD = os.getenv("VPS_WIN_PASSWORD")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(VPS_WIN_HOST, username='Administrator', password=VPS_WIN_PASSWORD, timeout=10, look_for_keys=False)

# Более простой конфиг без TUN (TUN требует драйвер)
config = {
    "log": {"level": "debug", "timestamp": True},
    "inbounds": [],
    "outbounds": [
        {
            "type": "socks",
            "tag": "proxy",
            "server": PROXY_HOST,
            "server_port": int(PROXY_PORT),
            "username": PROXY_USER,
            "password": PROXY_PASS
        },
        {"type": "direct", "tag": "direct"}
    ],
    "route": {"final": "proxy"}
}

config_json = json.dumps(config, indent=2)
config_b64 = base64.b64encode(config_json.encode('utf-8')).decode()

cmd = f'''
$configPath = "C:\\sing-box\\config_simple.json"
$configB64 = "{config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$configText = [System.Text.Encoding]::UTF8.GetString($configBytes)
[IO.File]::WriteAllText($configPath, $configText, [System.Text.Encoding]::UTF8)

Write-Output "Config saved"

$exe = "C:\\sing-box\\sing-box.exe"

Write-Output ""
Write-Output "=== Checking config ==="
& $exe check -c $configPath 2>&1

Write-Output ""
Write-Output "=== Running with output ==="

# Запуск в фоне и сохранение вывода
$job = Start-Job -ScriptBlock {{
    param($e, $c)
    & $e run -c $c 2>&1
}} -ArgumentList $exe, $configPath

Start-Sleep 5
$output = Receive-Job $job 2>&1
Write-Output $output

Stop-Job $job -ErrorAction SilentlyContinue
Remove-Job $job -ErrorAction SilentlyContinue

Write-Output ""
Write-Output "=== Process check ==="
$proc = Get-Process sing-box -ErrorAction SilentlyContinue
if ($proc) {{
    Write-Output "sing-box RUNNING: PID=$($proc.Id)"
}} else {{
    Write-Output "sing-box NOT running"
}}
'''

enc = base64.b64encode(cmd.encode('utf-16le')).decode()
_, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=60)
print(o.read().decode('utf-8', errors='ignore'))
c.close()
