# Comprehensive test for traffic statistics API
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"  # HUB
$packageId = 28045
$packageKey = "1fb08611c4d557ac8f22"

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SEARCHING FOR TRAFFIC STATISTICS API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try every possible combination
$endpoints = @(
    # By package ID
    "https://api.proxyma.io/api/residential/packages/$packageId/stats",
    "https://api.proxyma.io/api/residential/packages/$packageId/stat",
    "https://api.proxyma.io/api/residential/packages/$packageId/traffic",
    "https://api.proxyma.io/api/residential/packages/$packageId/usage",
    "https://api.proxyma.io/api/residential/packages/$packageId/statistics",

    # By package key
    "https://api.proxyma.io/api/residential/packages/$packageKey/stats",
    "https://api.proxyma.io/api/residential/packages/$packageKey/traffic",

    # Direct package info
    "https://api.proxyma.io/api/residential/packages/$packageId",
    "https://api.proxyma.io/api/residential/packages/$packageId/info",
    "https://api.proxyma.io/api/residential/packages/$packageId/details",

    # General stats
    "https://api.proxyma.io/api/residential/stats",
    "https://api.proxyma.io/api/residential/statistics",
    "https://api.proxyma.io/api/residential/usage",
    "https://api.proxyma.io/api/residential/traffic",

    # Profile stats
    "https://api.proxyma.io/api/profile/stats",
    "https://api.proxyma.io/api/profile/statistics",
    "https://api.proxyma.io/api/profile/usage",
    "https://api.proxyma.io/api/profile/packages",

    # Dashboard
    "https://api.proxyma.io/api/dashboard",
    "https://api.proxyma.io/api/dashboard/stats"
)

foreach ($endpoint in $endpoints) {
    Write-Host "Testing: $endpoint" -ForegroundColor Yellow

    try {
        $response = Invoke-RestMethod -Uri $endpoint -Method Get -Headers $headers -TimeoutSec 10
        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Gray
        Write-Host ""
        Write-Host "FOUND WORKING ENDPOINT: $endpoint" -ForegroundColor Green
        Write-Host ""
        break

    } catch {
        $code = $_.Exception.Response.StatusCode.value__

        if ($code -eq 405) {
            Write-Host "  -> 405 (Method Not Allowed - try POST?)" -ForegroundColor Yellow
        } elseif ($code -eq 401) {
            Write-Host "  -> 401 (Auth error)" -ForegroundColor Magenta
        } elseif ($code -eq 404) {
            Write-Host "  -> 404 (Not Found)" -ForegroundColor DarkGray
        } else {
            Write-Host "  -> HTTP $code" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
