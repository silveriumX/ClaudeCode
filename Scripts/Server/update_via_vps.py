import json
import requests
import time
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load current table data
with open('servers_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find HUB server
hub_server = None
for server in data['data']:
    if server.get('Магазин') == 'HUB' and server.get('Провайдер') == 'proxyma':
        hub_server = server
        break

if not hub_server:
    print("❌ HUB server not found")
    exit(1)

print("="*80)
print("🚀 UPDATING PROXYMA DATA VIA VPS")
print("="*80)
print()

rdp = hub_server.get('RDP IP:Username:Password', '').strip()
proxy_key = hub_server.get('Package Key proxyma', '').strip()
api_key = hub_server.get('Proxyma API Key ', '').strip()

print(f"Server: HUB")
print(f"RDP: {rdp[:30]}...")
print(f"Proxy Key: {proxy_key}")
print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
print()

# Send command to VPS
vps_url = "http://151.241.154.57:8080/execute_command"
payload = {
    "rdp": rdp,
    "command": "check_proxyma",
    "proxyKey": proxy_key,
    "proxymaApiKey": api_key
}

print("📡 Sending check_proxyma command to VPS...")

try:
    response = requests.post(vps_url, json=payload, timeout=60)

    if response.status_code == 200:
        result = response.json()
        print("✅ Command sent successfully!")
        print(f"Response: {result}")
        print()
        print("⏳ Waiting 5 seconds for VPS to update Google Sheets...")
        time.sleep(5)

        # Now re-read the Google Sheet
        print()
        print("📊 Reading updated Google Sheet...")

        sheet_url = "https://docs.google.com/spreadsheets/d/1wIS9hjLSbIU4PSjXbXyIoh3_KHVBRaX2jDQVj4o51V8/export?format=csv&gid=0"

        sheet_response = requests.get(sheet_url, timeout=30)

        if sheet_response.status_code == 200:
            # Parse CSV and find HUB row
            import csv
            import io

            csv_data = csv.reader(io.StringIO(sheet_response.text))
            headers = next(csv_data)

            # Find column indexes
            proxy_used_idx = None
            proxy_left_idx = None
            proxy_limit_idx = None
            proxy_expires_idx = None
            store_idx = None

            for idx, header in enumerate(headers):
                h = header.lower()
                if 'использовано' in h and 'gb' in h:
                    proxy_used_idx = idx
                if 'осталось' in h and 'gb' in h:
                    proxy_left_idx = idx
                if 'лимит трафика' in h:
                    proxy_limit_idx = idx
                if 'дата истечения прокси' in h:
                    proxy_expires_idx = idx
                if 'магазин' in h:
                    store_idx = idx

            print(f"Found columns: limit={proxy_limit_idx}, used={proxy_used_idx}, left={proxy_left_idx}")
            print()

            # Find HUB rows
            for row in csv_data:
                if store_idx and row[store_idx] == 'HUB':
                    print("="*60)
                    print(f"📦 HUB Package Data (UPDATED)")
                    print("="*60)

                    if proxy_limit_idx and proxy_limit_idx < len(row):
                        print(f"Limit:    {row[proxy_limit_idx]} GB")
                    if proxy_used_idx and proxy_used_idx < len(row):
                        print(f"Used:     {row[proxy_used_idx]} GB")
                    if proxy_left_idx and proxy_left_idx < len(row):
                        print(f"Left:     {row[proxy_left_idx]} GB")
                    if proxy_expires_idx and proxy_expires_idx < len(row):
                        print(f"Expires:  {row[proxy_expires_idx]}")
                    print("="*60)
                    print()
                    break
        else:
            print(f"❌ Failed to read sheet: HTTP {sheet_response.status_code}")
    else:
        print(f"❌ VPS returned: HTTP {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Error: {e}")
