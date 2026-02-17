import json

with open('servers_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("HUB servers RDP info:")
print("="*60)

for server in data['data']:
    if server.get('Магазин') == 'HUB':
        print(f"\nServer ID: {server.get('ID сервера в админке')}")

        # Find RDP column
        for key, value in server.items():
            if 'rdp' in key.lower() or ('ip' in key.lower() and 'username' in key.lower()):
                print(f"  {key}: {str(value)[:80]}")
