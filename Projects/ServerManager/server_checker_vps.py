#!/usr/bin/env python3
"""
=============================================================================
SERVER CHECKER - Module for checking Windows server status
=============================================================================
Version: 4.0 (with session monitoring)
Date: 19.01.2026
Added: RDP/AnyDesk session detection + client IP
=============================================================================
"""

import logging
import json
import re
from winrm_connector import WinRMConnector
import config

logger = logging.getLogger(__name__)

class ServerChecker:
    """
    Class for checking Windows server status via WinRM

    Features:
    - Check IP and location via 2IP.io
    - Check running processes (Proxifier, AnyDesk, RustDesk)
    - Check timezone and languages
    - NEW: Check active RDP/AnyDesk sessions
    - NEW: Get client IP for connections
    """

    def __init__(self):
        self.connector = WinRMConnector(timeout=config.WINRM_TIMEOUT)

    def check_full_status(self, ip, username, password):
        """
        Full server status check including session monitoring

        Returns:
            dict with keys:
                success, statusMachine, statusProxy, currentIp, currentCity,
                anydesk, rustdesk,
                NEW: isBusy, busyType, busyUser, clientIp
        """
        # PowerShell command for full check
        ps_cmd = f'''
$pr=[bool](ps Proxifier -EA 0)
$ad=[bool](ps AnyDesk -EA 0)
$rd=[bool](ps rustdesk -EA 0)

# Check RDP sessions
$rdpSessions = @()
$rdpOutput = quser 2>&1
if ($rdpOutput -notmatch "No User exists") {{
    $lines = $rdpOutput -split "
" | Select-Object -Skip 1
    foreach ($line in $lines) {{
        if ($line -match '^\s*>?(\S+)\s+') {{
            $rdpSessions += $Matches[1]
        }}
    }}
}}

# Check RDP client IP from Security Log
$rdpClientIp = ""
try {{
    $evt = Get-WinEvent -FilterHashtable @{{LogName='Security';ID=4624}} -MaxEvents 5 -EA 0 |
        Where-Object {{ $_.Properties[8].Value -eq 10 }} | Select-Object -First 1
    if ($evt) {{
        $rdpClientIp = $evt.Properties[18].Value
    }}
}} catch {{}}

# Check AnyDesk connections from trace log
$adClientIp = ""
$adConnected = $false
$adLogPath = "C:\ProgramData\AnyDesk\ad_svc.trace"
if (Test-Path $adLogPath) {{
    $adLog = Get-Content $adLogPath -Tail 50 -EA 0
    # Look for recent "Logged in from" entries (within last 30 min based on file position)
    $loginMatch = $adLog | Select-String "Logged in from (\d+\.\d+\.\d+\.\d+)" | Select-Object -Last 1
    $disconnectMatch = $adLog | Select-String "Client disconnected|Session stopped" | Select-Object -Last 1

    if ($loginMatch) {{
        # Check if login is after last disconnect
        $loginIdx = [array]::IndexOf($adLog, $loginMatch.Line)
        $disconnIdx = if ($disconnectMatch) {{ [array]::IndexOf($adLog, $disconnectMatch.Line) }} else {{ -1 }}

        if ($loginIdx -gt $disconnIdx) {{
            $adConnected = $true
            $adClientIp = $loginMatch.Matches[0].Groups[1].Value
        }}
    }}
}}

# Get IP from 2IP.io
try {{
    $r = irm "https://api.2ip.io/?token={config.API_TOKEN_2IP}" -TimeoutSec 10

    # Determine busy status
    $isBusy = $false
    $busyType = ""
    $busyUser = ""
    $clientIp = ""

    if ($rdpSessions.Count -gt 0) {{
        $isBusy = $true
        $busyType = "RDP"
        $busyUser = $rdpSessions[0]
        $clientIp = $rdpClientIp
    }}

    if ($adConnected) {{
        if ($isBusy) {{
            $busyType = "RDP+AnyDesk"
        }} else {{
            $isBusy = $true
            $busyType = "AnyDesk"
        }}
        if (-not $clientIp) {{
            $clientIp = $adClientIp
        }}
    }}

    @{{
        s = $true
        ip = $r.ip
        city = $r.city
        pr = $pr
        ad = $ad
        rd = $rd
        isBusy = $isBusy
        busyType = $busyType
        busyUser = $busyUser
        clientIp = $clientIp
    }} | ConvertTo-Json -Compress
}} catch {{
    @{{
        s = $false
        pr = $pr
        ad = $ad
        rd = $rd
        isBusy = ($rdpSessions.Count -gt 0 -or $adConnected)
        busyType = if ($rdpSessions.Count -gt 0) {{ "RDP" }} elseif ($adConnected) {{ "AnyDesk" }} else {{ "" }}
        busyUser = if ($rdpSessions.Count -gt 0) {{ $rdpSessions[0] }} else {{ "" }}
        clientIp = if ($rdpClientIp) {{ $rdpClientIp }} else {{ $adClientIp }}
    }} | ConvertTo-Json -Compress
}}
'''

        output = self.connector.execute_command(ip, username, password, ps_cmd)

        if output:
            try:
                result = json.loads(output)

                status_machine = "OK Online" if result.get('s') else "ERROR IP"
                status_proxy = "OK" if result.get('s') and result.get('pr') else (
                    "ERROR Proxifier Off" if not result.get('pr') else "ERROR IP"
                )

                # Format busy status for display
                busy_status = "Свободен"
                if result.get('isBusy'):
                    busy_type = result.get('busyType', '')
                    busy_user = result.get('busyUser', '')
                    if busy_user:
                        busy_status = f"Занят ({busy_type}: {busy_user})"
                    else:
                        busy_status = f"Занят ({busy_type})"

                return {
                    'success': True,
                    'statusMachine': status_machine,
                    'statusProxy': status_proxy,
                    'currentIp': result.get('ip', 'N/A'),
                    'currentCity': result.get('city', 'N/A'),
                    'anydesk': result.get('ad', False),
                    'rustdesk': result.get('rd', False),
                    # New fields for session monitoring
                    'isBusy': result.get('isBusy', False),
                    'busyStatus': busy_status,
                    'busyType': result.get('busyType', ''),
                    'busyUser': result.get('busyUser', ''),
                    'clientIp': result.get('clientIp', '')
                }

            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error for {ip}: {e}")

        return {
            'success': False,
            'statusMachine': 'ERROR Offline',
            'statusProxy': 'ERROR Offline',
            'currentIp': 'ERROR',
            'currentCity': 'ERROR',
            'anydesk': False,
            'rustdesk': False,
            'isBusy': False,
            'busyStatus': 'РќРµРёР·РІРµСЃС‚РЅРѕ',
            'busyType': '',
            'busyUser': '',
            'clientIp': ''
        }

    def get_timezone(self, ip, username, password):
        ps_cmd = '''
$tz = Get-TimeZone
$time = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
@{
    id = $tz.Id
    displayName = $tz.DisplayName
    offset = $tz.BaseUtcOffset.ToString()
    currentTime = $time
} | ConvertTo-Json -Compress
'''
        output = self.connector.execute_command(ip, username, password, ps_cmd)
        if output:
            try:
                return json.loads(output)
            except:
                pass
        return None

    def get_languages(self, ip, username, password):
        ps_cmd = '''
$langs = Get-WinUserLanguageList
$langs | ForEach-Object { $_.LanguageTag }
'''
        output = self.connector.execute_command(ip, username, password, ps_cmd)
        if output:
            return output.split('\n')
        return []

    def find_app_path(self, ip, username, password, app_name):
        ps_cmd = f'''
$paths = @(
    "{config.STANDARD_APPS_PATH}\{app_name}.lnk",
    "C:\Program Files (x86)\{app_name}\{app_name}.exe",
    "C:\Program Files\{app_name}\{app_name}.exe",
    "C:\{app_name}\{app_name}.exe"
)
foreach($p in $paths) {{
    if(Test-Path $p) {{
        Write-Host $p
        break
    }}
}}
'''
        output = self.connector.execute_command(ip, username, password, ps_cmd)
        return output.strip() if output else None
