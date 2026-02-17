# Установка Poppler для Windows
$ErrorActionPreference = "Stop"

Write-Host "=== Установка Poppler для Windows ===" -ForegroundColor Cyan
Write-Host ""

# Создаем временную директорию
$tempDir = "$env:TEMP\poppler_install"
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

try {
    # Скачиваем Poppler
    Write-Host "1. Скачиваем Poppler..." -ForegroundColor Yellow
    $downloadUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v25.12.0-0/Release-25.12.0-0.zip"
    $zipPath = "$tempDir\poppler.zip"

    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
    Write-Host "   ✓ Скачано" -ForegroundColor Green

    # Распаковываем
    Write-Host "2. Распаковываем..." -ForegroundColor Yellow
    Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force
    Write-Host "   ✓ Распаковано" -ForegroundColor Green

    # Устанавливаем в Program Files
    Write-Host "3. Устанавливаем в Program Files..." -ForegroundColor Yellow
    $installPath = "C:\Program Files\poppler"

    if (Test-Path $installPath) {
        Remove-Item -Path $installPath -Recurse -Force
    }

    $popplerFolder = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like "poppler-*" } | Select-Object -First 1
    Move-Item -Path $popplerFolder.FullName -Destination $installPath -Force
    Write-Host "   ✓ Установлено в $installPath" -ForegroundColor Green

    # Добавляем в PATH
    Write-Host "4. Добавляем в PATH..." -ForegroundColor Yellow
    $binPath = "$installPath\Library\bin"

    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")

    if ($currentPath -notlike "*$binPath*") {
        $newPath = $currentPath + ";" + $binPath
        [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
        $env:Path = $env:Path + ";" + $binPath
        Write-Host "   ✓ Добавлено в PATH" -ForegroundColor Green
    } else {
        Write-Host "   ✓ Уже в PATH" -ForegroundColor Green
    }

    # Проверяем установку
    Write-Host ""
    Write-Host "5. Проверяем установку..." -ForegroundColor Yellow
    $version = & "$binPath\pdftoppm.exe" -v 2>&1 | Select-Object -First 1
    Write-Host "   ✓ $version" -ForegroundColor Green

    Write-Host ""
    Write-Host "=== Установка завершена успешно! ===" -ForegroundColor Green

} catch {
    Write-Host ""
    Write-Host "✗ Ошибка: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Попробуйте установить вручную:" -ForegroundColor Yellow
    Write-Host "1. Скачайте: https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Gray
    Write-Host "2. Распакуйте в C:\Program Files\poppler" -ForegroundColor Gray
    Write-Host "3. Добавьте в PATH: C:\Program Files\poppler\Library\bin" -ForegroundColor Gray
} finally {
    # Очищаем временные файлы
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
