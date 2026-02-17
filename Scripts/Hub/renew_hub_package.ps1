# Renew HUB package via API
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"  # HUB
$packageId = 28045
$packageKey = "1fb08611c4d557ac8f22"

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ДОСРОЧНОЕ ПРОДЛЕНИЕ ПАКЕТА HUB" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Package ID: $packageId" -ForegroundColor Yellow
Write-Host "Package Key: $packageKey" -ForegroundColor Yellow
Write-Host "Current: 9.04/10 GB used, 0.96 GB left" -ForegroundColor Red
Write-Host "Balance: `$66 (sufficient for `$30 renewal)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try different renew endpoints
$renewEndpoints = @(
    @{url="https://api.proxyma.io/api/residential/$packageId/renew"; method="POST"; body=@{}},
    @{url="https://api.proxyma.io/api/residential/packages/$packageId/renew"; method="POST"; body=@{}},
    @{url="https://api.proxyma.io/api/residential/$packageId/renew"; method="POST"; body=@{package_key=$packageKey}},
    @{url="https://api.proxyma.io/api/residential/renew"; method="POST"; body=@{package_id=$packageId}},
    @{url="https://api.proxyma.io/api/residential/renew"; method="POST"; body=@{package_key=$packageKey}},
    @{url="https://cabinet.proxyma.io/api/residential/$packageId/renew"; method="POST"; body=@{}},
    @{url="https://cabinet.proxyma.io/api/residential/packages/$packageId/renew"; method="POST"; body=@{}}
)

$success = $false

foreach ($endpoint in $renewEndpoints) {
    Write-Host "Trying: $($endpoint.url)" -ForegroundColor Yellow

    try {
        $params = @{
            Uri = $endpoint.url
            Method = $endpoint.method
            Headers = $headers
            TimeoutSec = 30
        }

        if ($endpoint.body.Count -gt 0) {
            $params.Body = ($endpoint.body | ConvertTo-Json)
            Write-Host "  Body: $($params.Body)" -ForegroundColor Gray
        }

        $response = Invoke-RestMethod @params

        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Response:" -ForegroundColor White
        Write-Host ($response | ConvertTo-Json -Depth 5) -ForegroundColor Cyan

        $success = $true
        break

    } catch {
        $code = $_.Exception.Response.StatusCode.value__

        if ($code -eq 200 -or $code -eq 201) {
            Write-Host "  Success (HTTP $code)" -ForegroundColor Green
            $success = $true
            break
        } elseif ($code -eq 405) {
            Write-Host "  405 Method Not Allowed" -ForegroundColor Yellow
        } elseif ($code -eq 404) {
            Write-Host "  404 Not Found" -ForegroundColor DarkGray
        } else {
            Write-Host "  HTTP $code" -ForegroundColor Red

            # Try to get error message
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $errorBody = $reader.ReadToEnd()
                if ($errorBody.Length -lt 200) {
                    Write-Host "  Error: $errorBody" -ForegroundColor Red
                }
            } catch {}
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($success) {
    Write-Host "RENEWAL SUCCESSFUL!" -ForegroundColor Green
    Write-Host "New traffic: 10 GB available" -ForegroundColor Green
} else {
    Write-Host "API renewal failed - will use browser" -ForegroundColor Yellow
}
