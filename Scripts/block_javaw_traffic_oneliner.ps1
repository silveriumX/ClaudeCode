# Одна команда: найти javaw, показать инфо и заблокировать трафик.
# Запуск: PowerShell от имени администратора, вставьте блок целиком.

$ErrorActionPreference = 'Stop'
$prefix = 'BlockTraffic_trace_script_'
foreach ($p in (Get-Process -Name javaw -ErrorAction SilentlyContinue)) {
  $path = $p.Path
  if (-not $path) { Write-Host "PID $($p.Id): путь не получен"; continue }
  $parentId = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").ParentProcessId
  $parent = if ($parentId) { (Get-Process -Id $parentId -EA SilentlyContinue).Path } else { $null }
  Write-Host "--- javaw PID $($p.Id) ---"
  Write-Host "  Путь: $path"
  Write-Host "  Родитель PID: $parentId  Путь: $parent"
  $ruleName = $prefix + [System.BitConverter]::ToString((New-Object Security.Cryptography.SHA1Managed).ComputeHash([Text.Encoding]::UTF8.GetBytes($path))).Replace('-','').Substring(0,12)
  if (Get-NetFirewallRule -DisplayName $ruleName -EA SilentlyContinue) { Write-Host "  Уже заблокирован: $ruleName" -ForegroundColor Yellow; continue }
  New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Program $path -Action Block -Profile Any | Out-Null
  New-NetFirewallRule -DisplayName ($ruleName+'_In') -Direction Inbound -Program $path -Action Block -Profile Any | Out-Null
  Write-Host "  Трафик заблокирован (правила: $ruleName)" -ForegroundColor Green
}
if (-not (Get-Process -Name javaw -EA SilentlyContinue)) { Write-Host "Процесс javaw не найден. Запустите его и выполните команду снова." -ForegroundColor Yellow }
