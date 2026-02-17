#Requires -RunAsAdministrator
<#
  Находит источник постоянно запускающегося javaw (clint):
  - родительский процесс по PID с полным путём через CIM,
  - все процессы из папки C:\clint,
  - задачи Планировщика, автозагрузка реестра, папки автозагрузки.
  Запуск: .\find_javaw_source.ps1   или с PID родителя: .\find_javaw_source.ps1 -ParentPid 3520
#>
param([int]$ParentPid = 3520)

$ErrorActionPreference = "Continue"

Write-Host "`n=== 1. Родительский процесс (PID $ParentPid) — полный путь через CIM ===" -ForegroundColor Cyan
$parent = Get-CimInstance Win32_Process -Filter "ProcessId=$ParentPid" -ErrorAction SilentlyContinue
if ($parent) {
    Write-Host "  Имя:           $($parent.Name)"
    Write-Host "  Полный путь:   $($parent.ExecutablePath)"
    Write-Host "  Командная строка:"
    Write-Host "    $($parent.CommandLine)" -ForegroundColor Gray
} else {
    Write-Host "  Процесс с PID $ParentPid не найден (уже завершён?)." -ForegroundColor Yellow
}

Write-Host "`n=== 2. Все процессы, связанные с C:\clint (кто сейчас запущен) ===" -ForegroundColor Cyan
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -and $_.ExecutablePath -like "*clint*" } | ForEach-Object {
    Write-Host "  PID $($_.ProcessId): $($_.ExecutablePath)"
    Write-Host "    Команда: $($_.CommandLine)" -ForegroundColor Gray
}
$byName = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path -like "*clint*" }
if ($byName) {
    foreach ($p in $byName) { Write-Host "  (Get-Process) PID $($p.Id): $($p.Path)" }
}

Write-Host "`n=== 3. Задачи Планировщика (clint / javaw / Java) ===" -ForegroundColor Cyan
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
    $_.TaskPath -like "*clint*" -or $_.TaskName -like "*clint*" -or
    $_.TaskName -like "*javaw*" -or $_.TaskName -like "*java*" -or
    $_.Actions.Execute -like "*clint*" -or $_.Actions.Execute -like "*javaw*"
}
if (-not $tasks) {
    $tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
        ($_.Actions.Execute -like "*clint*") -or ($_.Actions.Arguments -like "*clint*")
    }
}
foreach ($t in $tasks) {
    Write-Host "  Задача: $($t.TaskPath)$($t.TaskName)  State: $($t.State)"
    $t.Actions | ForEach-Object { Write-Host "    Выполнить: $($_.Execute) $($_.Arguments)" -ForegroundColor Gray }
}

Write-Host "`n=== 4. Автозагрузка реестра (Run / RunOnce) — clint, java, javaw ===" -ForegroundColor Cyan
$paths = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
)
foreach ($regPath in $paths) {
    if (-not (Test-Path $regPath)) { continue }
    Get-ItemProperty $regPath -ErrorAction SilentlyContinue | ForEach-Object {
        $_.PSObject.Properties | Where-Object { $_.Name -notin @("PSPath","PSParentPath","PSChildName","PSDrive","PSProvider") } | ForEach-Object {
            if ($_.Value -match "clint|javaw|java") {
                Write-Host "  $regPath  ->  $($_.Name) = $($_.Value)" -ForegroundColor Gray
            }
        }
    }
}

Write-Host "`n=== 5. Папки автозагрузки (ярлыки/файлы с clint) ===" -ForegroundColor Cyan
$startupPaths = @(
    [Environment]::GetFolderPath("Startup"),
    [Environment]::GetFolderPath("CommonStartup")
)
foreach ($dir in $startupPaths) {
    if (-not (Test-Path $dir)) { continue }
    Get-ChildItem $dir -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "clint|javaw" -or (Get-Content $_.FullName -EA SilentlyContinue -Raw) -match "clint" } | ForEach-Object {
        Write-Host "  $dir\$($_.Name)" -ForegroundColor Gray
    }
}

Write-Host "`n=== 6. Содержимое C:\clint\clint (что там лежит — возможный лаунчер) ===" -ForegroundColor Cyan
if (Test-Path "C:\clint\clint") {
    Get-ChildItem "C:\clint\clint" -ErrorAction SilentlyContinue | Select-Object Name, FullName, LastWriteTime | Format-Table -AutoSize
    $exes = Get-ChildItem "C:\clint\clint" -Recurse -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 20 FullName, LastWriteTime
    if ($exes) {
        Write-Host "  EXE в папке:"
        $exes | ForEach-Object { Write-Host "    $($_.FullName)" -ForegroundColor Gray }
    }
} else {
    Write-Host "  Папка C:\clint\clint не найдена." -ForegroundColor Yellow
}

Write-Host "`nГотово. Источник постоянного запуска — смотри пункты 1 (родитель), 3 (задачи), 4 (реестр), 5 (автозагрузка).`n"
