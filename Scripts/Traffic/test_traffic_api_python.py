#!/usr/bin/env python3
"""
Proxyma API - Traffic Statistics
Based on provided API documentation
"""
import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ProxymaAPI:
    """Proxyma API handler"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }

    def get_package_info(self, package_key):
        """Get detailed package info including traffic"""

        # Try different base URLs
        base_urls = [
            "https://proxyma.io",
            "https://api.proxyma.io",
            "https://proxyma.io/api"
        ]

        for base_url in base_urls:
            url = f"{base_url}/reseller/info/package/{package_key}"

            try:
                response = requests.get(url, headers=self.headers, timeout=30)

                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"❌ {url}: HTTP {response.status_code}")

            except Exception as e:
                print(f"❌ {url}: {e}")

        return None


# Load data
with open('proxyma_data_complete.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('servers_data.json', 'r', encoding='utf-8') as f:
    table = json.load(f)

# Get API keys mapping
email_to_key = {}
for server in table['data']:
    if server.get('Провайдер') == 'proxyma':
        email = server.get('Провайдер логин', '').strip()
        api_key = server.get('Proxyma API Key ', '').strip()
        if email and api_key:
            email_to_key[email] = api_key

print("="*80)
print("🔍 ПОЛУЧЕНИЕ СТАТИСТИКИ ТРАФИКА ЧЕРЕЗ API")
print("="*80)
print()

# Test HUB first
hub_email = 'johnwicw12@gmail.com'
hub_data = data.get(hub_email)

if hub_data and hub_data.get('success'):
    api_key = email_to_key.get(hub_email)

    print(f"🔑 HUB Account ({hub_email})")
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
    print()

    api = ProxymaAPI(api_key)

    for pkg in hub_data['packages']:
        if pkg['status'] == 'active':
            print(f"📦 Package ID: {pkg['id']}")
            print(f"   Package Key: {pkg['package_key']}")
            print(f"   Status: {pkg['status']}")
            print()

            print(f"Trying to get traffic info...")
            info = api.get_package_info(pkg['package_key'])

            if info:
                print("✅ SUCCESS!")
                print(json.dumps(info, indent=2, ensure_ascii=False))

                if 'traffic' in info:
                    traffic = info['traffic']
                    used = traffic['usage']
                    limit = traffic['limit']
                    left = limit - used
                    percent = round((used / limit * 100), 2)

                    print()
                    print("="*60)
                    print("📊 TRAFFIC STATISTICS")
                    print("="*60)
                    print(f"Limit:   {limit} GB")
                    print(f"Used:    {used} GB ({percent}%)")
                    print(f"Left:    {left} GB")
                    print("="*60)
            else:
                print("❌ Failed to get traffic info")

            print()
