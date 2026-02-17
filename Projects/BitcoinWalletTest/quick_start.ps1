# Quick Start Script для Bitcoin Core 0.6.1
# Автоматизирует первоначальную настройку

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Bitcoin Core 0.6.1 Quick Start Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Конфигурация
$BitcoinDir = "C:\BitcoinCore-0.6.1"
$DataDir = "D:\BitcoinData06"
$BackupDir = "C:\BitcoinBackup"
$ConfigFile = "$DataDir\bitcoin.conf"

# Шаг 1: Проверка установки
Write-Host "[Step 1] Checking Bitcoin Core installation..." -ForegroundColor Yellow

if (-not (Test-Path "$BitcoinDir\bitcoin-qt.exe")) {
    Write-Host "[ERROR] bitcoin-qt.exe not found in $BitcoinDir" -ForegroundColor Red
    Write-Host "Please install Bitcoin Core 0.6.1 first!" -ForegroundColor Red
    Write-Host "Download from: https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/" -ForegroundColor Yellow
    pause
    exit
}

Write-Host "[OK] Bitcoin Core found at: $BitcoinDir" -ForegroundColor Green

# Шаг 2: Создание datadir
Write-Host ""
Write-Host "[Step 2] Creating data directory..." -ForegroundColor Yellow

if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    Write-Host "[OK] Created: $DataDir" -ForegroundColor Green
} else {
    Write-Host "[OK] Data directory already exists: $DataDir" -ForegroundColor Green
}

# Шаг 3: Создание bitcoin.conf
Write-Host ""
Write-Host "[Step 3] Creating bitcoin.conf..." -ForegroundColor Yellow

$ConfigContent = @"
# Bitcoin Core 0.6.1 Configuration
# RPC Settings

server=1
rpcuser=testuser
rpcpassword=testpass123
rpcport=8332

# Network
listen=0
# Не подключаться к сети (для быстрого теста)
connect=0
"@

Set-Content -Path $ConfigFile -Value $ConfigContent -Encoding UTF8
Write-Host "[OK] Config created: $ConfigFile" -ForegroundColor Green

# Шаг 4: Создание папки для бэкапа
Write-Host ""
Write-Host "[Step 4] Creating backup directory..." -ForegroundColor Yellow

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Host "[OK] Created: $BackupDir" -ForegroundColor Green
} else {
    Write-Host "[OK] Backup directory already exists: $BackupDir" -ForegroundColor Green
}

# Шаг 5: Запуск Bitcoin Core
Write-Host ""
Write-Host "[Step 5] Starting Bitcoin Core..." -ForegroundColor Yellow
Write-Host "This will open Bitcoin-Qt window..." -ForegroundColor Cyan

$BitcoinProcess = Start-Process -FilePath "$BitcoinDir\bitcoin-qt.exe" -ArgumentList "-datadir=$DataDir" -PassThru

Write-Host "[OK] Bitcoin Core started (PID: $($BitcoinProcess.Id))" -ForegroundColor Green
Write-Host "Waiting for wallet creation (30 seconds)..." -ForegroundColor Cyan

Start-Sleep -Seconds 30

# Шаг 6: Проверка wallet.dat
Write-Host ""
Write-Host "[Step 6] Checking wallet.dat..." -ForegroundColor Yellow

$WalletPath = "$DataDir\wallet.dat"
if (Test-Path $WalletPath) {
    Write-Host "[OK] wallet.dat created!" -ForegroundColor Green
    $WalletSize = (Get-Item $WalletPath).Length
    Write-Host "Wallet file size: $WalletSize bytes" -ForegroundColor Cyan
} else {
    Write-Host "[WARNING] wallet.dat not found yet. May need more time..." -ForegroundColor Yellow
}

# Шаг 7: Инструкции для проверки
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete! Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Wait for RPC server to start (10-15 seconds)" -ForegroundColor White
Write-Host ""
Write-Host "2. Check wallet version:" -ForegroundColor White
Write-Host "   cd $BitcoinDir" -ForegroundColor Yellow
Write-Host "   .\bitcoin-cli.exe -datadir=$DataDir -rpcuser=testuser -rpcpassword=testpass123 getinfo" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Look for 'walletversion: 60000' in output" -ForegroundColor White
Write-Host ""
Write-Host "4. To encrypt wallet:" -ForegroundColor White
Write-Host "   .\bitcoin-cli.exe -datadir=$DataDir -rpcuser=testuser -rpcpassword=testpass123 encryptwallet `"YourPassword123!`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "5. After encryption, Bitcoin Core will close. Restart it:" -ForegroundColor White
Write-Host "   .\bitcoin-qt.exe -datadir=$DataDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "6. To unlock wallet:" -ForegroundColor White
Write-Host "   .\bitcoin-cli.exe -datadir=$DataDir -rpcuser=testuser -rpcpassword=testpass123 walletpassphrase `"YourPassword123!`" 60" -ForegroundColor Yellow
Write-Host ""
Write-Host "7. To generate address:" -ForegroundColor White
Write-Host "   .\bitcoin-cli.exe -datadir=$DataDir -rpcuser=testuser -rpcpassword=testpass123 getnewaddress" -ForegroundColor Yellow
Write-Host ""
Write-Host "Backup location: $BackupDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
pause
