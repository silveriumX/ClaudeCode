# Улучшенная версия установщика с альтернативными методами

param(
    [string]$InstallDir = "C:\BitcoinCore-0.6.1",
    [string]$DataDir = "D:\BitcoinData06",
    [string]$BackupDir = "C:\BitcoinBackup"
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Bitcoin Core 0.6.1 Auto Installer v2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Конфигурация - используем прямую ссылку
$DownloadUrl = "https://bitcoin.org/bin/bitcoin-core-0.6.1/bitcoin-0.6.1-win32.zip"
$AlternativeUrl = "https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/bitcoin-0.6.1-win32.zip/download"
$TempDir = "C:\BitcoinTemp"
$ZipFile = "$TempDir\bitcoin-0.6.1-win32.zip"

# Шаг 1: Создание временной папки
Write-Host "[Step 1/8] Creating temporary directory..." -ForegroundColor Yellow
if (Test-Path $TempDir) {
    Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
Write-Host "[OK] Temp directory: $TempDir" -ForegroundColor Green

# Шаг 2: Скачивание
Write-Host ""
Write-Host "[Step 2/8] Downloading Bitcoin Core 0.6.1..." -ForegroundColor Yellow

$Downloaded = $false

# Попытка 1: основной URL
Write-Host "Trying: $DownloadUrl" -ForegroundColor Cyan
try {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipFile -UseBasicParsing -TimeoutSec 60

    if (Test-Path $ZipFile) {
        $FileSize = (Get-Item $ZipFile).Length / 1MB
        Write-Host "[OK] Downloaded: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Green
        $Downloaded = $true
    }
} catch {
    Write-Host "[FAILED] $($_.Exception.Message)" -ForegroundColor Yellow
}

# Попытка 2: альтернативный URL
if (-not $Downloaded) {
    Write-Host "Trying alternative: $AlternativeUrl" -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $AlternativeUrl -OutFile $ZipFile -UseBasicParsing -TimeoutSec 60

        if (Test-Path $ZipFile) {
            $FileSize = (Get-Item $ZipFile).Length / 1MB
            Write-Host "[OK] Downloaded: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Green
            $Downloaded = $true
        }
    } catch {
        Write-Host "[FAILED] $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if (-not $Downloaded) {
    Write-Host "[ERROR] Could not download Bitcoin Core" -ForegroundColor Red
    Write-Host "Please download manually and place in: $TempDir" -ForegroundColor Yellow
    Write-Host "Download from: https://bitcoin.org/en/download" -ForegroundColor Cyan
    pause
    exit 1
}

# Шаг 3: Распаковка
Write-Host ""
Write-Host "[Step 3/8] Extracting archive..." -ForegroundColor Yellow

try {
    # Метод 1: PowerShell Expand-Archive
    $ExtractPath = "$TempDir\extracted"

    # Создаём папку для распаковки
    if (Test-Path $ExtractPath) {
        Remove-Item -Path $ExtractPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ExtractPath -Force | Out-Null

    # Распаковываем
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipFile, $ExtractPath)

    Write-Host "[OK] Extracted to: $ExtractPath" -ForegroundColor Green

} catch {
    Write-Host "[ERROR] Extraction failed: $($_.Exception.Message)" -ForegroundColor Red

    # Пробуем альтернативный метод через tar (есть в Windows 10+)
    Write-Host "Trying alternative extraction method..." -ForegroundColor Yellow
    try {
        tar -xf $ZipFile -C $TempDir
        $ExtractPath = $TempDir
        Write-Host "[OK] Extracted via tar" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] All extraction methods failed" -ForegroundColor Red
        Write-Host "Please extract manually: $ZipFile" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Шаг 4: Поиск и копирование файлов
Write-Host ""
Write-Host "[Step 4/8] Installing to $InstallDir..." -ForegroundColor Yellow

# Создаём папку установки
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# Ищем исполняемые файлы рекурсивно
$Files = Get-ChildItem -Path $ExtractPath -Recurse -Include "bitcoin-qt.exe", "bitcoind.exe", "bitcoin-cli.exe" -ErrorAction SilentlyContinue

if ($Files.Count -eq 0) {
    Write-Host "[WARNING] Executable files not found in standard location" -ForegroundColor Yellow
    Write-Host "Searching in: $TempDir" -ForegroundColor Cyan
    $Files = Get-ChildItem -Path $TempDir -Recurse -Include "bitcoin-qt.exe", "bitcoind.exe", "bitcoin-cli.exe" -ErrorAction SilentlyContinue
}

if ($Files.Count -gt 0) {
    foreach ($File in $Files) {
        Copy-Item -Path $File.FullName -Destination $InstallDir -Force
        Write-Host "  Copied: $($File.Name)" -ForegroundColor Cyan
    }
    Write-Host "[OK] Installed $($Files.Count) files" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Bitcoin executables not found" -ForegroundColor Red
    Write-Host "Archive structure:" -ForegroundColor Yellow
    Get-ChildItem -Path $TempDir -Recurse | Select-Object -First 20 | Format-Table Name, FullName
    pause
    exit 1
}

# Шаг 5: Проверка
Write-Host ""
Write-Host "[Step 5/8] Verifying installation..." -ForegroundColor Yellow

$BitcoinQT = Join-Path $InstallDir "bitcoin-qt.exe"
$BitcoinCLI = Join-Path $InstallDir "bitcoin-cli.exe"

if ((Test-Path $BitcoinQT) -and (Test-Path $BitcoinCLI)) {
    Write-Host "[OK] bitcoin-qt.exe - Found" -ForegroundColor Green
    Write-Host "[OK] bitcoin-cli.exe - Found" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Required files missing" -ForegroundColor Red
    exit 1
}

# Шаг 6: Создание папок
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

# Шаг 7: Конфигурация
Write-Host ""
Write-Host "[Step 7/8] Creating bitcoin.conf..." -ForegroundColor Yellow

$ConfigFile = Join-Path $DataDir "bitcoin.conf"
$ConfigContent = @"
# Bitcoin Core 0.6.1 Configuration
server=1
rpcuser=testuser
rpcpassword=testpass123
rpcport=8332
listen=0
connect=0
"@

Set-Content -Path $ConfigFile -Value $ConfigContent -Encoding ASCII
Write-Host "[OK] Config: $ConfigFile" -ForegroundColor Green

# Шаг 8: Очистка
Write-Host ""
Write-Host "[Step 8/8] Cleaning up..." -ForegroundColor Yellow
Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Cleanup complete" -ForegroundColor Green

# Финал
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installation paths:" -ForegroundColor White
Write-Host "  Bitcoin Core: $InstallDir" -ForegroundColor Cyan
Write-Host "  Data: $DataDir" -ForegroundColor Cyan
Write-Host "  Backup: $BackupDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Bitcoin Core in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Запуск
$Process = Start-Process -FilePath $BitcoinQT -ArgumentList "-datadir=$DataDir" -PassThru
Write-Host "[OK] Bitcoin Core started (PID: $($Process.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "Waiting 30 seconds for wallet creation..." -ForegroundColor Cyan

for ($i = 30; $i -gt 0; $i--) {
    Write-Host -NoNewline "`r  $i seconds remaining..."
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host ""

# Проверка wallet.dat
$WalletPath = Join-Path $DataDir "wallet.dat"
if (Test-Path $WalletPath) {
    $WalletSize = (Get-Item $WalletPath).Length
    Write-Host "[SUCCESS] wallet.dat created! ($WalletSize bytes)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: Run check_wallet.ps1 to verify walletversion 60000" -ForegroundColor Cyan
} else {
    Write-Host "[INFO] wallet.dat not yet visible, may need more time" -ForegroundColor Yellow
    Write-Host "Check manually: $WalletPath" -ForegroundColor Cyan
}

Write-Host ""
