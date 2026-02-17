# Скрипт для быстрой проверки состояния кошелька

$BitcoinDir = "C:\BitcoinCore-0.6.1"
$DataDir = "D:\BitcoinData06"
$RPCUser = "testuser"
$RPCPass = "testpass123"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Bitcoin Wallet Status Checker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка wallet.dat
Write-Host "[CHECK 1] Wallet file..." -ForegroundColor Yellow
$WalletPath = "$DataDir\wallet.dat"

if (Test-Path $WalletPath) {
    $WalletSize = (Get-Item $WalletPath).Length
    $WalletModified = (Get-Item $WalletPath).LastWriteTime
    Write-Host "[OK] wallet.dat exists" -ForegroundColor Green
    Write-Host "     Size: $WalletSize bytes" -ForegroundColor Cyan
    Write-Host "     Last modified: $WalletModified" -ForegroundColor Cyan
} else {
    Write-Host "[ERROR] wallet.dat not found at: $WalletPath" -ForegroundColor Red
    exit
}

# Проверка процесса Bitcoin Core
Write-Host ""
Write-Host "[CHECK 2] Bitcoin Core process..." -ForegroundColor Yellow
$Process = Get-Process -Name "bitcoin-qt" -ErrorAction SilentlyContinue

if ($Process) {
    Write-Host "[OK] Bitcoin Core is running (PID: $($Process.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Bitcoin Core not running" -ForegroundColor Yellow
    Write-Host "Start it with: .\bitcoin-qt.exe -datadir=$DataDir" -ForegroundColor Cyan
    exit
}

# Проверка RPC
Write-Host ""
Write-Host "[CHECK 3] RPC connection..." -ForegroundColor Yellow

cd $BitcoinDir

$Command = ".\bitcoin-cli.exe -datadir=$DataDir -rpcuser=$RPCUser -rpcpassword=$RPCPass getinfo"

try {
    $Result = Invoke-Expression $Command 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] RPC connection successful" -ForegroundColor Green
        Write-Host ""
        Write-Host "Wallet Info:" -ForegroundColor Cyan
        Write-Host $Result

        # Извлечь walletversion
        if ($Result -match '"walletversion"\s*:\s*(\d+)') {
            $WalletVersion = $matches[1]
            Write-Host ""
            if ($WalletVersion -eq "60000") {
                Write-Host "[SUCCESS] Wallet version is 60000!" -ForegroundColor Green
            } else {
                Write-Host "[INFO] Wallet version: $WalletVersion" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "[ERROR] RPC connection failed" -ForegroundColor Red
        Write-Host $Result
    }
} catch {
    Write-Host "[ERROR] Failed to execute bitcoin-cli" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
