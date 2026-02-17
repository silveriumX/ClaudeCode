# Buy traffic for HUB package via Proxyma API

# Load .env file
$envFile = Join-Path $PSScriptRoot "..\..\\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}

$ErrorActionPreference = "Stop"

$apiKey = $env:PROXYMA_API_KEY
$packageId = 28045  # Active HUB package

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BUYING TRAFFIC FOR HUB PACKAGE" -ForegroundColor Cyan
Write-Host "Package ID: $packageId" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try different payload structures
$payloads = @(
    @{
        package_id = $packageId
        traffic = 10  # 10 GB
    },
    @{
        packageId = $packageId
        traffic = 10
    },
    @{
        user_id = $packageId
        traffic = 10
    },
    @{
        id = $packageId
        traffic = 10
    },
    @{
        package_id = $packageId
        amount = 10
    },
    @{
        package_id = $packageId
        gb = 10
    }
)

$endpoint = "https://api.proxyma.io/api/residential/buy-traffic"

foreach ($payload in $payloads) {
    Write-Host "Trying payload: $($payload | ConvertTo-Json -Compress)" -ForegroundColor Yellow

    try {
        $response = Invoke-RestMethod -Uri $endpoint `
            -Method Post `
            -Headers $headers `
            -Body ($payload | ConvertTo-Json) `
            -TimeoutSec 30

        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 5) -ForegroundColor Gray
        break

    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "Failed: HTTP $statusCode" -ForegroundColor Red

        # Try to read error response
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errorBody = $reader.ReadToEnd()
            if ($errorBody.Length -lt 500) {
                Write-Host "Error: $errorBody" -ForegroundColor Red
            }
        } catch {}
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
