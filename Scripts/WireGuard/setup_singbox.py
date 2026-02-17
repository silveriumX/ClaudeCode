#!/usr/bin/env python3
"""
Установка sing-box для маршрутизации VPN трафика через SOCKS5 прокси
"""
import base64, io, json, os, sys, time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = int(os.getenv("PROXY_PORT", "10000"))
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

def ssh(cmd, timeout=180):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15, look_for_keys=False)
    enc = base64.b64encode(cmd.encode('utf-16le')).decode()
    _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
    return o.read().decode('utf-8', errors='ignore').strip()


print("="*70)
print("  УСТАНОВКА SING-BOX")
print("="*70)

# Шаг 1: Скачать sing-box
print("\n1. Скачивание sing-box...")

result = ssh(r'''
$singboxDir = "C:\sing-box"
$exePath = "$singboxDir\sing-box.exe"

if (Test-Path $exePath) {
    Write-Output "SINGBOX:Already installed"
    & $exePath version 2>&1
} else {
    Write-Output "Downloading sing-box..."

    if (!(Test-Path $singboxDir)) {
        New-Item -ItemType Directory -Path $singboxDir -Force | Out-Null
    }

    $url = "https://github.com/SagerNet/sing-box/releases/download/v1.10.7/sing-box-1.10.7-windows-amd64.zip"
    $zipPath = "$env:TEMP\sing-box.zip"

    curl.exe -L -o $zipPath $url 2>&1

    if (Test-Path $zipPath) {
        $size = (Get-Item $zipPath).Length
        Write-Output "DOWNLOADED:$size bytes"

        Expand-Archive -Path $zipPath -DestinationPath $singboxDir -Force

        # Найти exe и переместить в корень
        $exe = Get-ChildItem $singboxDir -Filter "sing-box.exe" -Recurse | Select-Object -First 1
        if ($exe -and $exe.DirectoryName -ne $singboxDir) {
            Move-Item "$($exe.DirectoryName)\*" $singboxDir -Force
        }

        if (Test-Path $exePath) {
            Write-Output "INSTALL_SUCCESS"
            & $exePath version 2>&1
        } else {
            Write-Output "INSTALL_FAILED"
        }
    }
}
''')
print(result)

# Шаг 2: Создать конфиг sing-box
print("\n2. Создание конфига...")

# sing-box конфиг: TUN mode чтобы перехватывать весь трафик
singbox_config = {
    "log": {
        "level": "info",
        "timestamp": True
    },
    "inbounds": [
        {
            "type": "tun",
            "tag": "tun-in",
            "interface_name": "singbox-tun",
            "inet4_address": "172.19.0.1/30",
            "auto_route": True,
            "strict_route": True,
            "stack": "system",
            "sniff": True
        }
    ],
    "outbounds": [
        {
            "type": "socks",
            "tag": "proxy",
            "server": PROXY_HOST,
            "server_port": PROXY_PORT,
            "username": PROXY_USER,
            "password": PROXY_PASS
        },
        {
            "type": "direct",
            "tag": "direct"
        },
        {
            "type": "block",
            "tag": "block"
        }
    ],
    "route": {
        "rules": [
            {
                "ip_cidr": [f"{PROXY_HOST}/32"],
                "outbound": "direct"
            },
            {
                "ip_cidr": ["10.66.66.0/24"],
                "outbound": "direct"
            },
            {
                "port": [22, 3389],
                "outbound": "direct"
            }
        ],
        "final": "proxy",
        "auto_detect_interface": True
    }
}

config_json = json.dumps(singbox_config, indent=2)
config_b64 = base64.b64encode(config_json.encode('utf-8')).decode()

result = ssh(f'''
$configPath = "C:\\sing-box\\config.json"
$configB64 = "{config_b64}"
$configBytes = [Convert]::FromBase64String($configB64)
$configText = [System.Text.Encoding]::UTF8.GetString($configBytes)

[IO.File]::WriteAllText($configPath, $configText, [System.Text.Encoding]::UTF8)

if (Test-Path $configPath) {{
    Write-Output "CONFIG_CREATED:$configPath"
    Write-Output ""
    Get-Content $configPath
}} else {{
    Write-Output "CONFIG_FAILED"
}}
''')
print(result)

