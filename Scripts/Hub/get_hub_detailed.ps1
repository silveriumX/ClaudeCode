# Get detailed package info for HUB
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"
$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "HUB DETAILED PACKAGE INFO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get all packages
$response = Invoke-RestMethod -Uri "https://api.proxyma.io/api/residential/packages" `
    -Method Get `
    -Headers $headers `
    -TimeoutSec 30

Write-Host "Total packages: $($response.packages.Count)" -ForegroundColor Yellow
Write-Host ""

foreach ($pkg in $response.packages) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Package ID: $($pkg.id) - $($pkg.tariff.title)" -ForegroundColor Yellow
    Write-Host "Status: $($pkg.status)" -ForegroundColor $(if ($pkg.status -eq "active") { "Green" } else { "Red" })
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "FULL PACKAGE DATA:" -ForegroundColor White
    Write-Host ($pkg | ConvertTo-Json -Depth 10) -ForegroundColor Gray
    Write-Host ""
}
