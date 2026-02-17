# Check HUB traffic usage
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"
$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

# HUB packages
$packages = @(28045, 23330, 23362)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "HUB TRAFFIC USAGE CHECK" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($pkgId in $packages) {
    Write-Host "Package $pkgId`:" -ForegroundColor Yellow

    # Try different endpoints
    $endpoints = @(
        "https://api.proxyma.io/api/residential/$pkgId/usage",
        "https://api.proxyma.io/api/residential/packages/$pkgId/usage",
        "https://api.proxyma.io/api/residential/$pkgId/statistics",
        "https://api.proxyma.io/api/residential/packages/$pkgId/statistics",
        "https://api.proxyma.io/api/residential/packages/$pkgId"
    )

    $success = $false
    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-RestMethod -Uri $endpoint -Method Get -Headers $headers -TimeoutSec 10

            Write-Host "  SUCCESS: $endpoint" -ForegroundColor Green
            Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Gray
            $success = $true
            break

        } catch {
            # Continue to next endpoint
        }
    }

    if (-not $success) {
        Write-Host "  No usage data available" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
