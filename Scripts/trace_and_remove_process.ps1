#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Выслеживает процесс (по умолчанию javaw.exe), находит родителя и путь к источнику для удаления.
.DESCRIPTION
  Для процесса показывает: полный путь, командную строку, родительский процесс, дерево процессов.
  Опционально: завершение процесса, блокировка трафика через брандмауэр, вывод инструкций по удалению.
.PARAMETER ProcessId
  PID процесса (например 6016). Если не указан — ищет все javaw.exe.
.PARAMETER ProcessName
  Имя процесса (по умолчанию javaw).
.PARAMETER Kill
  Завершить найденный процесс после вывода информации.
.PARAMETER ShowTree
  Показать дерево процессов от корня до целевого.
.PARAMETER BlockTraffic
  Заблокировать весь сетевой трафик для этого exe в брандмауэре (исходящий и входящий). Процесс трафик не сжигает.
.PARAMETER UnblockTraffic
  Удалить правило блокировки трафика для этого процесса (по пути exe).
.EXAMPLE
  .\trace_and_remove_process.ps1 -ProcessId 6016
  .\trace_and_remove_process.ps1 -ProcessName javaw -BlockTraffic
  .\trace_and_remove_process.ps1 -ProcessName javaw -UnblockTraffic
#>

param(
    [int]   $ProcessId   = 0,
    [string] $ProcessName = "javaw",
    [switch] $Kill,
    [switch] $ShowTree,
    [switch] $BlockTraffic,
    [switch] $UnblockTraffic
)

$Script:FirewallRulePrefix = "BlockTraffic_trace_script_"

$ErrorActionPreference = "Stop"

function Get-ProcessCommandLine {
    param([int]$pid)
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $pid"
        if ($proc) { return $proc.CommandLine }
    } catch {}
    return $null
}

function Get-ParentProcessId {
    param([int]$pid)
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $pid"
        if ($proc) { return $proc.ParentProcessId }
    } catch {}
    return 0
}

function Get-ProcessTree {
    param([int]$pid, [int]$depth = 0)
    $indent = "  " * $depth
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $pid"
        if (-not $proc) { return }
        $name = $proc.ExecutablePath
        if (-not $name) { $name = $proc.Name }
        Write-Host "$indent[$pid] $name" -ForegroundColor $(if ($depth -eq 0) { "Yellow" } else { "Gray" })
        $parentId = $proc.ParentProcessId
        if ($parentId -and $parentId -ne 0 -and $depth -lt 15) {
            Get-ProcessTree -pid $parentId -depth ($depth + 1)
        }
    } catch {}
}

function Resolve-ProcessTarget {
    if ($ProcessId -gt 0) {
        $p = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($p) { return @($p) }
        Write-Warning "Процесс с PID $ProcessId не найден."
        return @()
    }
    $all = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    if (-not $all) {
        Write-Warning "Процессы с именем '$ProcessName' не найдены."
        return @()
    }
    return $all
}

function Get-FirewallRuleNameForPath {
    param([string]$exePath)
    if (-not $exePath) { return $null }
    $hash = [System.BitConverter]::ToString(
        (New-Object System.Security.Cryptography.SHA1Managed).ComputeHash(
            [Text.Encoding]::UTF8.GetBytes($exePath))
    ).Replace("-", "").Substring(0, 12)
    return $Script:FirewallRulePrefix + $hash
}

function Add-FirewallBlockForProgram {
    param([string]$exePath, [string]$displayName)
    if (-not $exePath -or -not (Test-Path -LiteralPath $exePath)) {
        Write-Warning "Путь к exe не найден или недоступен: $exePath"
        return $false
    }
    $ruleName = Get-FirewallRuleNameForPath -exePath $exePath
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "  Правило блокировки уже есть: $ruleName" -ForegroundColor Yellow
        return $true
    }
    try {
        New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Program $exePath -Action Block -Profile Any -ErrorAction Stop | Out-Null
        New-NetFirewallRule -DisplayName ($ruleName + "_In") -Direction Inbound -Program $exePath -Action Block -Profile Any -ErrorAction Stop | Out-Null
        Write-Host "  Созданы правила брандмауэра: трафик для этого exe заблокирован (исходящий и входящий)." -ForegroundColor Green
        return $true
    } catch {
        Write-Warning "Не удалось создать правило брандмауэра: $_"
        return $false
    }
}

function Remove-FirewallBlockForProgram {
    param([string]$exePath)
    $ruleName = Get-FirewallRuleNameForPath -exePath $exePath
    $removed = 0
    Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -eq $ruleName -or $_.DisplayName -eq ($ruleName + "_In") } | ForEach-Object {
        $_ | Remove-NetFirewallRule -ErrorAction SilentlyContinue
        $removed++
    }
    return $removed
}

function UnblockTraffic-AllByPrefix {
    $rules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like ($Script:FirewallRulePrefix + "*") }
    foreach ($r in $rules) {
        $r | Remove-NetFirewallRule -ErrorAction SilentlyContinue
        Write-Host "  Удалено правило: $($r.DisplayName)" -ForegroundColor Gray
    }
    return $rules.Count
}

