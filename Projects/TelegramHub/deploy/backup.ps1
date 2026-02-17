# TelegramHub Backup Script for Windows
# Creates backups of session files and data
#
# Usage:
#   .\backup.ps1           # Create backup
#   .\backup.ps1 -Restore  # Restore from latest backup
#   .\backup.ps1 -List     # List available backups

param(
    [switch]$Restore,
    [switch]$List,
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$BackupDir = Join-Path $ProjectDir "backups"
$MaxBackups = 7

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

function Create-Backup {
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupName = "telegramhub_backup_$Timestamp.zip"
    $BackupPath = Join-Path $BackupDir $BackupName

    Write-Host "Creating backup: $BackupPath" -ForegroundColor Cyan

    # Folders to backup
    $FoldersToBackup = @(
        (Join-Path $ProjectDir "accounts\sessions"),
        (Join-Path $ProjectDir "data"),
        (Join-Path $ProjectDir "drafts"),
        (Join-Path $ProjectDir "context")
    )

    # Create temp directory for backup
    $TempDir = Join-Path $env:TEMP "telegramhub_backup_$Timestamp"
    New-Item -ItemType Directory -Path $TempDir | Out-Null

    try {
        # Copy files to temp directory
        foreach ($Folder in $FoldersToBackup) {
            if (Test-Path $Folder) {
                $DestFolder = Join-Path $TempDir (Split-Path $Folder -Leaf)
                Copy-Item -Path $Folder -Destination $DestFolder -Recurse -Force
                Write-Host "  Backed up: $Folder" -ForegroundColor Gray
            }
        }

        # Create zip archive
        Compress-Archive -Path "$TempDir\*" -DestinationPath $BackupPath -Force

        Write-Host "Backup created: $BackupPath" -ForegroundColor Green

        # Show backup size
        $Size = (Get-Item $BackupPath).Length / 1MB
        Write-Host "Size: $([math]::Round($Size, 2)) MB" -ForegroundColor Gray

        # Clean old backups
        Write-Host "Cleaning old backups (keeping last $MaxBackups)..." -ForegroundColor Gray
        Get-ChildItem $BackupDir -Filter "telegramhub_backup_*.zip" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -Skip $MaxBackups |
            Remove-Item -Force
    }
    finally {
        # Clean up temp directory
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Restore-Backup {
    param([string]$File)

    if (-not $File) {
        # Get latest backup
        $File = Get-ChildItem $BackupDir -Filter "telegramhub_backup_*.zip" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1 -ExpandProperty FullName

        if (-not $File) {
            Write-Host "No backups found!" -ForegroundColor Red
            return
        }
    }

    if (-not (Test-Path $File)) {
        Write-Host "Backup file not found: $File" -ForegroundColor Red
        return
    }

    Write-Host "Restoring from: $File" -ForegroundColor Yellow
    Write-Host "WARNING: This will overwrite current data!" -ForegroundColor Red
    $Confirm = Read-Host "Continue? (y/n)"

    if ($Confirm -ne "y") {
        Write-Host "Cancelled." -ForegroundColor Gray
        return
    }

    # Extract to temp directory first
    $TempDir = Join-Path $env:TEMP "telegramhub_restore_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

    try {
        Expand-Archive -Path $File -DestinationPath $TempDir -Force

        # Restore each folder
        $FoldersToRestore = @("sessions", "data", "drafts", "context")
        foreach ($Folder in $FoldersToRestore) {
            $SourcePath = Join-Path $TempDir $Folder
            if (Test-Path $SourcePath) {
                $DestPath = switch ($Folder) {
                    "sessions" { Join-Path $ProjectDir "accounts\sessions" }
                    default { Join-Path $ProjectDir $Folder }
                }

                if (Test-Path $DestPath) {
                    Remove-Item -Path $DestPath -Recurse -Force
                }

                Copy-Item -Path $SourcePath -Destination $DestPath -Recurse -Force
                Write-Host "  Restored: $Folder" -ForegroundColor Gray
            }
        }

        Write-Host "Restore complete!" -ForegroundColor Green
    }
    finally {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function List-Backups {
    Write-Host "Available backups:" -ForegroundColor Cyan

    $Backups = Get-ChildItem $BackupDir -Filter "telegramhub_backup_*.zip" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending

    if ($Backups.Count -eq 0) {
        Write-Host "No backups found." -ForegroundColor Gray
        return
    }

    foreach ($Backup in $Backups) {
        $Size = [math]::Round($Backup.Length / 1MB, 2)
        Write-Host "  $($Backup.Name) - $Size MB - $($Backup.LastWriteTime)" -ForegroundColor Gray
    }
}

# Main
if ($List) {
    List-Backups
}
elseif ($Restore) {
    Restore-Backup -File $BackupFile
}
else {
    Create-Backup
}
