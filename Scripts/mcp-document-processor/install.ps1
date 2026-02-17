# Установка MCP Document Processor
# Этот скрипт установит все необходимые зависимости

Write-Host "=== Установка MCP Document Processor ===" -ForegroundColor Cyan
Write-Host ""

# Переходим в директорию сервера
$serverPath = "$PSScriptRoot\mcp-document-processor"
Set-Location $serverPath

Write-Host "1. Устанавливаем Python зависимости..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "2. Проверяем наличие Poppler (нужен для PDF)..." -ForegroundColor Yellow

# Проверяем наличие pdftoppm
$popplerInstalled = $null -ne (Get-Command pdftoppm -ErrorAction SilentlyContinue)

if ($popplerInstalled) {
    Write-Host "   ✓ Poppler уже установлен!" -ForegroundColor Green
} else {
    Write-Host "   ✗ Poppler не найден" -ForegroundColor Red
    Write-Host ""
    Write-Host "Poppler нужен для обработки PDF файлов." -ForegroundColor White
    Write-Host "Варианты установки:" -ForegroundColor White
    Write-Host ""
    Write-Host "1. Через Chocolatey (рекомендуется):" -ForegroundColor Cyan
    Write-Host "   choco install poppler" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Вручную:" -ForegroundColor Cyan
    Write-Host "   - Скачайте: https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Gray
    Write-Host "   - Распакуйте в C:\Program Files\poppler" -ForegroundColor Gray
    Write-Host "   - Добавьте в PATH: C:\Program Files\poppler\Library\bin" -ForegroundColor Gray
    Write-Host ""

    $choice = Read-Host "Установить через Chocolatey сейчас? (y/n)"
    if ($choice -eq 'y' -or $choice -eq 'Y') {
        Write-Host "   Устанавливаем Poppler..." -ForegroundColor Yellow
        choco install poppler -y

        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✓ Poppler установлен!" -ForegroundColor Green
        } else {
            Write-Host "   ✗ Ошибка установки. Попробуйте вручную." -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "3. Настраиваем API ключ..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Откройте файл:" -ForegroundColor White
Write-Host "   .cursor\mcp.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "И замените:" -ForegroundColor White
Write-Host '   "ANTHROPIC_API_KEY": "УКАЖИТЕ_ВАШ_API_КЛЮЧ_ЗДЕСЬ"' -ForegroundColor Gray
Write-Host ""
Write-Host "На ваш реальный API ключ от Anthropic" -ForegroundColor White
Write-Host ""

Write-Host "=== Установка завершена! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Что дальше:" -ForegroundColor White
Write-Host "1. Укажите API ключ в .cursor\mcp.json" -ForegroundColor Gray
Write-Host "2. Перезапустите Cursor (Ctrl+Shift+P -> Reload Window)" -ForegroundColor Gray
Write-Host "3. Попробуйте: 'Обработай файл C:\путь\к\файлу.pdf'" -ForegroundColor Gray
Write-Host ""

Read-Host "Нажмите Enter для выхода"
