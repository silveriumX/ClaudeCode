# Удаление clint (Runtime Brocker / SystemWatchdog) с Windows

Пошаговая инструкция: найти процесс, отключить трафик, убрать автозагрузку, завершить процессы и удалить папку. Все команды выполнять **в PowerShell от имени администратора**.

На других компьютерах путь может быть иным (не `C:\clint\clint`) — тогда подставьте свой путь в командах.

---

## Шаг 1. Найти источник (кто запускает, откуда автозапуск)

Вставьте команду **целиком**. Переменная должна быть `$parentPid` (не `$pid` — в PowerShell она зарезервирована).

```powershell
$parentPid=3520; Write-Host "`n=== Родитель PID $parentPid (путь через CIM) ===" -ForegroundColor Cyan; $p=Get-CimInstance Win32_Process -Filter "ProcessId=$parentPid" -EA SilentlyContinue; if($p){ Write-Host "  Имя: $($p.Name)"; Write-Host "  Путь: $($p.ExecutablePath)"; Write-Host "  Команда: $($p.CommandLine)" } else { Write-Host "  Процесс не найден" }; Write-Host "`n=== Процессы из C:\clint ===" -ForegroundColor Cyan; Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.ExecutablePath -like "*clint*" } | ForEach-Object { Write-Host "  PID $($_.ProcessId): $($_.ExecutablePath)"; Write-Host "    $($_.CommandLine)" }; Write-Host "`n=== Задачи (clint/javaw) ===" -ForegroundColor Cyan; Get-ScheduledTask -EA SilentlyContinue | Where-Object { $_.Actions.Execute -like "*clint*" -or $_.Actions.Arguments -like "*clint*" -or $_.TaskName -like "*clint*" } | ForEach-Object { Write-Host "  $($_.TaskPath)$($_.TaskName) [$($_.State)]"; $_.Actions | % { Write-Host "    $($_.Execute) $($_.Arguments)" } }; Write-Host "`n=== Реестр Run (clint) ===" -ForegroundColor Cyan; foreach($r in @("HKCU:\Software\Microsoft\Windows\CurrentVersion\Run","HKLM:\Software\Microsoft\Windows\CurrentVersion\Run")){ Get-ItemProperty $r -EA SilentlyContinue | % { $_.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match 'clint|javaw' } | % { Write-Host "  $($_.Name)=$($_.Value)" } } }; if(Test-Path "C:\clint\clint"){ Write-Host "`n=== EXE в C:\clint\clint ===" -ForegroundColor Cyan; Get-ChildItem "C:\clint\clint" -Recurse -Filter "*.exe" -EA SilentlyContinue | Select-Object -First 15 | % { Write-Host "  $($_.FullName)" } }
```

По выводу смотрите:
- **Процессы из C:\clint** — кто сейчас запущен (Runtime Brocker, javaw и т.д.).
- **Реестр Run** — запись автозагрузки (часто `SystemWatchdog = C:\clint\clint\Runtime Brocker.exe`).

Если на другом ПК папка не `C:\clint`, замените в команде `*clint*` и путь `C:\clint\clint` на свой.

---

## Шаг 2. Заблокировать трафик для процесса (опционально)

Чтобы процесс перестал использовать сеть (до удаления), создаются правила брандмауэра по пути к exe. Запускайте, когда процесс **уже запущен** (чтобы был известен путь).

Для всех запущенных `javaw`:

```powershell
$ErrorActionPreference='Stop'; $prefix='BlockTraffic_trace_script_'; foreach($p in (Get-Process -Name javaw -EA SilentlyContinue)){ $path=$p.Path; if(-not $path){Write-Host "PID $($p.Id): путь не получен"; continue}; $parentId=(Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").ParentProcessId; $parent=if($parentId){(Get-Process -Id $parentId -EA SilentlyContinue).Path}else{$null}; Write-Host "--- javaw PID $($p.Id) ---"; Write-Host "  Путь: $path"; Write-Host "  Родитель: $parent"; $ruleName=$prefix+[System.BitConverter]::ToString((New-Object Security.Cryptography.SHA1Managed).ComputeHash([Text.Encoding]::UTF8.GetBytes($path))).Replace('-','').Substring(0,12); if(Get-NetFirewallRule -DisplayName $ruleName -EA SilentlyContinue){Write-Host "  Уже заблокирован" -ForegroundColor Yellow; continue}; New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Program $path -Action Block -Profile Any|Out-Null; New-NetFirewallRule -DisplayName ($ruleName+'_In') -Direction Inbound -Program $path -Action Block -Profile Any|Out-Null; Write-Host "  Трафик заблокирован" -ForegroundColor Green }; if(-not (Get-Process -Name javaw -EA SilentlyContinue)){Write-Host "javaw не найден." -ForegroundColor Yellow }
```

---

## Шаг 3. Отключить автозагрузку, завершить процессы, удалить папку

Одна команда: удаляет запись **SystemWatchdog** из реестра (Run), завершает все процессы из `C:\clint`, удаляет папку `C:\clint\clint`.

```powershell
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "SystemWatchdog" -EA SilentlyContinue; Remove-ItemProperty -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "SystemWatchdog" -EA SilentlyContinue; Write-Host "Автозагрузка отключена" -ForegroundColor Green; Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.ExecutablePath -like "*clint*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue; Write-Host "Остановлен PID $($_.ProcessId)" }; Remove-Item -Path "C:\clint\clint" -Recurse -Force -EA SilentlyContinue; if(Test-Path "C:\clint\clint"){ Write-Host "Папка занята — перезагрузка, затем удали вручную C:\clint\clint" -ForegroundColor Yellow } else { Write-Host "Папка C:\clint\clint удалена" -ForegroundColor Green }
```

Если на другом ПК папка иная — замените `*clint*` и `C:\clint\clint` на свой путь.

---

## Шаг 4. Если папка не удалилась («папка занята»)

1. **Перезагрузите ПК.**
2. После входа снова откройте **PowerShell от имени администратора** и выполните:

```powershell
Remove-Item -Path "C:\clint\clint" -Recurse -Force
```

Если не поможет — через cmd (администратор):

```cmd
rd /s /q "C:\clint\clint"
```

Удалить весь каталог `C:\clint`:

```powershell
Remove-Item -Path "C:\clint" -Recurse -Force
```

или в cmd:

```cmd
rd /s /q "C:\clint"
```

---

## Краткий порядок на новом компьютере

| Действие | Команда |
|----------|--------|
| 1. Найти процессы и автозагрузку | Шаг 1 (большая команда с `$parentPid`) |
| 2. (По желанию) Заблокировать трафик | Шаг 2 (правила брандмауэра для javaw) |
| 3. Удалить автозагрузку + процессы + папку | Шаг 3 (одна строка с Remove-ItemProperty и Remove-Item) |
| 4. Если папка осталась | Перезагрузка → Шаг 4 |

---

## Файлы скриптов в репозитории

- `Scripts/trace_and_remove_process.ps1` — поиск процесса, родитель, блокировка трафика (`-BlockTraffic`), завершение (`-Kill`).
- `Scripts/find_javaw_source.ps1` — поиск источника (родитель, задачи, реестр, папка).
- `Scripts/remove_clint_source.ps1` — удаление SystemWatchdog, завершение процессов, удаление `C:\clint\clint`.

Все команды выше — рабочие однострочники без зависимости от этих скриптов; скрипты дают те же действия с параметрами.
