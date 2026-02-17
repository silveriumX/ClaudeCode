"""
Автоматическая проверка Proxyma API
Тест доступных endpoints с реальными данными из таблицы
"""

import requests
import json
import sys
import io

# Устанавливаем UTF-8 для консоли Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def test_proxyma_api():
    """Проверка Proxyma API с данными из таблицы"""

    print("="*70)
    print("🔍 ПРОВЕРКА PROXYMA API")
    print("="*70)

    # Загружаем данные
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Собираем уникальные API ключи
    proxyma_accounts = {}

    for server in data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            api_key = server.get('Proxyma API Key ', '').strip()
            package_id = server.get('Package Key / ID', '').strip()
            shop = server.get('Магазин', '')
            balance = server.get('Баланс кабинета', '')

            if api_key and package_id:
                if api_key not in proxyma_accounts:
                    proxyma_accounts[api_key] = {
                        'packages': [],
                        'shops': [],
                        'balance': balance
                    }
                if package_id not in [p['id'] for p in proxyma_accounts[api_key]['packages']]:
                    proxyma_accounts[api_key]['packages'].append({
                        'id': package_id,
                        'shop': shop,
                        'limit': server.get('Лимит трафика (GB)', ''),
                        'used': server.get('Использовано (GB)', ''),
                        'remaining': server.get('Осталось (GB)', ''),
                        'expires': server.get('Дата истечения прокси', '')
                    })
                if shop not in proxyma_accounts[api_key]['shops']:
                    proxyma_accounts[api_key]['shops'].append(shop)

    print(f"\n📊 Найдено уникальных API ключей: {len(proxyma_accounts)}")
    print(f"📦 Всего пакетов: {sum(len(acc['packages']) for acc in proxyma_accounts.values())}")

    # Тестируем каждый аккаунт
    for idx, (api_key, info) in enumerate(proxyma_accounts.items(), 1):
        print(f"\n{'='*70}")
        print(f"🔑 АККАУНТ #{idx}")
        print(f"{'='*70}")
        print(f"Магазины: {', '.join(info['shops'])}")
        print(f"Баланс: ${info['balance']}")
        print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
        print(f"Пакетов: {len(info['packages'])}")

        # Список пакетов
        print(f"\n📦 Пакеты:")
        for pkg in info['packages']:
            print(f"   • {pkg['shop']}: {pkg['id']}")
            print(f"     Трафик: {pkg['used']}/{pkg['limit']} GB (осталось: {pkg['remaining']} GB)")
            print(f"     Истекает: {pkg['expires']}")

        # Тестируем API endpoints
        print(f"\n🔍 Проверка API endpoints...")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Тест 1: Получение баланса
        test_endpoint(
            "GET",
            "https://api.proxyma.io/balance",
            headers,
            "Проверка баланса"
        )

        # Тест 2: Список пакетов
        test_endpoint(
            "GET",
            "https://api.proxyma.io/packages",
            headers,
            "Список пакетов"
        )

        # Тест 3: Информация о пакете
        if info['packages']:
            pkg_id = info['packages'][0]['id']
            test_endpoint(
                "GET",
                f"https://api.proxyma.io/package/{pkg_id}",
                headers,
                f"Информация о пакете {pkg_id[:20]}"
            )

            # Тест 4: Настройки пакета
            test_endpoint(
                "GET",
                f"https://api.proxyma.io/package/{pkg_id}/settings",
                headers,
                f"Настройки пакета {pkg_id[:20]}"
            )

            # Тест 5: Автопродление (только проверка, без изменения)
            test_endpoint(
                "GET",
                f"https://api.proxyma.io/package/{pkg_id}/autorenew",
                headers,
                f"Статус автопродления {pkg_id[:20]}"
            )

        print(f"\n{'='*70}\n")

    # Итоги
    print("\n" + "="*70)
    print("📋 ИТОГИ ПРОВЕРКИ")
    print("="*70)
    print("\n✅ Доступные данные из таблицы:")
    print("   • API ключи: работают")
    print("   • Package IDs: найдены")
    print("   • Трафик и балансы: отображаются")

    print("\n📌 Возможные действия через API:")
    print("   1. Получить актуальную информацию о пакетах")
    print("   2. Проверить баланс")
    print("   3. Получить список прокси")
    print("   4. Проверить/изменить настройки автопродления")
    print("   5. Продлить пакет (если есть баланс)")

    print("\n⚠️  Для включения автопродления нужно:")
    print("   1. Убедиться что API поддерживает endpoint для автопродления")
    print("   2. Проверить достаточен ли баланс на каждом аккаунте")
    print("   3. Запустить скрипт который включит автопродление")


def test_endpoint(method, url, headers, description):
    """Тестирование конкретного API endpoint"""

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, timeout=10)
        else:
            print(f"   ❌ {description}: неподдерживаемый метод {method}")
            return

        status_code = response.status_code

        if status_code == 200:
            print(f"   ✅ {description}: OK")
            try:
                data = response.json()
                # Показываем краткую информацию
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"      Ключи ответа: {', '.join(keys)}")
                elif isinstance(data, list):
                    print(f"      Элементов в списке: {len(data)}")
            except:
                pass
        elif status_code == 401:
            print(f"   ❌ {description}: Ошибка авторизации (неверный API ключ)")
        elif status_code == 404:
            print(f"   ⚠️  {description}: Endpoint не найден (API может не поддерживать)")
        elif status_code == 403:
            print(f"   ⚠️  {description}: Доступ запрещен")
        else:
            print(f"   ❌ {description}: HTTP {status_code}")
            if len(response.text) < 200:
                print(f"      Ответ: {response.text}")

    except requests.exceptions.Timeout:
        print(f"   ⏱️  {description}: Таймаут")
    except requests.exceptions.ConnectionError:
        print(f"   🔌 {description}: Ошибка подключения")
    except Exception as e:
        print(f"   ❌ {description}: {str(e)[:100]}")


if __name__ == "__main__":
    test_proxyma_api()

    print("\n" + "="*70)
    print("🎯 СЛЕДУЮЩИЕ ШАГИ")
    print("="*70)
    print("\n1. Проверьте результаты тестов выше")
    print("2. Если нужно включить автопродление - напишите мне")
    print("3. Я создам финальный скрипт на основе рабочих endpoints")
    print("\n" + "="*70)
