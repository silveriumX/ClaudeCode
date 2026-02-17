# Try to read proxyma_api.py from VPS
$vpsUrl = "http://151.241.154.57:8080/execute_command"

# Try to execute a command that reads the file
$payload = @{
    rdp = "151.241.154.57:root:password222"
    command = "get_file_content"  # Custom command
    file_path = "/root/proxyma_api.py"
} | ConvertTo-Json

Write-Host "Attempting to read proxyma_api.py from VPS..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $vpsUrl `
        -Method Post `
        -Body $payload `
        -ContentType "application/json" `
        -TimeoutSec 30

    Write-Host "Response:" -ForegroundColor White
    Write-Host ($response | ConvertTo-Json -Depth 5) -ForegroundColor Gray

} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n---`n" -ForegroundColor Cyan

# Try alternative: use VPS to list files
$payload2 = @{
    rdp = "151.241.154.57:root:password222"
    command = "list_files"
} | ConvertTo-Json

Write-Host "Trying to list files on VPS..." -ForegroundColor Cyan

try {
    $response2 = Invoke-RestMethod -Uri $vpsUrl `
        -Method Post `
        -Body $payload2 `
        -ContentType "application/json" `
        -TimeoutSec 30

    Write-Host "Response:" -ForegroundColor White
    Write-Host ($response2 | ConvertTo-Json -Depth 5) -ForegroundColor Gray

} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}
