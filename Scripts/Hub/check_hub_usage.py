import json

with open('proxyma_data_complete.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

hub_data = data.get('johnwicw12@gmail.com')

if hub_data:
    print("HUB Account - Traffic Usage")
    print("="*60)
    print(f"Balance: ${hub_data['balance']}")
    print(f"\nPackages: {len(hub_data['packages'])}")

    for pkg in hub_data['packages']:
        print(f"\n{'='*60}")
        print(f"Package ID: {pkg['id']}")
        print(f"Name: {pkg['tariff']['title']}")
        print(f"Status: {pkg['status']}")
        print(f"Package Key: {pkg['package_key']}")

        # Traffic info
        print(f"\nTraffic Limit: {pkg['tariff']['traffic']} GB")
        print(f"Price: ${pkg['tariff']['price']}")
        print(f"Price per GB: ${pkg['tariff']['per_gb']}")

        # Check for usage fields
        print(f"\nAll available fields:")
        for key, value in pkg.items():
            if key not in ['user', 'tariff']:
                print(f"  {key}: {value}")
