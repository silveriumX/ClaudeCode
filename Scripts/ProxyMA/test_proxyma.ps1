# WARNING: Contains API keys. Move to secure storage before sharing.
# Test Proxyma API via PowerShell
# Using exact API specification provided

$ErrorActionPreference = "Stop"

# API Keys from table
$apiKeys = @(
    @{Email="ivanokunev254@gmail.com"; Shop="MN"; Key="AmHZQSYVznlllE8psYA9GR5L5LNbxl"},  # pragma: allowlist secret
    @{Email="oxylo@atomicmail.io"; Shop="DBZ"; Key="fvMfGKhaBCPW2de3B3Toa0WtXstShi"},  # pragma: allowlist secret
    @{Email="elproxybox@keemail.me"; Shop="VAS"; Key="6otjaD5Ch7BWWH1S29V3piA3GMXMrK"},  # pragma: allowlist secret
    @{Email="max.veb1r49q@gmail.com"; Shop="MAKS"; Key="7mIans4pDD3rW4seFAxbvyOY3ToTp7"},  # pragma: allowlist secret
    @{Email="maiksho73@gmail.com"; Shop="LIFE"; Key="X5nklGVFCuKe25p3Zz4jhM1Wh6YFjo"},  # pragma: allowlist secret
    @{Email="mil9lqo@atomicmail.io"; Shop="ALEX"; Key="VmEWRA6BdJwxMLHor8qw7OkA5ofHF5"},  # pragma: allowlist secret
    @{Email="johnwicw12@gmail.com"; Shop="HUB"; Key="n2yhff6z7fC1VBBKi8QveSr9LYm5Li"}  # pragma: allowlist secret
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROXYMA API TEST - PowerShell" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($account in $apiKeys) {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "Account: $($account.Shop) ($($account.Email))" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow

    $headers = @{
        "api-key" = $account.Key
        "Content-Type" = "application/json"
    }

    # Test 1: Get Packages
    Write-Host "`n[1] Getting packages..." -ForegroundColor White
    try {
        $response = Invoke-RestMethod -Uri "https://proxyma.io/api/residential-unlim/packages" `
            -Method Get `
            -Headers $headers `
            -TimeoutSec 30

        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 5) -ForegroundColor Gray

        # If we have packages, get usage for first one
        if ($response.packages -and $response.packages.Count -gt 0) {
            $pkgId = $response.packages[0].id
            Write-Host "`n[2] Getting usage for package $pkgId..." -ForegroundColor White

            try {
                $usage = Invoke-RestMethod -Uri "https://proxyma.io/api/residential-unlim/$pkgId/usage" `
                    -Method Get `
                    -Headers $headers `
                    -TimeoutSec 30

                Write-Host "SUCCESS!" -ForegroundColor Green
                Write-Host ($usage | ConvertTo-Json -Depth 5) -ForegroundColor Gray
            } catch {
                Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
            }
        }

    } catch {
        Write-Host "FAILED!" -ForegroundColor Red
        Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red

        # Try to get response body
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            if ($responseBody.Length -lt 500) {
                Write-Host "Response: $responseBody" -ForegroundColor Red
            } else {
                Write-Host "Response: [HTML page - ${$responseBody.Length} bytes]" -ForegroundColor Red
            }
        }
    }

    # Test 2: Get Locations
    Write-Host "`n[3] Getting locations..." -ForegroundColor White
    try {
        $locations = Invoke-RestMethod -Uri "https://proxyma.io/api/residential-unlim/locations" `
            -Method Get `
            -Headers $headers `
            -TimeoutSec 30

        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($locations | ConvertTo-Json -Depth 3) -ForegroundColor Gray
    } catch {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host "`n"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
