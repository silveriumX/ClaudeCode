---
name: windows-vps-deploy
description: Деплой и управление процессами на Windows VPS через WinRM (PowerShell Remoting). Загрузка файлов, запуск/остановка ботов, проверка логов, диагностика. Используй при любом деплое на Windows Server.
disable-model-invocation: true
---

# Windows VPS Deploy via WinRM

SSH на Windows Server часто не работает (нет OpenSSH). Используем WinRM (PowerShell Remoting).

## КРИТИЧЕСКИ ВАЖНО: что работает, что нет

### НЕ РАБОТАЕТ на Windows VPS:

1. **SSH через paramiko** — Windows Server часто не имеет OpenSSH, paramiko получает `Error reading SSH protocol banner`
2. **Start-Process через WinRM** — процесс УМИРАЕТ когда WinRM сессия закрывается
3. **PowerShell `&` operator** для фоновых задач через WinRM — не работает надёжно
4. **UTF-8 BOM в .env** — `Set-Content -Encoding UTF8` добавляет BOM, python-dotenv может не прочитать
5. **`\b` в путях внутри PowerShell строк** — `\b` = backspace, `C:\bot.log` -> `C:<backspace>ot.log`

### РАБОТАЕТ:

1. **WinRM (PowerShell Remoting)** — основной метод подключения
2. **DETACHED_PROCESS** — запуск через Python subprocess.Popen с creationflags
3. **Here-string @'...'@** — для передачи файлов через WinRM
4. **[System.IO.File]::WriteAllText** — для записи файлов без BOM
5. **os.path.join** — для безопасных путей без `\b` проблемы

## Шаблон подключения (Python)

```python
"""Template for Windows VPS operations via WinRM"""
import sys, io, subprocess
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

VPS_HOST = "CHANGE_ME"
VPS_USER = "Administrator"
VPS_PASS = "CHANGE_ME"

def run_on_vps(remote_commands, timeout=60):
    """Execute PowerShell commands on remote Windows VPS."""
    ps_script = f'''
$password = ConvertTo-SecureString "{VPS_PASS}" -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential("{VPS_USER}", $password)
$so = New-PSSessionOption -SkipCACheck -SkipCNCheck -SkipRevocationCheck
try {{
    $session = New-PSSession -ComputerName {VPS_HOST} -Credential $cred -SessionOption $so -ErrorAction Stop
    Invoke-Command -Session $session -ScriptBlock {{ {remote_commands} }}
    Remove-PSSession $session
}} catch {{
    Write-Error "WinRM ERROR: $_"
}}
'''
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def add_trusted_host():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f'Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "{VPS_HOST}" -Force -ErrorAction SilentlyContinue'],
        capture_output=True, timeout=10
    )
```

## Операции

### 1. Остановить процесс

```python
stdout, _, _ = run_on_vps('''
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Output "Stopped"
''')
```

### 2. Записать .env файл (БЕЗ BOM!)

```powershell
# НЕПРАВИЛЬНО - добавляет BOM:
Set-Content -Path ".env" -Value $envText -Encoding UTF8

# ПРАВИЛЬНО - без BOM:
[System.IO.File]::WriteAllText("C:\\MyApp\\.env", $envText, [System.Text.UTF8Encoding]::new($false))
```

### 3. Запустить процесс PERSISTENT (переживает закрытие WinRM)

**САМАЯ ЧАСТАЯ ОШИБКА**: `Start-Process` через WinRM создаёт процесс, привязанный к сессии.

**РЕШЕНИЕ**: Python subprocess.Popen с DETACHED_PROCESS:

```python
starter_code = """import subprocess, sys, os
app_dir = os.path.join("C:", os.sep, "MyApp")
log_out = os.path.join(app_dir, "app.log")
log_err = os.path.join(app_dir, "app_error.log")
proc = subprocess.Popen(
    [sys.executable, "bot.py"],
    cwd=app_dir,
    stdout=open(log_out, "w", encoding="utf-8"),
    stderr=open(log_err, "w", encoding="utf-8"),
    creationflags=0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
)
print("PID: " + str(proc.pid))
"""
```

### 4. Проверить статус

```python
stdout, _, _ = run_on_vps('''
    $proc = Get-Process python -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "RUNNING PID: $($proc.Id)"
    } else {
        Write-Output "NOT RUNNING"
    }
    Write-Output "=== ERRORS ==="
    Get-Content "C:\\MyApp\\app_error.log" -ErrorAction SilentlyContinue | Select-Object -Last 20
    Write-Output "=== LOG ==="
    Get-Content "C:\\MyApp\\app.log" -ErrorAction SilentlyContinue | Select-Object -Last 20
''')
```

### 5. Диагностика (бот не запускается)

