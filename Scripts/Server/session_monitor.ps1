# Session Monitor - Check active RDP/AnyDesk sessions on servers via WinRM
# Usage: .\session_monitor.ps1 -ServerFilter "HUB"

param(
    [string]$ServerFilter = "*",
    [switch]$JsonOutput
)

$ServersDataPath = "$PSScriptRoot\..\..\Data\servers_data.csv"

function Get-ServersData {
    if (Test-Path $ServersDataPath) {
        return Import-Csv $ServersDataPath -ErrorAction SilentlyContinue
    }
    return @()
}

function Get-RdpSessions {
    param([string]$Output)

    $sessions = @()
    if ($Output -and $Output -notmatch "No User exists") {
        $lines = $Output -split "`n" | Where-Object { $_ -match '\S' } | Select-Object -Skip 1
        foreach ($line in $lines) {
            if ($line -match '^\s*(\S+)\s+(\S+)?\s+(\d+)\s+(\w+)') {
                $sessions += @{
                    Username = $Matches[1]
                    SessionId = $Matches[3]
                    State = $Matches[4]
                }
            }
        }
    }
    return $sessions
}

function Test-ServerSession {
    param([Parameter(Mandatory)][PSCustomObject]$Server)

    # Get shop name from CSV (header may vary due to encoding)
    $shopProp = $Server.PSObject.Properties | Where-Object { $_.Name -match "^.{0,5}$" -or $_.Name -eq "Магазин" } | Select-Object -First 1
    $shop = if ($shopProp) { $shopProp.Value } else { "Unknown" }

    # Try different property names for server ID
    $serverId = $Server."ID сервера в админке"
    if (-not $serverId) {
        $idProp = $Server.PSObject.Properties | Where-Object { $_.Name -match "ID" } | Select-Object -First 1
        $serverId = if ($idProp) { $idProp.Value } else { "" }
    }

    $result = @{
        Shop = $shop
        ServerId = $serverId
        AnyDesk = $Server."anydesk (AD)"
        RdpIp = $null
        Status = "Unknown"
        RdpSessions = @()
        AnyDeskRunning = $false
        Error = $null
        CheckTime = Get-Date -Format "dd.MM.yyyy HH:mm:ss"
    }

    $rdpString = $Server."RDP IP:Username:Password"
    if (-not $rdpString) {
        $result.Status = "NoRDP"
        return $result
    }

    $rdpParts = $rdpString -split ":"
    if ($rdpParts.Count -lt 3) {
        $result.Status = "InvalidRDP"
        return $result
    }

    $ip = $rdpParts[0]
    $username = $rdpParts[1]
    $password = $rdpParts[2]
    $result.RdpIp = $ip

    try {
        $secpasswd = ConvertTo-SecureString $password -AsPlainText -Force
        $cred = New-Object System.Management.Automation.PSCredential ($username, $secpasswd)

        $remoteResult = Invoke-Command -ComputerName $ip -Credential $cred -ErrorAction Stop -ScriptBlock {
            $rdp = quser 2>&1 | Out-String
            $adProcess = Get-Process AnyDesk* -ErrorAction SilentlyContinue
            @{
                Quser = $rdp
                AnyDeskRunning = ($null -ne $adProcess)
            }
        }

        $result.RdpSessions = Get-RdpSessions -Output $remoteResult.Quser
        $result.AnyDeskRunning = $remoteResult.AnyDeskRunning

        $activeRdp = $result.RdpSessions | Where-Object { $_.State -eq "Active" }

        if ($activeRdp) {
            $users = ($activeRdp | ForEach-Object { $_.Username }) -join ", "
            $result.Status = "Busy"
            $result.BusyReason = "RDP: $users"
        } else {
            $result.Status = "Free"
        }

    } catch {
        $result.Status = "Error"
        $result.Error = $_.Exception.Message
    }

    return $result
}

# === MAIN ===
Write-Host "=== Session Monitor ===" -ForegroundColor Cyan

$servers = Get-ServersData
if (-not $servers -or $servers.Count -eq 0) {
    Write-Error "Failed to load servers data from: $ServersDataPath"
    exit 1
}

Write-Host "Loaded $($servers.Count) servers" -ForegroundColor Gray

# Filter by shop name
if ($ServerFilter -ne "*") {
    $servers = $servers | Where-Object {
        $shopProp = $_.PSObject.Properties | Select-Object -First 1
        $shopProp.Value -like "*$ServerFilter*"
    }
}

# Filter only servers with RDP
$serversWithRdp = $servers | Where-Object { $_."RDP IP:Username:Password" }
Write-Host "Servers with RDP: $($serversWithRdp.Count)" -ForegroundColor Yellow
Write-Host ""

$results = @()

foreach ($server in $serversWithRdp) {
    $shopProp = $server.PSObject.Properties | Select-Object -First 1
    $shop = $shopProp.Value
    $rdpIp = ($server."RDP IP:Username:Password" -split ":")[0]

    Write-Host "Checking: $shop ($rdpIp)... " -NoNewline

    $result = Test-ServerSession -Server $server
    $results += $result

    switch ($result.Status) {
        "Free" { Write-Host "FREE" -ForegroundColor Green }
        "Busy" { Write-Host "BUSY ($($result.BusyReason))" -ForegroundColor Red }
        "Error" { Write-Host "ERROR" -ForegroundColor Yellow }
        default { Write-Host $result.Status -ForegroundColor Gray }
    }
}

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Cyan

$free = ($results | Where-Object { $_.Status -eq "Free" }).Count
$busy = ($results | Where-Object { $_.Status -eq "Busy" }).Count
$errors = ($results | Where-Object { $_.Status -eq "Error" }).Count

Write-Host "Free: $free" -ForegroundColor Green
Write-Host "Busy: $busy" -ForegroundColor Red
Write-Host "Errors: $errors" -ForegroundColor Yellow

if ($JsonOutput) {
    Write-Output ($results | ConvertTo-Json -Depth 5)
}
