"""
Получение данных с Proxyma API используя рабочий подход из вашей системы
"""
import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_proxyma_data(api_key):
    """Получить данные с Proxyma API"""

    base_url = "https://proxyma.io/api/residential-unlim"
    headers = {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

    results = {}

    # 1. Получаем список всех пакетов
    print(f"📦 Получаю список пакетов...")
    try:
        response = requests.get(
            f"{base_url}/packages",
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            packages = data.get('packages', [])
            print(f"✅ Получено пакетов: {len(packages)}")
            results['packages'] = packages

            # Для каждого пакета получаем детали
            for pkg in packages:
                pkg_id = pkg.get('id')
                print(f"\n🔍 Пакет ID {pkg_id}:")
                print(f"   Название: {pkg.get('name')}")
                print(f"   Статус: {pkg.get('status')}")
                print(f"   Цена: {pkg.get('price')}")
                print(f"   Дата создания: {pkg.get('created_at')}")

                # Получаем usage
                usage_response = requests.get(
                    f"{base_url}/{pkg_id}/usage",
                    headers=headers,
                    timeout=30
                )

                if usage_response.status_code == 200:
                    usage = usage_response.json()
                    print(f"   Usage: {json.dumps(usage, ensure_ascii=False)[:200]}")
                    pkg['usage'] = usage

        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"Ответ: {response.text[:500]}")
            return None

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

    # 2. Получаем доступные локации
    print(f"\n🌍 Получаю локации...")
    try:
        response = requests.get(
            f"{base_url}/locations",
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            locations = data.get('data', [])
            print(f"✅ Локаций: {len(locations) if isinstance(locations, list) else 'N/A'}")
            results['locations'] = locations
    except Exception as e:
        print(f"⚠️  Локации: {e}")

    # 3. Получаем страны
    print(f"\n🗺️  Получаю страны...")
    try:
        response = requests.get(
            f"{base_url}/countries",
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            countries = data.get('data', [])
            print(f"✅ Стран: {len(countries) if isinstance(countries, list) else 'N/A'}")
            results['countries'] = countries
    except Exception as e:
        print(f"⚠️  Страны: {e}")

    return results


def main():
    """Получить данные для всех аккаунтов"""

    print("="*70)
    print("🚀 ПОЛУЧЕНИЕ ДАННЫХ С PROXYMA API")
    print("="*70)

    # Загружаем данные из таблицы
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            table_data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Собираем уникальные API ключи
    api_keys = {}

    for server in table_data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            api_key = server.get('Proxyma API Key ', '').strip()
            shop = server.get('Магазин', '')
            email = server.get('Провайдер логин', '')
            balance = server.get('Баланс кабинета', '')

            if api_key and api_key not in api_keys:
                api_keys[api_key] = {
                    'shops': [],
                    'email': email,
                    'balance': balance
                }

            if api_key and shop not in api_keys[api_key]['shops']:
                api_keys[api_key]['shops'].append(shop)

    print(f"\n📊 Найдено уникальных API ключей: {len(api_keys)}\n")

    all_results = {}

    # Получаем данные для каждого аккаунта
    for idx, (api_key, info) in enumerate(api_keys.items(), 1):
        print(f"\n{'='*70}")
        print(f"🔑 АККАУНТ #{idx}: {', '.join(info['shops'])}")
        print(f"{'='*70}")
        print(f"Email: {info['email']}")
        print(f"Баланс (из таблицы): ${info['balance']}")
        print(f"API Key: {api_key[:20]}...{api_key[-10:]}")

        results = get_proxyma_data(api_key)

        if results:
            all_results[info['email']] = {
                'shops': info['shops'],
                'api_key': api_key[:20] + '...',
                'data': results
            }
            print(f"\n✅ Данные успешно получены!")
        else:
            print(f"\n❌ Не удалось получить данные")

        print(f"\n{'='*70}\n")

    # Сохраняем результаты
    if all_results:
        with open('proxyma_api_results.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        print("\n" + "="*70)
        print("💾 РЕЗУЛЬТАТЫ СОХРАНЕНЫ")
        print("="*70)
        print(f"\nФайл: proxyma_api_results.json")
        print(f"Аккаунтов обработано: {len(all_results)}")

        # Статистика
        total_packages = sum(
            len(acc['data'].get('packages', []))
            for acc in all_results.values()
        )
        print(f"Всего пакетов найдено: {total_packages}")

        # Показываем краткую сводку
        print("\n📊 СВОДКА ПО АККАУНТАМ:")
        for email, acc in all_results.items():
            packages = acc['data'].get('packages', [])
            print(f"\n  {', '.join(acc['shops'])} ({email})")
            print(f"    Пакетов: {len(packages)}")
            for pkg in packages:
                print(f"      • {pkg.get('name')} - {pkg.get('status')}")
    else:
        print("\n❌ Не удалось получить данные ни для одного аккаунта")
        print("\nВозможные причины:")
        print("1. API ключи неактивны или неверные")
        print("2. Пакеты не Residential Unlim типа")
        print("3. API endpoint изменился")


if __name__ == "__main__":
    main()