```python
stdout, stderr, _ = run_on_vps('''
    cd C:\\MyApp

    # Syntax check
    python -m py_compile bot.py 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Output "SYNTAX: OK" } else { Write-Output "SYNTAX: ERROR" }

    # Direct run test (6 seconds)
    $pinfo = New-Object System.Diagnostics.ProcessStartInfo
    $pinfo.FileName = "python"
    $pinfo.Arguments = "-u bot.py"
    $pinfo.WorkingDirectory = "C:\\MyApp"
    $pinfo.RedirectStandardOutput = $true
    $pinfo.RedirectStandardError = $true
    $pinfo.UseShellExecute = $false
    $pinfo.CreateNoWindow = $true
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $pinfo
    $p.Start() | Out-Null
    Start-Sleep -Seconds 6
    if ($p.HasExited) {
        $err = $p.StandardError.ReadToEnd()
        Write-Output "CRASHED: exit=$($p.ExitCode)"
        Write-Output "ERROR: $err"
    } else {
        Write-Output "RUNNING OK (PID: $($p.Id))"
        $p.Kill()
    }
''', timeout=30)
print(stdout)
print(stderr)  # IMPORTANT: real Python errors often end up here
```

## Полный деплой-скрипт (copy-paste ready)

```python
"""Full deploy: stop -> upload -> write .env -> start -> verify"""
import sys, io, subprocess, time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

VPS = "CHANGE_ME"
USER = "Administrator"
PASS = "CHANGE_ME"
REMOTE_DIR = "C:\\\\MyApp"

bot_content = Path("bot.py").read_text(encoding="utf-8")

start_script = '''import subprocess, sys, os
app_dir = os.path.join("C:", os.sep, "MyApp")
log_out = os.path.join(app_dir, "bot.log")
log_err = os.path.join(app_dir, "bot_error.log")
proc = subprocess.Popen(
    [sys.executable, "bot.py"],
    cwd=app_dir,
    stdout=open(log_out, "w", encoding="utf-8"),
    stderr=open(log_err, "w", encoding="utf-8"),
    creationflags=0x00000008 | 0x00000200
)
print("PID: " + str(proc.pid))
'''

env_content = "KEY1=value1\\nKEY2=value2"

# Add to trusted hosts
subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     f'Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "{VPS}" -Force -ErrorAction SilentlyContinue'],
    capture_output=True, timeout=10
)

ps = f'''
$password = ConvertTo-SecureString "{PASS}" -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential("{USER}", $password)
$so = New-PSSessionOption -SkipCACheck -SkipCNCheck -SkipRevocationCheck
$session = New-PSSession -ComputerName {VPS} -Credential $cred -SessionOption $so

$bot = @'
{bot_content}
'@

$starter = @'
{start_script}
'@

$envTxt = @'
{env_content}
'@

Invoke-Command -Session $session -ScriptBlock {{
    param($botCode, $starterCode, $envText)

    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 2

    Set-Content -Path "{REMOTE_DIR}\\bot.py" -Value $botCode -Encoding UTF8 -Force
    Set-Content -Path "{REMOTE_DIR}\\start_detached.py" -Value $starterCode -Encoding UTF8 -Force
    [System.IO.File]::WriteAllText("{REMOTE_DIR}\\.env", $envText, [System.Text.UTF8Encoding]::new($false))

    cd {REMOTE_DIR}
    $out = python start_detached.py 2>&1
    Write-Output "START: $out"

    Start-Sleep 6

    $proc = Get-Process python -ErrorAction SilentlyContinue
    if ($proc) {{ Write-Output "OK: RUNNING" }} else {{ Write-Output "FAIL: NOT RUNNING" }}

    Write-Output "=== errors ==="
    Get-Content "{REMOTE_DIR}\\bot_error.log" -EA SilentlyContinue | Select -Last 15
    Write-Output "=== log ==="
    Get-Content "{REMOTE_DIR}\\bot.log" -EA SilentlyContinue | Select -Last 10

}} -ArgumentList $bot, $starter, $envTxt

Remove-PSSession $session
'''

result = subprocess.run(
    ["powershell", "-NoProfile", "-Command", ps],
    capture_output=True, text=True, timeout=120,
    encoding='utf-8', errors='replace'
)
print(result.stdout)
if result.stderr.strip():
    print("STDERR:", result.stderr[:500])
```

## Чеклист перед деплоем

- [ ] VPS_HOST, VPS_USER, VPS_PASS заполнены
- [ ] `add_trusted_host()` вызван хотя бы раз
- [ ] .env пишется через `WriteAllText` (без BOM)
- [ ] Пути в start_detached.py используют `os.path.join()` (НЕ raw strings с `\b`)
- [ ] Процесс запускается через `start_detached.py` с DETACHED_PROCESS flag
- [ ] После запуска ждём 5-6 секунд перед проверкой
- [ ] Проверяем И stdout И stderr (Python ошибки часто в stderr)

## Частые ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `Error reading SSH protocol banner` | Нет SSH на Windows Server | Используй WinRM |
| `Token is invalid!` | .env не читается (BOM или путь) | WriteAllText без BOM + os.path.join |
| Процесс умирает после деплоя | Start-Process привязан к WinRM сессии | DETACHED_PROCESS через Python |
| `\x08` в путях | `\b` = backspace в строках | os.path.join или `\\\\` |
| WinRM timeout | Медленная сеть | Увеличь timeout |
| `Access Denied` | WinRM не настроен | Добавь в TrustedHosts |

## Известные VPS серверы

| Проект | IP | User | Метод | Dir |
|--------|-----|------|-------|-----|
| EnglishTutorBot | 195.177.94.53 | Administrator | WinRM | C:\EnglishTutorBot |
| FinanceBot | 195.177.94.189 | root | SSH (Linux) | /root/finance_bot |
