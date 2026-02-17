# list_tasks_without_clickup_id.ps1 - List tasks in Work/Задачи that don't have **ClickUp ID:**
# Run: .\scripts\list_tasks_without_clickup_id.ps1
# Use for backfill: create these tasks in ClickUp and add ID to files, or let AI do it via skill.

param(
    [switch]$Brief   # Only count per file, no task lines
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TasksDir = Split-Path -Parent $ScriptDir

$mdFiles = Get-ChildItem -Path $TasksDir -Filter "*.md" -File | Where-Object { $_.Name -notmatch "^(БЫСТРЫЙ_СТАРТ|CLICKUP_СООТВЕТСТВИЕ|СИНХРОНИЗАЦИЯ_ПРИМЕР|ИНСТРУКЦИЯ|ДЕЛЕГИРОВАНИЕ)" }

$totalWithout = 0
$results = @()

foreach ($file in $mdFiles) {
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    if (-not $content) { continue }
    $lines = $content -split "`n"
    $without = @()
    $i = 0
    while ($i -lt $lines.Count) {
        $line = $lines[$i]
        $trimmed = $line.Trim()
        # Task line: numbered list (1. **...) or ### N. ...
        if ($trimmed -match "^\d+\.?\s*\*\*.+\*\*" -or $trimmed -match "^###\s+\d+\.\s+") {
            $nextLine = ""
            if ($i + 1 -lt $lines.Count) { $nextLine = $lines[$i + 1].Trim() }
            if ($nextLine -notmatch '^\*\*ClickUp ID:\*\*\s*`[^`]+`') {
                $without += $trimmed
            }
        }
        $i++
    }
    if ($without.Count -gt 0) {
        $totalWithout += $without.Count
        $results += [PSCustomObject]@{ File = $file.Name; Count = $without.Count; Tasks = $without }
    }
}

if ($Brief) {
    foreach ($r in $results) {
        Write-Host "$($r.File): $($r.Count) tasks without ClickUp ID"
    }
    Write-Host "Total: $totalWithout tasks without ClickUp ID"
} else {
    foreach ($r in $results) {
        Write-Host ""
        Write-Host "=== $($r.File) ($($r.Count)) ===" -ForegroundColor Cyan
        foreach ($t in $r.Tasks) {
            $short = if ($t.Length -gt 80) { $t.Substring(0, 77) + "..." } else { $t }
            Write-Host "  - $short"
        }
    }
    Write-Host ""
    Write-Host "Total: $totalWithout tasks without ClickUp ID" -ForegroundColor Yellow
    Write-Host "To sync: use skill ClickUp–Cursor Sync or ask AI to create these tasks in ClickUp and add ID."
}
