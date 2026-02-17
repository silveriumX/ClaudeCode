#!/usr/bin/env python3
"""
Session Monitor - Check active RDP/AnyDesk sessions on Windows servers via WinRM
Run from VPS: python3 session_monitor.py [--filter HUB]
"""

import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    import winrm
except ImportError:
    print("Installing pywinrm...")
    import subprocess
    subprocess.check_call(['pip3', 'install', 'pywinrm'])
    import winrm


def load_servers(json_path: str) -> list:
    """Load servers from JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('data', [])


def parse_quser_output(output: str) -> list:
    """Parse quser command output to get active sessions"""
    sessions = []
    lines = output.strip().split('\n')

    for line in lines[1:]:  # Skip header
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 4:
            sessions.append({
                'username': parts[0].lstrip('>'),
                'state': parts[3] if len(parts) > 3 else 'Unknown'
            })
    return sessions


def check_server_session(server: dict) -> dict:
    """Check if server is busy via WinRM"""
    result = {
        'shop': server.get('Магазин', 'Unknown'),
        'server_id': server.get('ID сервера в админке', ''),
        'anydesk': server.get('anydesk (AD)', ''),
        'rdp_ip': None,
        'status': 'Unknown',
        'busy_reason': None,
        'sessions': [],
        'error': None,
        'check_time': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    }

    rdp_string = server.get('RDP IP:Username:Password', '')
    if not rdp_string:
        result['status'] = 'NoRDP'
        return result

    parts = rdp_string.split(':')
    if len(parts) < 3:
        result['status'] = 'InvalidRDP'
        return result

    ip, username, password = parts[0], parts[1], parts[2]
    result['rdp_ip'] = ip

    try:
        # Connect via WinRM
        session = winrm.Session(
            f'http://{ip}:5985/wsman',
            auth=(username, password),
            transport='ntlm'
        )

        # Run quser to get active sessions
        cmd = session.run_cmd('quser')
        output = cmd.std_out.decode('cp866', errors='ignore')

        if 'No User exists' in output or cmd.status_code != 0:
            result['status'] = 'Free'
            result['sessions'] = []
        else:
            sessions = parse_quser_output(output)
            result['sessions'] = sessions

            active = [s for s in sessions if s.get('state') == 'Active']
            if active:
                users = ', '.join([s['username'] for s in active])
                result['status'] = 'Busy'
                result['busy_reason'] = f"RDP: {users}"
            else:
                result['status'] = 'Free'

    except Exception as e:
        result['status'] = 'Error'
        result['error'] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description='Check server sessions via WinRM')
    parser.add_argument('--filter', '-f', default='*', help='Filter by shop name')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    parser.add_argument('--data', '-d', default='/root/servers_data.json', help='Path to servers JSON')
    args = parser.parse_args()

    print("=== Session Monitor ===")

    # Try to load from different paths
    data_paths = [
        args.data,
        'servers_data.json',
        '/root/servers_data.json',
        '/home/servers_data.json'
    ]

    servers = None
    for path in data_paths:
        if Path(path).exists():
            servers = load_servers(path)
            print(f"Loaded {len(servers)} servers from {path}")
            break

    if not servers:
        print("ERROR: servers_data.json not found")
        print("Upload it to VPS first: scp Data/servers_data.json root@151.241.154.57:/root/")
        return

    # Filter servers
    if args.filter != '*':
        servers = [s for s in servers if args.filter.lower() in s.get('Магазин', '').lower()]

    # Only servers with RDP
    servers_with_rdp = [s for s in servers if s.get('RDP IP:Username:Password')]
    print(f"Servers with RDP: {len(servers_with_rdp)}")
    print()

    results = []

    for server in servers_with_rdp:
        shop = server.get('Магазин', 'Unknown')
        rdp_ip = server.get('RDP IP:Username:Password', '').split(':')[0]

        print(f"Checking: {shop} ({rdp_ip})... ", end='', flush=True)

        result = check_server_session(server)
        results.append(result)

        if result['status'] == 'Free':
            print("\033[92mFREE\033[0m")
        elif result['status'] == 'Busy':
            print(f"\033[91mBUSY ({result['busy_reason']})\033[0m")
        elif result['status'] == 'Error':
            print(f"\033[93mERROR\033[0m")
        else:
            print(result['status'])

    print()
    print("=== SUMMARY ===")

    free = len([r for r in results if r['status'] == 'Free'])
    busy = len([r for r in results if r['status'] == 'Busy'])
    errors = len([r for r in results if r['status'] == 'Error'])

    print(f"\033[92mFree: {free}\033[0m")
    print(f"\033[91mBusy: {busy}\033[0m")
    print(f"\033[93mErrors: {errors}\033[0m")

    if args.json:
        print()
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return results


if __name__ == '__main__':
    main()
