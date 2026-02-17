# Пошаговый помощник установки Bitcoin Core 0.6.1
# Проверяет каждый шаг и помогает пройти процесс

$InstallDir = "C:\BitcoinCore-0.6.1"
$DataDir = "D:\BitcoinData06"
$BackupDir = "C:\BitcoinBackup"
$ConfigFile = "$DataDir\bitcoin.conf"
$WalletFile = "$DataDir\wallet.dat"

function Show-Step {
    param($Number, $Title, $Status = "PENDING")

    $Color = switch ($Status) {
        "OK" { "Green" }
        "ERROR" { "Red" }
        "PENDING" { "Yellow" }
        default { "White" }
    }

    $Symbol = switch ($Status) {
        "OK" { "[OK]" }
        "ERROR" { "[X]" }
        "PENDING" { "[ ]" }
        default { "[ ]" }
    }

    Write-Host "$Symbol Step $Number`: $Title" -ForegroundColor $Color
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Bitcoin Core 0.6.1 Installation Helper" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Проверка скачанного файла
Show-Step 1 "Download bitcoin-0.6.1-win32.zip" "PENDING"
Write-Host ""
Write-Host "Please download from:" -ForegroundColor White
Write-Host "https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Save to your Downloads folder" -ForegroundColor White
Write-Host ""
Write-Host "Press any key when downloaded..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Поиск файла
$PossibleLocations = @(
    "$env:USERPROFILE\Downloads\bitcoin-0.6.1-win32.zip",
    "C:\Downloads\bitcoin-0.6.1-win32.zip",
    "D:\Downloads\bitcoin-0.6.1-win32.zip"
)

$ZipPath = $null
foreach ($Path in $PossibleLocations) {
    if (Test-Path $Path) {
        $ZipPath = $Path
        break
    }
}

if ($ZipPath) {
    Show-Step 1 "Download bitcoin-0.6.1-win32.zip" "OK"
    Write-Host "  Found at: $ZipPath" -ForegroundColor Cyan
} else {
    Show-Step 1 "Download bitcoin-0.6.1-win32.zip" "ERROR"
    Write-Host "  File not found. Please specify path:" -ForegroundColor Yellow
    $ZipPath = Read-Host "  Full path to bitcoin-0.6.1-win32.zip"

    if (-not (Test-Path $ZipPath)) {
        Write-Host "[ERROR] File not found. Exiting." -ForegroundColor Red
        pause
        exit 1
    }
}

Write-Host ""

# Шаг 2: Распаковка
Show-Step 2 "Extract files to $InstallDir" "PENDING"
Write-Host ""
Write-Host "Extracting..." -ForegroundColor Cyan

if (Test-Path $InstallDir) {
    Write-Host "  Directory exists, cleaning..." -ForegroundColor Yellow
    Remove-Item -Path "$InstallDir\*" -Force -Recurse -ErrorAction SilentlyContinue
} else {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

try {
    Expand-Archive -Path $ZipPath -DestinationPath $InstallDir -Force

    # Проверка структуры
    $ExeFiles = Get-ChildItem -Path $InstallDir -Filter "bitcoin-qt.exe" -Recurse

    if ($ExeFiles.Count -gt 0) {
        $BitcoinDir = $ExeFiles[0].DirectoryName

        if ($BitcoinDir -ne $InstallDir) {
            Write-Host "  Moving files from subfolder..." -ForegroundColor Cyan
            Get-ChildItem -Path $BitcoinDir | Move-Item -Destination $InstallDir -Force
        }

        Show-Step 2 "Extract files" "OK"
    } else {
        Show-Step 2 "Extract files" "ERROR"
        Write-Host "  bitcoin-qt.exe not found" -ForegroundColor Red
        pause
        exit 1
    }
} catch {
    Show-Step 2 "Extract files" "ERROR"
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please extract manually:" -ForegroundColor Yellow
    Write-Host "  1. Right-click: $ZipPath" -ForegroundColor Cyan
    Write-Host "  2. Extract to: $InstallDir" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press any key when done..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

Write-Host ""

# Шаг 3: Проверка файлов
Show-Step 3 "Verify files" "PENDING"

$RequiredFiles = @("bitcoin-qt.exe", "bitcoin-cli.exe")
$AllFound = $true

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $InstallDir $File
    if (Test-Path $Path) {
        Write-Host "  [OK] $File" -ForegroundColor Green
    } else {
        Write-Host "  [X] $File NOT FOUND" -ForegroundColor Red
        $AllFound = $false
    }
}

if ($AllFound) {
    Show-Step 3 "Verify files" "OK"
} else {
    Show-Step 3 "Verify files" "ERROR"
    pause
    exit 1
}

Write-Host ""

# Шаг 4: Создание папок
Show-Step 4 "Create directories" "PENDING"

foreach ($Dir in @($DataDir, $BackupDir)) {
    if (-not (Test-Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force | Out-Null
        Write-Host "  Created: $Dir" -ForegroundColor Cyan
    } else {
        Write-Host "  Exists: $Dir" -ForegroundColor Cyan
    }
}

Show-Step 4 "Create directories" "OK"
Write-Host ""

# Шаг 5: Создание конфигурации
Show-Step 5 "Create bitcoin.conf" "PENDING"

$Config = @"
server=1
rpcuser=testuser
rpcpassword=testpass123
rpcport=8332
listen=0
connect=0
"@

Set-Content -Path $ConfigFile -Value $Config -Encoding ASCII
Show-Step 5 "Create bitcoin.conf" "OK"
Write-Host ""

# Шаг 6: Запуск Bitcoin Core
Show-Step 6 "Start Bitcoin Core" "PENDING"
Write-Host ""
Write-Host "Starting Bitcoin Core..." -ForegroundColor Cyan
Write-Host "(A window will open - don't close it!)" -ForegroundColor Yellow
Write-Host ""

$BitcoinQT = Join-Path $InstallDir "bitcoin-qt.exe"
$Process = Start-Process -FilePath $BitcoinQT -ArgumentList "-datadir=$DataDir" -PassThru

Start-Sleep -Seconds 3

if ($Process.HasExited) {
    Show-Step 6 "Start Bitcoin Core" "ERROR"
    Write-Host "  Process exited immediately" -ForegroundColor Red
    pause
    exit 1
} else {
    Show-Step 6 "Start Bitcoin Core" "OK"
    Write-Host "  PID: $($Process.Id)" -ForegroundColor Cyan
}

Write-Host ""

# Шаг 7: Ожидание создания wallet.dat
Show-Step 7 "Wait for wallet.dat creation" "PENDING"
Write-Host ""
Write-Host "Waiting for wallet file (max 60 seconds)..." -ForegroundColor Cyan

$MaxWait = 60
$Elapsed = 0

while (-not (Test-Path $WalletFile) -and ($Elapsed -lt $MaxWait)) {
    Write-Host -NoNewline "`r  Elapsed: $Elapsed seconds..."
    Start-Sleep -Seconds 2
    $Elapsed += 2
}

Write-Host ""

if (Test-Path $WalletFile) {
    $Size = (Get-Item $WalletFile).Length
    Show-Step 7 "wallet.dat created" "OK"
    Write-Host "  Size: $Size bytes" -ForegroundColor Cyan
} else {
    Show-Step 7 "wallet.dat creation" "ERROR"
    Write-Host "  File not created yet, may need more time" -ForegroundColor Yellow
}

Write-Host ""

# Шаг 8: Проверка версии
Show-Step 8 "Check wallet version" "PENDING"
Write-Host ""
Write-Host "Waiting for RPC server (15 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

$BitcoinCLI = Join-Path $InstallDir "bitcoin-cli.exe"
$CLIArgs = @("-datadir=$DataDir", "-rpcuser=testuser", "-rpcpassword=testpass123", "getinfo")

try {
    $Output = & $BitcoinCLI $CLIArgs 2>&1 | Out-String

    if ($Output -match '"walletversion"\s*:\s*(\d+)') {
        $Version = $matches[1]

        if ($Version -eq "60000") {
            Show-Step 8 "Check wallet version" "OK"
            Write-Host "  Wallet version: $Version (CORRECT!)" -ForegroundColor Green
        } else {
            Show-Step 8 "Check wallet version" "OK"
            Write-Host "  Wallet version: $Version (Expected 60000)" -ForegroundColor Yellow
        }
    } else {
        Show-Step 8 "Check wallet version" "ERROR"
        Write-Host "  Could not parse version" -ForegroundColor Yellow
        Write-Host "  Output: $Output" -ForegroundColor Gray
    }
} catch {
    Show-Step 8 "Check wallet version" "ERROR"
    Write-Host "  RPC not ready yet" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Helper Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "1. Check version manually:" -ForegroundColor Yellow
Write-Host "   cd $InstallDir" -ForegroundColor Cyan
Write-Host "   .\bitcoin-cli.exe -datadir=$DataDir -rpcuser=testuser -rpcpassword=testpass123 getinfo" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Encrypt wallet:" -ForegroundColor Yellow
Write-Host "   .\bitcoin-cli.exe -datadir=$DataDir -rpcuser=testuser -rpcpassword=testpass123 encryptwallet `"YourPassword123!`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Make backup:" -ForegroundColor Yellow
Write-Host "   copy $WalletFile $BackupDir\wallet_backup.dat" -ForegroundColor Cyan
Write-Host ""
Write-Host "Full guide: SIMPLE_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
pause
