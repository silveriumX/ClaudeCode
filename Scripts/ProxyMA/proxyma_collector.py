#!/usr/bin/env python3
"""
Proxyma API Data Collector
Получает данные со всех аккаунтов Proxyma через API
БЕЗ браузера, только через API keys
"""
import requests
import json
import sys
import io
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_proxyma_data(api_key, email, shop):
    """Получить данные аккаунта Proxyma через API"""

    headers = {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

    result = {
        'email': email,
        'shop': shop,
        'success': False
    }

    try:
        # 1. Get profile (balance)
        profile_response = requests.get(
            'https://api.proxyma.io/api/profile',
            headers=headers,
            timeout=30
        )

        if profile_response.status_code == 200:
            profile = profile_response.json()
            result['balance'] = profile['user']['balance']
            result['profile'] = profile['user']
        else:
            result['error'] = f"Profile API returned {profile_response.status_code}"
            return result

        # 2. Get Dynamic packages
        packages_response = requests.get(
            'https://api.proxyma.io/api/residential/packages',
            headers=headers,
            timeout=30
        )

        if packages_response.status_code == 200:
            data = packages_response.json()
            result['packages'] = data.get('packages', [])
            result['success'] = True
        else:
            result['error'] = f"Packages API returned {packages_response.status_code}"
            return result

    except Exception as e:
        result['error'] = str(e)
        return result

    return result


def main():
    """Получить данные для всех Proxyma аккаунтов"""

    print("="*80)
    print("🚀 PROXYMA API - ПОЛУЧЕНИЕ ДАННЫХ")
    print("="*80)
    print()

    # Load data from table
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            table_data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Collect unique API keys
    accounts = {}

    for server in table_data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            api_key = server.get('Proxyma API Key ', '').strip()
            shop = server.get('Магазин', '')
            email = server.get('Провайдер логин', '')

            if api_key and api_key not in accounts:
                accounts[api_key] = {
                    'email': email,
                    'shops': [shop]
                }
            elif api_key and shop not in accounts[api_key]['shops']:
                accounts[api_key]['shops'].append(shop)

    print(f"📊 Найдено аккаунтов: {len(accounts)}\n")

    all_results = {}

    # Get data for each account
    for idx, (api_key, info) in enumerate(accounts.items(), 1):
        shops_str = ', '.join(info['shops'])
        print(f"{'='*80}")
        print(f"🔑 АККАУНТ #{idx}: {shops_str}")
        print(f"{'='*80}")
        print(f"Email: {info['email']}")
        print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
        print()

        result = get_proxyma_data(api_key, info['email'], shops_str)

        if result['success']:
            print(f"✅ Данные получены!")
            print(f"\n💰 Баланс: ${result['balance']}")
            print(f"\n📦 Пакетов: {len(result['packages'])}")

            for pkg in result['packages']:
                print(f"\n  🔹 {pkg['tariff']['title']}")
                print(f"     ID: {pkg['id']}")
                print(f"     Package Key: {pkg['package_key']}")
                print(f"     Статус: {pkg['status']}")
                print(f"     Трафик: {pkg['tariff']['traffic']} GB")
                print(f"     Цена: ${pkg['tariff']['price']}")
                print(f"     Дата истечения: {pkg['expired_at']} ({pkg['days_left']} дней)")
                print(f"     Автопродление: {'✅ ON' if pkg['auto_update'] else '❌ OFF'}")
                print(f"     Продлений: {pkg['renew']}")

            all_results[info['email']] = result
        else:
            print(f"❌ Ошибка: {result.get('error', 'Unknown error')}")

        print(f"\n{'='*80}\n")

    # Save results
    if all_results:
        output_file = 'proxyma_data_complete.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        print("\n" + "="*80)
        print("💾 РЕЗУЛЬТАТЫ СОХРАНЕНЫ")
        print("="*80)
        print(f"\nФайл: {output_file}")
        print(f"Аккаунтов обработано: {len(all_results)}")

        # Summary
        total_packages = sum(len(acc['packages']) for acc in all_results.values())
        total_balance = sum(acc['balance'] for acc in all_results.values())

        print(f"Всего пакетов: {total_packages}")
        print(f"Общий баланс: ${total_balance}")

        # Packages needing attention
        print("\n⚠️  ВНИМАНИЕ:")
        for email, acc in all_results.items():
            for pkg in acc['packages']:
                if pkg['days_left'] < 7:
                    print(f"  • {acc['shop']}: Пакет истекает через {pkg['days_left']} дней!")
                if not pkg['auto_update']:
                    print(f"  • {acc['shop']}: Автопродление ВЫКЛЮЧЕНО для пакета {pkg['id']}!")
    else:
        print("\n❌ Не удалось получить данные ни для одного аккаунта")


if __name__ == "__main__":
    main()
