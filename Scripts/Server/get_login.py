import json

with open('servers_data.json', encoding='utf-8') as f:
    data = json.load(f)

# Find MN proxyma account
for server in data['data']:
    if server.get('Магазин') == 'MN' and server.get('Провайдер') == 'proxyma':
        print(f"Email: {server.get('Провайдер логин', '')}")
        print(f"Password: {server.get('Провайдер пароль', '')}")
        break
