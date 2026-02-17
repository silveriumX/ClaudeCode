# Try POST requests for statistics
$ErrorActionPreference = "Stop"

$apiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"
$packageId = 28045

$headers = @{
    "api-key" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "Testing POST requests for statistics..." -ForegroundColor Cyan
Write-Host ""

$endpoints = @(
    "https://api.proxyma.io/api/residential/stats",
    "https://api.proxyma.io/api/residential/statistics",
    "https://api.proxyma.io/api/residential/usage",
    "https://api.proxyma.io/api/residential/traffic"
)

$payloads = @(
    @{package_id = $packageId},
    @{packageId = $packageId},
    @{id = $packageId},
    @{user_package_id = $packageId},
    @{}  # Empty payload
)

foreach ($endpoint in $endpoints) {
    Write-Host "Endpoint: $endpoint" -ForegroundColor Yellow

    foreach ($payload in $payloads) {
        $payloadStr = if ($payload.Count -eq 0) {"(empty)"} else {($payload | ConvertTo-Json -Compress)}
        Write-Host "  Payload: $payloadStr" -ForegroundColor Gray

        try {
            $body = if ($payload.Count -eq 0) {$null} else {($payload | ConvertTo-Json)}

            $params = @{
                Uri = $endpoint
                Method = "Post"
                Headers = $headers
                TimeoutSec = 10
            }

            if ($body) {
                $params.Body = $body
            }

            $response = Invoke-RestMethod @params
            Write-Host "  SUCCESS!" -ForegroundColor Green
            Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor White
            Write-Host ""
            break

        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            Write-Host "  -> HTTP $code" -ForegroundColor DarkGray
        }
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
