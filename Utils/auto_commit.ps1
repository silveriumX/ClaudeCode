# Автокоммит и пуш в GitHub

$RepoPath = "C:\Users\Admin\Documents\Cursor"
$CommitMessage = "Auto-backup $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

Set-Location $RepoPath

# Проверяем есть ли изменения
$status = git status --porcelain

if ($status) {
    Write-Host "Найдены изменения, сохраняем..." -ForegroundColor Yellow

    # Добавляем все файлы
    git add .

    # Коммитим
    git commit -m $CommitMessage

    # Пушим
    git push origin main

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Сохранено в GitHub: $(Get-Date)" -ForegroundColor Green
    } else {
        Write-Host "✗ Ошибка при пуше" -ForegroundColor Red
    }
} else {
    Write-Host "Нет изменений для сохранения" -ForegroundColor Gray
}
