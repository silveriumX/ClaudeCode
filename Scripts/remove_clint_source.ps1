#Requires -RunAsAdministrator
<#
  Удаляет источник clint: автозагрузку в реестре, процессы, папку.
  Запуск: .\remove_clint_source.ps1
  Опции: -KillOnly (только процессы), -NoDeleteFolder (не удалять C:\clint\clint)
#>
param(
    [switch] $KillOnly,
    [switch] $NoDeleteFolder
)

$ErrorActionPreference = "Continue"
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regPathLM = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
$valueName = "SystemWatchdog"
$folder = "C:\clint\clint"

Write-Host "`n=== 1. Удаление автозагрузки (реестр Run) ===" -ForegroundColor Cyan
foreach ($path in $regPath, $regPathLM) {
    if (Test-Path $path) {
        $val = Get-ItemProperty $path -Name $valueName -ErrorAction SilentlyContinue
        if ($val) {
            Remove-ItemProperty -Path $path -Name $valueName -ErrorAction SilentlyContinue
            Write-Host "  Удалено: $path -> $valueName" -ForegroundColor Green
        } else {
            Write-Host "  Нет значения $valueName в $path" -ForegroundColor Gray
        }
    }
}

Write-Host "`n=== 2. Завершение процессов (Runtime Brocker, javaw из clint) ===" -ForegroundColor Cyan
Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.ExecutablePath -like "*clint*" } | ForEach-Object {
    $pid_ = $_.ProcessId
    $name = $_.Name
    $path = $_.ExecutablePath
    Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
    Write-Host "  Остановлен PID $pid_ : $name" -ForegroundColor Green
}

if ($KillOnly) {
    Write-Host "`nРежим -KillOnly: папка не удаляется.`n"
    exit 0
}

if ($NoDeleteFolder) {
    Write-Host "`nРежим -NoDeleteFolder: папка не удаляется.`n"
    exit 0
}

Write-Host "`n=== 3. Удаление папки C:\clint\clint ===" -ForegroundColor Cyan
if (Test-Path $folder) {
    try {
        Remove-Item -Path $folder -Recurse -Force -ErrorAction Stop
        Write-Host "  Папка удалена: $folder" -ForegroundColor Green
    } catch {
        Write-Host "  Не удалось удалить (файлы заняты?). Закройте все окна и перезапустите ПК, затем удалите вручную: $folder" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Папка не найдена: $folder" -ForegroundColor Gray
}

Write-Host "`nГотово. Перезагрузка рекомендуется.`n"
