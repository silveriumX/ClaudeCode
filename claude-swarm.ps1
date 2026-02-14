# Claude Code - SWARM MODE для PowerShell
# Запуск: .\claude-swarm.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Claude Code - SWARM MODE ACTIVATED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Установка переменной окружения
$env:NODE_OPTIONS = "--import $env:USERPROFILE\.claude\injectors\feature-flag-bypass-pure.mjs"

# Запуск Claude Code
Write-Host "Запуск Claude Code с Swarm режимом..." -ForegroundColor Yellow
Write-Host ""

# Передаем все аргументы в claude
& claude @args

# Для тихого режима (без логов) раскомментируйте:
# $env:BYPASS_SILENT = "1"
# $env:NODE_OPTIONS = "--import $env:USERPROFILE\.claude\injectors\feature-flag-bypass-pure.mjs"
# & claude @args
