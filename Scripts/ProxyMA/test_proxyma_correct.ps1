# Test CORRECT Proxyma API endpoint for Dynamic proxies
$ErrorActionPreference = "Stop"

# API Keys from table
$apiKeys = @(
    @{Email="ivanokunev254@gmail.com"; Shop="MN"; Key="AmHZQSYVznlllE8psYA9WEGR5L5LNbxl"},
    @{Email="oxylo@atomicmail.io"; Shop="DBZ"; Key="fvMfGKhaBCPW2de3B3Toa0WtXstShi"},
    @{Email="elproxybox@keemail.me"; Shop="VAS"; Key="6otjaD5Ch7BWWH1S29V3piA3GMXMrK"}
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROXYMA API - CORRECT ENDPOINTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($account in $apiKeys[0..0]) {  # Test first account only
    Write-Host "Account: $($account.Shop) ($($account.Email))" -ForegroundColor Yellow

    $headers = @{
        "api-key" = $account.Key
        "Content-Type" = "application/json"
    }

    # Test Dynamic packages endpoint
    Write-Host "`n[1] Getting Dynamic packages..." -ForegroundColor White
    try {
        $response = Invoke-RestMethod -Uri "https://api.proxyma.io/api/residential/packages" `
            -Method Get `
            -Headers $headers `
            -TimeoutSec 30

        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Gray

    } catch {
        Write-Host "FAILED!" -ForegroundColor Red
        Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }

    # Test profile endpoint
    Write-Host "`n[2] Getting profile (balance)..." -ForegroundColor White
    try {
        $profile = Invoke-RestMethod -Uri "https://api.proxyma.io/api/profile" `
            -Method Get `
            -Headers $headers `
            -TimeoutSec 30

        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($profile | ConvertTo-Json -Depth 5) -ForegroundColor Gray

    } catch {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
