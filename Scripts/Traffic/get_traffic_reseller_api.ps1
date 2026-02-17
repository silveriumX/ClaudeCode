# Get package traffic info using correct Reseller API endpoint
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"  # HUB
$packageKey = "1fb08611c4d557ac8f22"  # HUB active package

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GETTING PACKAGE TRAFFIC INFO" -ForegroundColor Cyan
Write-Host "Package Key: $packageKey" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try correct Reseller API endpoint
$endpoints = @(
    "https://proxyma.io/reseller/info/package/$packageKey",
    "https://api.proxyma.io/reseller/info/package/$packageKey",
    "https://proxyma.io/api/reseller/info/package/$packageKey"
)

foreach ($endpoint in $endpoints) {
    Write-Host "Trying: $endpoint" -ForegroundColor Yellow

    try {
        $response = Invoke-RestMethod -Uri $endpoint -Method Get -Headers $headers -TimeoutSec 30

        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ""
        Write-Host "FULL RESPONSE:" -ForegroundColor White
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Gray
        Write-Host ""

        if ($response.traffic) {
            $used = $response.traffic.usage
            $limit = $response.traffic.limit
            $left = $limit - $used
            $percent = [math]::Round(($used / $limit * 100), 2)

            Write-Host "========================================" -ForegroundColor Cyan
            Write-Host "TRAFFIC STATISTICS" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Cyan
            Write-Host "Limit:   $limit GB" -ForegroundColor White
            Write-Host "Used:    $used GB ($percent%)" -ForegroundColor Yellow
            Write-Host "Left:    $left GB" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Cyan
        }

        break

    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        Write-Host "Failed: HTTP $code" -ForegroundColor Red
    }
    Write-Host ""
}