# Шаг 3: Проверить конфиг
print("\n3. Проверка конфига...")

result = ssh(r'''
$exe = "C:\sing-box\sing-box.exe"
$config = "C:\sing-box\config.json"

if ((Test-Path $exe) -and (Test-Path $config)) {
    Write-Output "Checking config..."
    & $exe check -c $config 2>&1
} else {
    Write-Output "Files missing"
}
''')
print(result)

# Шаг 4: Установить как службу Windows
print("\n4. Установка службы...")

result = ssh(r'''
$exe = "C:\sing-box\sing-box.exe"
$config = "C:\sing-box\config.json"

# Остановить если работает
$svc = Get-Service sing-box -ErrorAction SilentlyContinue
if ($svc) {
    Stop-Service sing-box -ErrorAction SilentlyContinue
    sc.exe delete sing-box 2>$null
    Start-Sleep 2
}

# Создать службу через NSSM или напрямую
# sing-box не имеет встроенной команды install service, используем sc.exe

Write-Output "Creating service..."
$binPath = "`"$exe`" run -c `"$config`""
sc.exe create sing-box binPath= $binPath start= auto DisplayName= "Sing-Box Proxy" 2>&1

Start-Sleep 2

$svc = Get-Service sing-box -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output "SERVICE_CREATED:$($svc.Status)"
} else {
    Write-Output "SERVICE_FAILED - trying alternative..."

    # Попробовать через NSSM или WinSW
    # Пока запустим вручную
}
''')
print(result)

# Шаг 5: Запустить sing-box
print("\n5. Запуск sing-box...")

result = ssh(r'''
$exe = "C:\sing-box\sing-box.exe"
$config = "C:\sing-box\config.json"

# Попытка через службу
$svc = Get-Service sing-box -ErrorAction SilentlyContinue
if ($svc) {
    try {
        Start-Service sing-box -ErrorAction Stop
        Start-Sleep 3
        $svc = Get-Service sing-box
        Write-Output "SERVICE:$($svc.Status)"
    } catch {
        Write-Output "SERVICE_START_ERROR:$($_.Exception.Message)"
    }
}

# Если служба не работает, запустить процесс
$proc = Get-Process sing-box -ErrorAction SilentlyContinue
if (!$proc) {
    Write-Output "Starting as process..."

    # Создать scheduled task для запуска
    $taskName = "SingBoxRun"
    schtasks /Delete /TN $taskName /F 2>&1 | Out-Null

    $action = "Start-Process -FilePath '$exe' -ArgumentList 'run','-c','$config' -WindowStyle Hidden"
    $psPath = "C:\sing-box\start.ps1"
    $action | Out-File $psPath -Encoding utf8

    schtasks /Create /TN $taskName /TR "powershell.exe -ExecutionPolicy Bypass -File $psPath" /SC ONSTART /RU "SYSTEM" /RL HIGHEST /F 2>&1
    schtasks /Run /TN $taskName 2>&1

    Start-Sleep 5

    $proc = Get-Process sing-box -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "PROCESS_STARTED:PID=$($proc.Id)"
    } else {
        Write-Output "PROCESS_FAILED"
    }
}
''')
print(result)

# Шаг 6: Проверка IP
print("\n6. Проверка IP...")
time.sleep(5)

result = ssh(r'''
Write-Output "Current external IP:"
$ip = curl.exe -s --max-time 15 https://api.ipify.org 2>$null
Write-Output "IP:$ip"

if ($ip -eq "83.239.242.138") {
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "SUCCESS! Traffic goes through proxy!"
    Write-Output "=========================================="
} elseif ($ip -eq "62.84.101.97") {
    Write-Output ""
    Write-Output "IP is server IP - sing-box may not be routing yet"
}

# Статус процесса
$proc = Get-Process sing-box -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output ""
    Write-Output "sing-box: Running (PID=$($proc.Id))"
} else {
    Write-Output ""
    Write-Output "sing-box: Not running"
}
''')
print(result)

print("\n" + "="*70)
print("  ГОТОВО")
print("="*70)
