# Try more specific endpoints for Dynamic proxies traffic purchase
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"  # HUB
$packageId = 28045

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "Testing more specific endpoints..." -ForegroundColor Cyan
Write-Host ""

# More specific endpoints
$testCases = @(
    @{url="https://api.proxyma.io/api/residential/packages/$packageId/add-traffic"; method="POST"; body=@{traffic=10}},
    @{url="https://api.proxyma.io/api/residential/$packageId/add-traffic"; method="POST"; body=@{traffic=10}},
    @{url="https://api.proxyma.io/api/residential/packages/$packageId/purchase"; method="POST"; body=@{traffic=10}},
    @{url="https://api.proxyma.io/api/residential/tariffs"; method="GET"; body=$null},
    @{url="https://api.proxyma.io/api/residential/buy"; method="POST"; body=@{package_id=$packageId; traffic=10}},
    @{url="https://api.proxyma.io/api/profile/balance"; method="GET"; body=$null}
)

foreach ($test in $testCases) {
    Write-Host "$($test.method) $($test.url)" -ForegroundColor Yellow

    try {
        $params = @{
            Uri = $test.url
            Method = $test.method
            Headers = $headers
            TimeoutSec = 10
        }

        if ($test.body) {
            $params.Body = ($test.body | ConvertTo-Json)
        }

        $response = Invoke-RestMethod @params
        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 5) -ForegroundColor Gray

    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        Write-Host "HTTP $code" -ForegroundColor $(if ($code -eq 404) {"Red"} elseif ($code -eq 405) {"Yellow"} else {"Magenta"})
    }
    Write-Host ""
}
