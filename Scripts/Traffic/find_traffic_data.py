import json

with open('servers_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== HEADERS WITH TRAFFIC ===")
for idx, header in enumerate(data['headers']):
    if any(word in header.lower() for word in ['трафик', 'traffic', 'gb', 'лимит', 'использ']):
        print(f"{idx}: {header}")

print("\n=== HUB DATA ===")
for server in data['data']:
    if server.get('Магазин') == 'HUB':
        print(f"\nServer: {server.get('ID сервера в админке', 'N/A')}")
        print(f"Provider: {server.get('Провайдер', 'N/A')}")

        # Print all keys that might contain traffic info
        for key, value in server.items():
            if any(word in key.lower() for word in ['трафик', 'traffic', 'gb', 'лимит', 'использ', 'остат']):
                print(f"  {key}: {value}")