# --- main ---
if ($UnblockTraffic -and -not $BlockTraffic -and -not $ProcessId -and -not $Kill) {
    Write-Host "`n=== Удаление правил блокировки трафика (все, созданные этим скриптом) ===" -ForegroundColor Cyan
    $n = UnblockTraffic-AllByPrefix
    Write-Host "Удалено правил: $n`n"
    exit 0
}

Write-Host "`n=== Поиск процесса (имя: $ProcessName" -NoNewline
if ($ProcessId -gt 0) { Write-Host ", PID: $ProcessId" -NoNewline }
Write-Host ") ===`n" -ForegroundColor Cyan

$targets = Resolve-ProcessTarget
if ($targets.Count -eq 0) {
    if ($UnblockTraffic) {
        Write-Host "Процесс не найден. Удаляю все правила блокировки этого скрипта..." -ForegroundColor Yellow
        $n = UnblockTraffic-AllByPrefix
        Write-Host "Удалено правил: $n`n"
    }
    exit 1
}

foreach ($proc in $targets) {
    $pid = $proc.Id
    Write-Host "--- Процесс: $($proc.ProcessName) (PID $pid) ---" -ForegroundColor Green

    $path = $proc.Path
    if ($path) {
        Write-Host "  Путь:        $path"
        $dir = Split-Path $path
        Write-Host "  Каталог:     $dir"
        if (Test-Path $path) {
            $item = Get-Item $path
            Write-Host "  Размер:      $([math]::Round($item.Length/1KB, 2)) KB"
            Write-Host "  Изменён:     $($item.LastWriteTime)"
        }
    } else {
        Write-Host "  Путь:        (не удалось получить)"
    }

    $cmd = Get-ProcessCommandLine -pid $pid
    if ($cmd) {
        Write-Host "  Командная строка:"
        Write-Host "    $cmd" -ForegroundColor Gray
    }

    $parentId = Get-ParentProcessId -pid $pid
    if ($parentId -gt 0) {
        $parent = Get-Process -Id $parentId -ErrorAction SilentlyContinue
        $parentPath = $null
        if ($parent) { $parentPath = $parent.Path }
        Write-Host "  Родитель:    PID $parentId - $($parent.ProcessName)"
        if ($parentPath) { Write-Host "              $parentPath" }
    } else {
        Write-Host "  Родитель:    (нет или системный)"
    }

    if ($ShowTree) {
        Write-Host "`n  Дерево процессов (снизу вверх):" -ForegroundColor Cyan
        Get-ProcessTree -pid $pid
    }

    Write-Host ""
}

# Блокировка трафика через брандмауэр
if ($BlockTraffic -and $targets.Count -gt 0) {
    Write-Host "=== Блокировка трафика в брандмауэре ===" -ForegroundColor Cyan
    $pathsDone = @{}
    foreach ($p in $targets) {
        $path = $p.Path
        if ($path -and -not $pathsDone[$path]) {
            Add-FirewallBlockForProgram -exePath $path -displayName $p.ProcessName
            $pathsDone[$path] = $true
        }
    }
    Write-Host "Готово. Этот exe больше не сможет отправлять или получать данные по сети.`n" -ForegroundColor Green
}

# Снять блокировку трафика
if ($UnblockTraffic -and $targets.Count -gt 0) {
    Write-Host "=== Снятие блокировки трафика ===" -ForegroundColor Cyan
    $pathsDone = @{}
    foreach ($p in $targets) {
        $path = $p.Path
        if ($path -and -not $pathsDone[$path]) {
            $n = Remove-FirewallBlockForProgram -exePath $path
            Write-Host "  Для $path удалено правил: $n" -ForegroundColor Gray
            $pathsDone[$path] = $true
        }
    }
    Write-Host ""
}

# Рекомендации по удалению
Write-Host "=== Рекомендации по удалению ===" -ForegroundColor Cyan
Write-Host @"
Чтобы процесс вообще не использовал трафик: запустите скрипт с ключом -BlockTraffic (правило в брандмауэре).
Чтобы потом разрешить трафик снова: -UnblockTraffic или -UnblockTraffic -ProcessName javaw (если процесс запущен).

1) Закройте приложение нормально (если это известная программа).
2) Иначе завершите процесс:
   Stop-Process -Id $($targets[0].Id) -Force
   или: taskkill /F /PID $($targets[0].Id)
3) Удалите папку/файлы по пути выше (каталог процесса).
4) Проверьте автозагрузку:
   - shell:startup (текущий пользователь)
   - shell:common startup
   - Задачи Планировщика (taskschd.msc)
   - Реестр: HKCU\...\Run, HKLM\...\Run
5) Если это Java-приложение — проверьте папки с Java и переменную JAVA_HOME.
"@ -ForegroundColor Gray

if ($Kill -and $targets.Count -gt 0) {
    Write-Host "Завершение процесса(ов) (ключ -Kill)..." -ForegroundColor Yellow
    foreach ($p in $targets) {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        Write-Host "  Остановлен PID $($p.Id)."
    }
}

Write-Host "`nГотово.`n"
