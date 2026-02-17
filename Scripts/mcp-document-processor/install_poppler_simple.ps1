# Установка Poppler для Windows
$ErrorActionPreference = "Stop"

Write-Host "=== Установка Poppler ===" -ForegroundColor Cyan

$tempDir = "$env:TEMP\poppler_install"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$downloadUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v25.12.0-0/Release-25.12.0-0.zip"
$zipPath = "$tempDir\poppler.zip"

Write-Host "Скачиваем..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing

Write-Host "Распаковываем..." -ForegroundColor Yellow
Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force

$installPath = "C:\Program Files\poppler"
if (Test-Path $installPath) {
    Remove-Item -Path $installPath -Recurse -Force
}

$popplerFolder = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like "poppler-*" } | Select-Object -First 1
Move-Item -Path $popplerFolder.FullName -Destination $installPath -Force

Write-Host "Добавляем в PATH..." -ForegroundColor Yellow
$binPath = "$installPath\Library\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")

if ($currentPath -notlike "*$binPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$binPath", "Machine")
}

$env:Path = "$env:Path;$binPath"

Remove-Item -Path $tempDir -Recurse -Force

Write-Host "Готово!" -ForegroundColor Green
