#!/usr/bin/env python3
"""
Proxyma API - Get Traffic Statistics
Using working approach from VPS code
"""
import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ProxymaAPI:
    """Proxyma API handler for Dynamic proxies"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }

    def get_package_info(self, proxy_key):
        """
        Get package info including traffic statistics

        Args:
            proxy_key: Package key (e.g., '1fb08611c4d557ac8f22')

        Returns:
            dict with traffic info or None
        """
        # Get all packages first
        url = "https://api.proxyma.io/api/residential/packages"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                packages = data.get('packages', [])

                # Find package by key
                for pkg in packages:
                    if pkg.get('package_key') == proxy_key:
                        # Format to match expected structure
                        return {
                            'status': pkg.get('status'),
                            'created_at': pkg.get('created_at'),
                            'expired_at': pkg.get('expired_at'),
                            'days_left': pkg.get('days_left'),
                            'traffic': {
                                'limit': pkg['tariff'].get('traffic', 0),
                                'usage': 0  # API doesn't provide usage for Dynamic proxies
                            }
                        }

                print(f"⚠️ Package {proxy_key} not found in list")
                return None
            else:
                print(f"❌ API returned HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None


# Main execution
print("="*80)
print("🚀 PROXYMA TRAFFIC CHECK - Using Working Method")
print("="*80)
print()

# Load data
with open('servers_data.json', 'r', encoding='utf-8') as f:
    table = json.load(f)

# Get API keys
email_to_data = {}
for server in table['data']:
    if server.get('Провайдер') == 'proxyma':
        email = server.get('Провайдер логин', '').strip()
        api_key = server.get('Proxyma API Key ', '').strip()
        package_key = server.get('Package Key proxyma', '').strip()
        shop = server.get('Магазин', '')

        if email and api_key and package_key and email not in email_to_data:
            email_to_data[email] = {
                'api_key': api_key,
                'package_key': package_key,
                'shop': shop
            }

# Check HUB
hub_email = 'johnwicw12@gmail.com'
if hub_email in email_to_data:
    data = email_to_data[hub_email]

    print(f"🔑 {data['shop']} Account")
    print(f"Email: {hub_email}")
    print(f"Package Key: {data['package_key']}")
    print()

    # Use ProxymaAPI class
    proxyma = ProxymaAPI(data['api_key'])

    print("Getting package info...")
    info = proxyma.get_package_info(data['package_key'])

    if info:
        print("✅ SUCCESS!")
        print()
        print(json.dumps(info, indent=2, ensure_ascii=False))
        print()

        # Format like VPS code
        proxy_data = {
            'proxyLimit': info['traffic']['limit'],
            'proxyUsed': round(info['traffic']['usage'], 2),
            'proxyLeft': round(info['traffic']['limit'] - info['traffic']['usage'], 2),
            'proxyExpires': info['expired_at']
        }

        print("="*60)
        print("📊 FORMATTED DATA")
        print("="*60)
        print(f"Proxy Limit:   {proxy_data['proxyLimit']} GB")
        print(f"Proxy Used:    {proxy_data['proxyUsed']} GB")
        print(f"Proxy Left:    {proxy_data['proxyLeft']} GB")
        print(f"Expires:       {proxy_data['proxyExpires']}")
        print("="*60)
    else:
        print("❌ Failed to get package info")
