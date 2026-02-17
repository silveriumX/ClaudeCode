#!/usr/bin/env python3
"""
Proxyma Auto-Renewal Enabler
Включает автопродление для всех пакетов Proxyma
"""
import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def enable_auto_renewal(api_key, package_id):
    """Включить автопродление для пакета"""

    headers = {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

    # Try different possible endpoints
    endpoints = [
        f'https://api.proxyma.io/api/residential/{package_id}/auto-update',
        f'https://api.proxyma.io/api/residential/packages/{package_id}/auto-update',
    ]

    for endpoint in endpoints:
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={'auto_update': 1},  # или True
                timeout=30
            )

            if response.status_code == 200:
                return {'success': True, 'endpoint': endpoint}
            elif response.status_code == 404:
                continue  # Try next endpoint
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'response': response.text[:200]
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    return {'success': False, 'error': 'All endpoints returned 404'}


def main():
    """Включить автопродление для всех пакетов"""

    print("="*80)
    print("🔄 ВКЛЮЧЕНИЕ АВТОПРОДЛЕНИЯ PROXYMA")
    print("="*80)
    print()

    # Load collected data
    try:
        with open('proxyma_data_complete.json', 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл proxyma_data_complete.json не найден")
        print("   Сначала запустите: python proxyma_collector.py")
        return

    # Load API keys mapping
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            table_data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Create email -> api_key mapping
    email_to_key = {}
    for server in table_data['data']:
        if server.get('Провайдер') == 'proxyma':
            email = server.get('Провайдер логин', '').strip()
            api_key = server.get('Proxyma API Key ', '').strip()
            if email and api_key:
                email_to_key[email] = api_key

    total_packages = 0
    enabled_count = 0
    already_on_count = 0
    failed_count = 0

    for email, data in all_data.items():
        if not data.get('success'):
            continue

        api_key = email_to_key.get(email)
        if not api_key:
            print(f"⚠️  {data['shop']}: API key не найден")
            continue

        print(f"\n{'='*80}")
        print(f"🔑 {data['shop']} ({email})")
        print(f"{'='*80}")

        for pkg in data['packages']:
            total_packages += 1
            pkg_id = pkg['id']
            pkg_name = pkg['tariff']['title']
            current_auto = pkg['auto_update']

            print(f"\n  📦 Пакет {pkg_id}: {pkg_name}")
            print(f"     Статус: {pkg['status']}")
            print(f"     Автопродление: {'✅ ON' if current_auto else '❌ OFF'}")

            if current_auto:
                print(f"     ➡️  Уже включено, пропускаем")
                already_on_count += 1
                continue

            if pkg['status'] != 'active':
                print(f"     ⚠️  Пакет неактивен, пропускаем")
                failed_count += 1
                continue

            print(f"     🔄 Включаю автопродление...")

            result = enable_auto_renewal(api_key, pkg_id)

            if result['success']:
                print(f"     ✅ Автопродление ВКЛЮЧЕНО!")
                enabled_count += 1
            else:
                print(f"     ❌ Ошибка: {result['error']}")
                failed_count += 1

    print(f"\n\n{'='*80}")
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print(f"{'='*80}")
    print(f"Всего пакетов обработано: {total_packages}")
    print(f"✅ Автопродление включено: {enabled_count}")
    print(f"⏭️  Уже было включено: {already_on_count}")
    print(f"❌ Ошибок/пропущено: {failed_count}")
    print()

    if enabled_count > 0:
        print("✅ Автопродление успешно включено!")
        print("   Запустите проверку: python proxyma_collector.py")
    elif already_on_count == total_packages:
        print("✅ На всех активных пакетах автопродление уже включено!")
    else:
        print("⚠️  Не удалось включить автопродление")
        print("   Возможно, нужен другой API endpoint")


if __name__ == "__main__":
    main()
