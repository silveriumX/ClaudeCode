#!/usr/bin/env python3
"""
=============================================================================
SERVER CHECKER (SSH VERSION) - Module for checking Windows server status
=============================================================================
Version: 6.0 (SSH + City Matching)
Date: 26.01.2026
Changes:
- Migrated from WinRM to SSH for better stability
- Added city matching (English ↔ Russian)
- Only report errors when city mismatch
=============================================================================
"""

import logging
import json
from ssh_connector import SSHConnector
from city_matcher import CityMatcher, check_city
import config

logger = logging.getLogger(__name__)

class ServerChecker:
    """
    Class for checking Windows server status via SSH

    Features:
    - Check IP and location via 2IP.io (HTTP)
    - Check running processes (Proxifier, AnyDesk, RustDesk)
    - Check active RDP/AnyDesk sessions
    - Get client IP for connections
    - Match city names (English from 2ip.io vs Russian expected)
    """

    def __init__(self):
        self.connector = SSHConnector(timeout=config.WINRM_TIMEOUT)
        self.city_matcher = CityMatcher()

    def check_full_status(self, ip, username, password):
        """
        Full server status check via SSH

        Returns:
            dict with keys:
                success, statusMachine, statusProxy, currentIp, currentCity,
                anydesk, rustdesk, isBusy, busyType, busyUser, clientIp
        """
        # PowerShell command for full check (OPTIMIZED for SSH compatibility)
        # Сокращенная версия для работы с OpenSSH 9.5
        ps_cmd = f'''
$pr=[bool](ps Proxifier -EA 0);$ad=[bool](ps AnyDesk -EA 0);$rd=[bool](ps rustdesk -EA 0)
$rdpU="";$qu=quser 2>&1;if($qu -notmatch "No User"){{$qu-split"`n"|select -skip 1|%{{if($_-match'^\s*>?(\S+)'){{$rdpU=$matches[1]}}}}}}
$rdpIp="";try{{$e=Get-WinEvent -FilterHashtable @{{LogName='Security';ID=4624}} -MaxEvents 3 -EA 0|?{{$_.Properties[8].Value -eq 10}}|select -First 1;if($e){{$rdpIp=$e.Properties[18].Value}}}}catch{{}}
try{{$r=irm "http://api.2ip.io/?token={config.API_TOKEN_2IP}" -TimeoutSec 8;@{{s=$true;ip=$r.ip;city=$r.city;pr=$pr;ad=$ad;rd=$rd;isBusy=!!$rdpU;busyType=if($rdpU){{"RDP"}}else{{""}};busyUser=$rdpU;clientIp=$rdpIp}}|ConvertTo-Json -Compress}}catch{{@{{s=$false;pr=$pr;ad=$ad;rd=$rd;isBusy=!!$rdpU;busyType=if($rdpU){{"RDP"}}else{{""}};busyUser=$rdpU;clientIp=$rdpIp}}|ConvertTo-Json -Compress}}
'''

        output = self.connector.execute_command(ip, username, password, ps_cmd)

        if output:
            try:
                result = json.loads(output)

                # Различаем: сервер работает VS IP не получен
                # Если есть данные о процессах - сервер доступен
                has_process_data = 'pr' in result or 'ad' in result or 'rd' in result

                if has_process_data:
                    # Сервер отвечает
                    status_machine = "OK Online" if result.get('s') else "OK Online (IP не определен)"
                    status_proxy = "OK" if result.get('s') and result.get('pr') else (
                        "ERROR Proxifier Off" if not result.get('pr') else "OK (IP не определен)"
                    )
                else:
                    # Сервер не отвечает
                    status_machine = "ERROR IP"
                    status_proxy = "ERROR IP"

                # Format busy status
                busy_status = "Свободен"
                if result.get('isBusy'):
                    busy_type = result.get('busyType', '')
                    busy_user = result.get('busyUser', '')
                    if busy_user:
                        busy_status = f"Занят ({busy_type}: {busy_user})"
                    else:
                        busy_status = f"Занят ({busy_type})"

                return {
                    'success': has_process_data,  # Сервер доступен если есть данные о процессах
                    'statusMachine': status_machine,
                    'statusProxy': status_proxy,
                    'currentIp': result.get('ip', 'Не определен'),
                    'currentCity': result.get('city', 'Не определен'),
                    'anydesk': result.get('ad', False),
                    'rustdesk': result.get('rd', False),
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
            'busyStatus': 'Неизвестно',
            'busyType': '',
            'busyUser': '',
            'clientIp': ''
        }
