# Скрипт для установки постоянного алиаса claude-swarm в PowerShell
# Запуск: .\install-swarm-alias.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Claude Swarm - Установка алиаса" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка профиля PowerShell
if (!(Test-Path -Path $PROFILE)) {
    Write-Host "Создание PowerShell профиля..." -ForegroundColor Yellow
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

# Функция для добавления в профиль
$functionText = @'

# Claude Code Swarm Mode
function claude-swarm {
    $env:NODE_OPTIONS = "--import $env:USERPROFILE\.claude\injectors\feature-flag-bypass-pure.mjs"
    claude $args
}

Write-Host "💡 Swarm режим доступен! Используйте: " -ForegroundColor Green -NoNewline
Write-Host "claude-swarm" -ForegroundColor Cyan
'@

# Проверка, не добавлена ли функция уже
$profileContent = Get-Content -Path $PROFILE -Raw -ErrorAction SilentlyContinue

if ($profileContent -notmatch "function claude-swarm") {
    Write-Host "Добавление функции claude-swarm в PowerShell профиль..." -ForegroundColor Yellow
    Add-Content -Path $PROFILE -Value $functionText
    Write-Host "✅ Функция успешно добавлена!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Функция claude-swarm уже существует в профиле" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Установка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Для применения изменений:" -ForegroundColor White
Write-Host "1. Закройте и откройте PowerShell заново" -ForegroundColor White
Write-Host "   ИЛИ" -ForegroundColor Yellow
Write-Host "2. Выполните: " -ForegroundColor White -NoNewline
Write-Host ". `$PROFILE" -ForegroundColor Cyan
Write-Host ""
Write-Host "После этого используйте: " -ForegroundColor White -NoNewline
Write-Host "claude-swarm" -ForegroundColor Green
Write-Host ""
