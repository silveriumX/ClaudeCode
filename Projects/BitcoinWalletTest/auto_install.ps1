# Автоматическая установка Bitcoin Core 0.6.1 с нуля
# Скачивает, устанавливает, настраивает и создаёт кошелёк

param(
    [string]$InstallDir = "C:\BitcoinCore-0.6.1",
    [string]$DataDir = "D:\BitcoinData06",
    [string]$BackupDir = "C:\BitcoinBackup"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Bitcoin Core 0.6.1 Auto Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Конфигурация
$DownloadUrl = "https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/bitcoin-0.6.1-win32.zip/download"
$TempDir = "$env:TEMP\BitcoinInstall"
$ZipFile = "$TempDir\bitcoin-0.6.1-win32.zip"

# Шаг 1: Создание временной папки
Write-Host "[Step 1/8] Creating temporary directory..." -ForegroundColor Yellow
if (-not (Test-Path $TempDir)) {
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
}
Write-Host "[OK] Temp directory: $TempDir" -ForegroundColor Green

# Шаг 2: Скачивание Bitcoin Core 0.6.1
Write-Host ""
Write-Host "[Step 2/8] Downloading Bitcoin Core 0.6.1..." -ForegroundColor Yellow
Write-Host "URL: $DownloadUrl" -ForegroundColor Cyan
Write-Host "This may take a few minutes..." -ForegroundColor Cyan

try {
    # Используем Invoke-WebRequest для скачивания
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipFile -UseBasicParsing

    if (Test-Path $ZipFile) {
        $FileSize = (Get-Item $ZipFile).Length / 1MB
        Write-Host "[OK] Downloaded: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Green
    } else {
        throw "Download failed - file not found"
    }
} catch {
    Write-Host "[ERROR] Failed to download: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Trying alternative method..." -ForegroundColor Yellow

    # Альтернативный метод через curl (если есть)
    try {
        curl.exe -L -o $ZipFile $DownloadUrl
        if (Test-Path $ZipFile) {
            Write-Host "[OK] Downloaded via curl" -ForegroundColor Green
        }
    } catch {
        Write-Host "[ERROR] All download methods failed" -ForegroundColor Red
        Write-Host "Please download manually from:" -ForegroundColor Yellow
        Write-Host "https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/" -ForegroundColor Cyan
        exit 1
    }
}

# Шаг 3: Распаковка архива
Write-Host ""
Write-Host "[Step 3/8] Extracting archive..." -ForegroundColor Yellow

try {
    Expand-Archive -Path $ZipFile -DestinationPath $TempDir -Force

    # Найти папку с файлами
    $ExtractedFolder = Get-ChildItem -Path $TempDir -Directory | Where-Object { $_.Name -like "bitcoin-*" } | Select-Object -First 1

    if ($ExtractedFolder) {
        Write-Host "[OK] Extracted to: $($ExtractedFolder.FullName)" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Expected folder structure not found, checking root..." -ForegroundColor Yellow
        $ExtractedFolder = Get-Item $TempDir
    }
} catch {
    Write-Host "[ERROR] Failed to extract: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Шаг 4: Установка (копирование файлов)
Write-Host ""
Write-Host "[Step 4/8] Installing to $InstallDir..." -ForegroundColor Yellow

try {
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    # Ищем исполняемые файлы
    $Files = Get-ChildItem -Path $ExtractedFolder.FullName -Recurse -Include "bitcoin-qt.exe", "bitcoind.exe", "bitcoin-cli.exe"

    if ($Files.Count -eq 0) {
        # Пробуем искать в подпапках
        $Files = Get-ChildItem -Path $TempDir -Recurse -Include "bitcoin-qt.exe", "bitcoind.exe", "bitcoin-cli.exe"
    }

    if ($Files.Count -gt 0) {
        foreach ($File in $Files) {
            Copy-Item -Path $File.FullName -Destination $InstallDir -Force
            Write-Host "  Copied: $($File.Name)" -ForegroundColor Cyan
        }
        Write-Host "[OK] Installed successfully" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Bitcoin executables not found in archive" -ForegroundColor Red
        Write-Host "Archive contents:" -ForegroundColor Yellow
        Get-ChildItem -Path $TempDir -Recurse | Select-Object FullName | Format-Table
        exit 1
    }
} catch {
    Write-Host "[ERROR] Installation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Шаг 5: Проверка установки
Write-Host ""
Write-Host "[Step 5/8] Verifying installation..." -ForegroundColor Yellow

$RequiredFiles = @("bitcoin-qt.exe", "bitcoin-cli.exe")
$AllFound = $true

foreach ($File in $RequiredFiles) {
    $FilePath = Join-Path $InstallDir $File
    if (Test-Path $FilePath) {
        Write-Host "  [OK] $File" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] $File not found" -ForegroundColor Red
        $AllFound = $false
    }
}

if (-not $AllFound) {
    Write-Host "[ERROR] Installation incomplete" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] All files verified" -ForegroundColor Green

# Шаг 6: Создание папок для данных
Write-Host ""
Write-Host "[Step 6/8] Creating data directories..." -ForegroundColor Yellow

foreach ($Dir in @($DataDir, $BackupDir)) {
    if (-not (Test-Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force | Out-Null
        Write-Host "  Created: $Dir" -ForegroundColor Cyan
    } else {
        Write-Host "  Exists: $Dir" -ForegroundColor Cyan
    }
}

Write-Host "[OK] Directories ready" -ForegroundColor Green

# Шаг 7: Создание конфигурации
Write-Host ""
Write-Host "[Step 7/8] Creating bitcoin.conf..." -ForegroundColor Yellow

$ConfigFile = Join-Path $DataDir "bitcoin.conf"
$ConfigContent = @"
# Bitcoin Core 0.6.1 Configuration
# Auto-generated by installer

# RPC Settings
server=1
rpcuser=testuser
rpcpassword=testpass123
rpcport=8332

# Network settings
# Не подключаться к сети для быстрого теста
listen=0
connect=0

# Logging
debug=1
"@

Set-Content -Path $ConfigFile -Value $ConfigContent -Encoding UTF8
Write-Host "[OK] Config created: $ConfigFile" -ForegroundColor Green

# Шаг 8: Очистка временных файлов
Write-Host ""
Write-Host "[Step 8/8] Cleaning up..." -ForegroundColor Yellow

try {
    Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Temporary files cleaned" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Could not clean temp files: $TempDir" -ForegroundColor Yellow
}

# Финал
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation Summary:" -ForegroundColor White
Write-Host "  Bitcoin Core: $InstallDir" -ForegroundColor Cyan
Write-Host "  Data directory: $DataDir" -ForegroundColor Cyan
Write-Host "  Backup directory: $BackupDir" -ForegroundColor Cyan
Write-Host "  Config file: $ConfigFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "1. Start Bitcoin Core:" -ForegroundColor Yellow
Write-Host "   cd $InstallDir" -ForegroundColor Cyan
Write-Host "   .\bitcoin-qt.exe -datadir=$DataDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Wait 30 seconds for wallet creation" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Check wallet version:" -ForegroundColor Yellow
Write-Host "   .\bitcoin-cli.exe -datadir=$DataDir -rpcuser=testuser -rpcpassword=testpass123 getinfo" -ForegroundColor Cyan
Write-Host ""
Write-Host "Or run the quick check script:" -ForegroundColor Yellow
Write-Host "   powershell -ExecutionPolicy Bypass -File check_wallet.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to start Bitcoin Core now..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Запуск Bitcoin Core
Write-Host ""
Write-Host "Starting Bitcoin Core..." -ForegroundColor Yellow

$BitcoinQT = Join-Path $InstallDir "bitcoin-qt.exe"
$Process = Start-Process -FilePath $BitcoinQT -ArgumentList "-datadir=$DataDir" -PassThru

Write-Host "[OK] Bitcoin Core started (PID: $($Process.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "Waiting 30 seconds for wallet creation..." -ForegroundColor Cyan

Start-Sleep -Seconds 30

# Проверка wallet.dat
$WalletPath = Join-Path $DataDir "wallet.dat"
if (Test-Path $WalletPath) {
    $WalletSize = (Get-Item $WalletPath).Length
    Write-Host "[SUCCESS] wallet.dat created! ($WalletSize bytes)" -ForegroundColor Green
} else {
    Write-Host "[INFO] wallet.dat not yet created, may need more time..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Run 'check_wallet.ps1' to verify the installation!" -ForegroundColor Cyan
