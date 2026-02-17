# Автосинхронизация мыслей с сервера

## Параметры
$ServerIP = "195.177.94.189"
$ServerUser = "root"
$ServerPath = "~/thoughts/"
$LocalPath = "C:\Users\Admin\Documents\Cursor\Мысли\"

# Создаём папку если не существует
if (-not (Test-Path $LocalPath)) {
    New-Item -ItemType Directory -Path $LocalPath -Force
}

Write-Host "Синхронизация мыслей с сервера..."

# Копируем файлы
scp -r "${ServerUser}@${ServerIP}:${ServerPath}*" $LocalPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Синхронизация завершена: $(Get-Date)" -ForegroundColor Green
} else {
    Write-Host "✗ Ошибка синхронизации" -ForegroundColor Red
}
