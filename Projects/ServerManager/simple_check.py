#!/usr/bin/env python3
import json

with open('servers_full_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

rdp_col = 'RDP \nIP:Username:Password'
problem_ips = ['89.124.71.240', '89.124.72.242', '91.201.113.127', '62.84.101.97', '5.35.32.68']

print("=" * 80)
print("ПРОБЛЕМНЫЕ СЕРВЕРЫ:")
print("=" * 80)

found = [s for s in data['all_servers'] if any(ip in s.get(rdp_col, '') for ip in problem_ips)]

print(f"\nНайдено: {len(found)} из {len(problem_ips)}")
print()

for s in found:
    rdp = s.get(rdp_col, 'N/A')
    shop = s.get('Магазин', 'N/A')
    status = s.get('Статус машины', 'N/A')

    if ':' in rdp:
        parts = rdp.split(':')
        ip = parts[0]
        username = parts[1] if len(parts) > 1 else 'N/A'
        password = parts[2] if len(parts) > 2 else 'N/A'

        print(f"Shop: {shop} | Status: {status}")
        print(f"  IP: {ip}")
        print(f"  Username: '{username}'")
        print(f"  Password: {'*' * len(password)} ({len(password)} chars)")

        # Проверка проблем
        if '\\' in username:
            print(f"  [PROBLEM] Username has backslash!")
        else:
            print(f"  [OK] Username format correct")

        print()
