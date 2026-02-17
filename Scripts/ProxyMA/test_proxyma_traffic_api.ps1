# Test Proxyma API for traffic stats and purchase
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"  # HUB
$packageId = 28045  # Active HUB package

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TESTING PROXYMA API ENDPOINTS" -ForegroundColor Cyan
Write-Host "Package ID: $packageId" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test different endpoints for traffic statistics
$statsEndpoints = @(
    "https://api.proxyma.io/api/residential/packages/$packageId",
    "https://api.proxyma.io/api/residential/$packageId",
    "https://api.proxyma.io/api/residential/packages/$packageId/stats",
    "https://api.proxyma.io/api/residential/packages/$packageId/statistics",
    "https://api.proxyma.io/api/residential/$packageId/usage",
    "https://api.proxyma.io/api/residential/$packageId/traffic"
)

Write-Host "=== TESTING STATISTICS ENDPOINTS ===" -ForegroundColor Yellow
foreach ($endpoint in $statsEndpoints) {
    Write-Host "`nTrying: $endpoint" -ForegroundColor White
    try {
        $response = Invoke-RestMethod -Uri $endpoint -Method Get -Headers $headers -TimeoutSec 10
        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 5) -ForegroundColor Gray
        break
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "Failed: HTTP $statusCode" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host ""

# Test endpoints for buying traffic
$buyEndpoints = @(
    "https://api.proxyma.io/api/residential/packages/$packageId/buy-traffic",
    "https://api.proxyma.io/api/residential/$packageId/buy-traffic",
    "https://api.proxyma.io/api/residential/packages/$packageId/renew",
    "https://api.proxyma.io/api/residential/$packageId/renew",
    "https://api.proxyma.io/api/residential/buy-traffic",
    "https://api.proxyma.io/api/residential/packages/buy-traffic"
)

Write-Host "=== TESTING BUY TRAFFIC ENDPOINTS ===" -ForegroundColor Yellow
Write-Host "(Testing with GET first to check if endpoint exists)" -ForegroundColor Gray

foreach ($endpoint in $buyEndpoints) {
    Write-Host "`nTrying: $endpoint" -ForegroundColor White
    try {
        # First try GET to see if endpoint exists
        $response = Invoke-RestMethod -Uri $endpoint -Method Get -Headers $headers -TimeoutSec 10 -ErrorAction Stop
        Write-Host "GET SUCCESS (endpoint exists)!" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 3) -ForegroundColor Gray
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 405) {
            Write-Host "Method Not Allowed (405) - endpoint exists but needs POST!" -ForegroundColor Yellow
        } elseif ($statusCode -eq 404) {
            Write-Host "Not Found (404)" -ForegroundColor Red
        } else {
            Write-Host "HTTP $statusCode" -ForegroundColor Red
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
