#!/usr/bin/env python3
"""
SESSION CHECKER (SSH VERSION) - Check active sessions on Windows server
"""
import json
import requests
from ssh_connector import SSHConnector
import config

class SessionChecker:
    def __init__(self):
        self.connector = SSHConnector(timeout=config.WINRM_TIMEOUT)

    def get_city_by_ip(self, ip):
        """Get city by IP using ip-api.com (free)"""
        if not ip:
            return ''
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=city", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('city', '')
        except:
            pass
        return ''

    def check_sessions(self, ip, username, password):
        ps_cmd = '''
$r=@{busy=$false;type='';user='';ip=''}

$q=quser 2>&1
if($q -notmatch 'No User' -and $q -notmatch 'Error'){
  $lines=$q -split "`n"|Select -Skip 1
  foreach($ln in $lines){
    if($ln -match 'Active' -and $ln -match '^\\s*>?(\\S+)'){
      $r.busy=$true;$r.type='RDP';$r.user=$Matches[1]
      break
    }
  }
}

if($r.busy -and $r.type -eq 'RDP'){
  $ns=netstat -n 2>$null
  foreach($line in $ns){
    if($line -match ':3389\\s+(\\d+\\.\\d+\\.\\d+\\.\\d+):\\d+\\s+ESTABLISHED'){
      $cip=$Matches[1]
      if($cip -ne '127.0.0.1' -and $cip -ne '::1'){
        $r.ip=$cip
        break
      }
    }
  }
}

$l='C:\\ProgramData\\AnyDesk\\ad_svc.trace'
if(Test-Path $l){
  $t=gc $l -Tail 50 -EA 0
  $m=$t|sls 'Logged in from (\\d+\\.\\d+\\.\\d+\\.\\d+)'|Select -Last 1
  $d=$t|sls 'Client disconnected|Session stopped'|Select -Last 1
  if($m){
    $mi=-1;$di=-1
    for($i=0;$i -lt $t.Count;$i++){
      if($t[$i] -eq $m.Line){$mi=$i}
      if($d -and $t[$i] -eq $d.Line){$di=$i}
    }
    if($mi -gt $di){
      if($r.busy){$r.type='RDP+AD'}else{$r.busy=$true;$r.type='AD'}
      if(-not $r.ip){$r.ip=$m.Matches[0].Groups[1].Value}
    }
  }
}

$r|ConvertTo-Json -Compress
'''
        output = self.connector.execute_command(ip, username, password, ps_cmd)
        client_ip = ''
        client_city = ''
        busy_status = 'Ошибка'

        if output:
            try:
                result = json.loads(output)
                busy_status = "Свободен"
                if result.get('busy'):
                    t = result.get('type', '')
                    u = result.get('user', '')
                    busy_status = f"Занят ({t}: {u})" if u else f"Занят ({t})"
                    client_ip = result.get('ip', '')
                    if client_ip:
                        client_city = self.get_city_by_ip(client_ip)
            except:
                pass

        return {
            'busyStatus': busy_status,
            'clientIp': client_ip,
            'clientCity': client_city
        }
