#!/usr/bin/env python3
"""
Proxyma API with Login Flow
Get traffic stats through session-based authentication
"""
import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def login_and_get_traffic(email, password, package_key):
    """Login to Proxyma and get traffic stats"""

    session = requests.Session()

    # Step 1: Login
    print(f"🔐 Logging in as {email}...")
    login_url = "https://api.proxyma.io/api/userlogin"
    login_data = {
        "email": email,
        "password": password
    }

    try:
        login_response = session.post(login_url, json=login_data, timeout=30)

        if login_response.status_code == 200:
            print("✅ Login successful!")
            login_result = login_response.json()
            print(f"   User: {login_result.get('user', {}).get('name', 'N/A')}")
        else:
            print(f"❌ Login failed: HTTP {login_response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

    # Step 2: Get package info with session
    print(f"\n📦 Getting package info for {package_key}...")

    # Try different endpoints with session
    endpoints = [
        f"https://cabinet.proxyma.io/reseller/info/package/{package_key}",
        f"https://api.proxyma.io/reseller/info/package/{package_key}",
        f"https://cabinet.proxyma.io/api/reseller/info/package/{package_key}",
        f"https://api.proxyma.io/api/reseller/info/package/{package_key}"
    ]

    for endpoint in endpoints:
        try:
            response = session.get(endpoint, timeout=30)

            if response.status_code == 200:
                # Check if it's JSON
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    print(f"✅ SUCCESS with endpoint: {endpoint}")
                    data = response.json()
                    return data
                else:
                    print(f"⚠️  {endpoint}: Got HTML, not JSON")
            else:
                print(f"❌ {endpoint}: HTTP {response.status_code}")

        except Exception as e:
            print(f"❌ {endpoint}: {e}")

    return None


# Test with HUB account
print("="*80)
print("🔍 PROXYMA API - LOGIN FLOW TEST")
print("="*80)
print()

# Load credentials
with open('servers_data.json', 'r', encoding='utf-8') as f:
    table = json.load(f)

# Find HUB credentials
for server in table['data']:
    if server.get('Магазин') == 'HUB' and server.get('Провайдер') == 'proxyma':
        email = server.get('Провайдер логин', '').strip()
        password = server.get('Провайдер пароль', '').strip()
        package_key = server.get('Package Key proxyma', '').strip()

        if email and password and package_key:
            print(f"Testing with HUB account")
            print(f"Email: {email}")
            print(f"Package Key: {package_key}")
            print()

            result = login_and_get_traffic(email, password, package_key)

            if result and 'traffic' in result:
                traffic = result['traffic']
                print()
                print("="*60)
                print("📊 TRAFFIC STATISTICS")
                print("="*60)
                print(f"Limit:   {traffic['limit']} GB")
                print(f"Used:    {traffic['usage']} GB")
                print(f"Left:    {traffic['limit'] - traffic['usage']} GB")
                print("="*60)
            elif result:
                print()
                print("✅ Got response but no traffic data:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print()
                print("❌ Failed to get traffic info")

            break
