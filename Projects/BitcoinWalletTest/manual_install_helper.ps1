# Простая установка Bitcoin Core 0.6.1
# Использует curl для скачивания и встроенные Windows инструменты

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Bitcoin Core 0.6.1 Simple Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Пути
$InstallDir = "C:\BitcoinCore-0.6.1"
$DataDir = "D:\BitcoinData06"
$BackupDir = "C:\BitcoinBackup"

# Прямая ссылка на старые билды (archive.org backup)
$DownloadUrl = "https://web.archive.org/web/20120515000000/http://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/bitcoin-0.6.1-win32.zip/download"

Write-Host "[INFO] This installer will guide you through manual download" -ForegroundColor Yellow
Write-Host ""
Write-Host "Please follow these steps:" -ForegroundColor White
Write-Host ""
Write-Host "1. Open this URL in your browser:" -ForegroundColor Yellow
Write-Host "   https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Download: bitcoin-0.6.1-win32.zip" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Save it to: C:\BitcoinTemp\bitcoin-0.6.1-win32.zip" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key when download is complete..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Создаём папку если нет
New-Item -ItemType Directory -Path "C:\BitcoinTemp" -Force | Out-Null

# Ждём файл
$ZipPath = "C:\BitcoinTemp\bitcoin-0.6.1-win32.zip"
Write-Host ""
Write-Host "Checking for file..." -ForegroundColor Yellow

$MaxWait = 300 # 5 минут
$Elapsed = 0

while (-not (Test-Path $ZipPath) -and ($Elapsed -lt $MaxWait)) {
    Start-Sleep -Seconds 5
    $Elapsed += 5
    Write-Host -NoNewline "`r  Waiting for file... ($Elapsed seconds)"
}

Write-Host ""

if (-not (Test-Path $ZipPath)) {
    Write-Host "[ERROR] File not found: $ZipPath" -ForegroundColor Red
    Write-Host "Please download manually and run this script again" -ForegroundColor Yellow
    pause
    exit 1
}

$FileSize = (Get-Item $ZipPath).Length / 1MB
Write-Host "[OK] Found: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Green

# Распаковка через PowerShell
Write-Host ""
Write-Host "Extracting..." -ForegroundColor Yellow

$ExtractPath = "C:\BitcoinTemp\extracted"

# Удаляем старую папку если есть
if (Test-Path $ExtractPath) {
    Remove-Item -Path $ExtractPath -Recurse -Force
}

# Пробуем распаковать
try {
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force
    Write-Host "[OK] Extracted" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Could not extract automatically" -ForegroundColor Red
    Write-Host "Please extract manually:" -ForegroundColor Yellow
    Write-Host "  1. Right-click on: $ZipPath" -ForegroundColor Cyan
    Write-Host "  2. Select 'Extract All...'" -ForegroundColor Cyan
    Write-Host "  3. Extract to: $ExtractPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press any key when extraction is done..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Поиск файлов
Write-Host ""
Write-Host "Searching for Bitcoin files..." -ForegroundColor Yellow

$Files = Get-ChildItem -Path $ExtractPath -Recurse -Include "bitcoin-qt.exe", "bitcoin-cli.exe" -ErrorAction SilentlyContinue

if ($Files.Count -eq 0) {
    Write-Host "[ERROR] Bitcoin files not found" -ForegroundColor Red
    Write-Host "Expected structure not found. Listing contents:" -ForegroundColor Yellow
    Get-ChildItem -Path $ExtractPath -Recurse | Select-Object -First 10 | Format-Table
    pause
    exit 1
}

# Установка
Write-Host "[OK] Found $($Files.Count) files" -ForegroundColor Green
Write-Host ""
Write-Host "Installing to $InstallDir..." -ForegroundColor Yellow

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

foreach ($File in $Files) {
    Copy-Item -Path $File.FullName -Destination $InstallDir -Force
    Write-Host "  Copied: $($File.Name)" -ForegroundColor Cyan
}

Write-Host "[OK] Installation complete" -ForegroundColor Green

# Создание папок
Write-Host ""
Write-Host "Creating directories..." -ForegroundColor Yellow

foreach ($Dir in @($DataDir, $BackupDir)) {
    if (-not (Test-Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force | Out-Null
    }
    Write-Host "  $Dir" -ForegroundColor Cyan
}

# Конфигурация
Write-Host ""
Write-Host "Creating config..." -ForegroundColor Yellow

$ConfigFile = "$DataDir\bitcoin.conf"
$Config = @"
server=1
rpcuser=testuser
rpcpassword=testpass123
rpcport=8332
listen=0
connect=0
"@

Set-Content -Path $ConfigFile -Value $Config -Encoding ASCII
Write-Host "[OK] Config created" -ForegroundColor Green

# Очистка
Remove-Item -Path "C:\BitcoinTemp" -Recurse -Force -ErrorAction SilentlyContinue

# Финал
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Paths:" -ForegroundColor White
Write-Host "  Program: $InstallDir" -ForegroundColor Cyan
Write-Host "  Data: $DataDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Bitcoin Core..." -ForegroundColor Yellow

cd $InstallDir
Start-Process -FilePath ".\bitcoin-qt.exe" -ArgumentList "-datadir=$DataDir"

Write-Host "[OK] Bitcoin Core started" -ForegroundColor Green
Write-Host ""
Write-Host "Waiting 30 seconds for wallet creation..." -ForegroundColor Cyan

for ($i = 30; $i -gt 0; $i--) {
    Write-Host -NoNewline "`r  $i seconds..."
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host ""

if (Test-Path "$DataDir\wallet.dat") {
    Write-Host "[SUCCESS] wallet.dat created!" -ForegroundColor Green
} else {
    Write-Host "[INFO] wallet.dat not ready yet" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Run 'check_wallet.ps1' to verify!" -ForegroundColor Cyan
