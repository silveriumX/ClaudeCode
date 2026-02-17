# Systematic search for working package info endpoint
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"  # HUB
$packageKey = "1fb08611c4d557ac8f22"  # HUB active package key
$packageId = 28045  # HUB active package ID

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SYSTEMATIC ENDPOINT SEARCH" -ForegroundColor Cyan
Write-Host "Package Key: $packageKey" -ForegroundColor Yellow
Write-Host "Package ID: $packageId" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# All possible combinations
$baseUrls = @(
    "https://proxyma.io",
    "https://api.proxyma.io",
    "https://cabinet.proxyma.io"
)

$paths = @(
    "/reseller/info/package",
    "/api/reseller/info/package",
    "/reseller/package",
    "/api/reseller/package",
    "/api/residential/package",
    "/api/residential/packages",
    "/api/residential/info/package",
    "/api/package",
    "/api/packages"
)

$identifiers = @(
    $packageKey,
    $packageId
)

$tested = @{}
$foundEndpoint = $null

foreach ($base in $baseUrls) {
    foreach ($path in $paths) {
        foreach ($id in $identifiers) {
            $url = "$base$path/$id"

            # Skip if already tested
            if ($tested.ContainsKey($url)) { continue }
            $tested[$url] = $true

            Write-Host "Testing: $url" -ForegroundColor Gray

            try {
                $response = Invoke-RestMethod -Uri $url -Method Get -Headers $headers -TimeoutSec 10

                Write-Host "SUCCESS!" -ForegroundColor Green
                Write-Host ""
                Write-Host "FOUND WORKING ENDPOINT:" -ForegroundColor Green
                Write-Host $url -ForegroundColor Yellow
                Write-Host ""
                Write-Host "RESPONSE:" -ForegroundColor White
                Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Cyan

                $foundEndpoint = $url
                break

            } catch {
                # Silent fail, continue searching
            }
        }
        if ($foundEndpoint) { break }
    }
    if ($foundEndpoint) { break }
}

if (-not $foundEndpoint) {
    Write-Host ""
    Write-Host "No working endpoint found!" -ForegroundColor Red
    Write-Host "Tested $($tested.Count) combinations" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
