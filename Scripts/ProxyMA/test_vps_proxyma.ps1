# Send check_proxyma command to VPS
$vpsUrl = "http://151.241.154.57:8080/execute_command"

# HUB data
$payload = @{
    rdp = "0.0.0.0:root:dummy"  # Dummy RDP, just to test proxyma check
    command = "check_proxyma"
    proxyKey = "1fb08611c4d557ac8f22"
    proxymaApiKey = "n2yhff6z7fC1VBBKi8QveSr9LYm5Li"
} | ConvertTo-Json

Write-Host "Sending check_proxyma command to VPS..." -ForegroundColor Cyan
Write-Host "Payload:" -ForegroundColor Yellow
Write-Host $payload -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $vpsUrl `
        -Method Post `
        -Body $payload `
        -ContentType "application/json" `
        -TimeoutSec 60

    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor White
    Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Cyan

} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}
