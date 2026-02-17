"""
Тестирование различных вариантов Proxyma API endpoints
Для обычных пользовательских аккаунтов (не reseller)
"""

import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def test_various_endpoints(api_key, package_key):
    """Тестирование различных возможных endpoints"""

    print(f"\n{'='*70}")
    print(f"🔍 ТЕСТИРОВАНИЕ ENDPOINTS")
    print(f"{'='*70}")
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
    print(f"Package: {package_key}\n")

    # Варианты заголовков
    headers_variants = [
        {"api-key": api_key, "Content-Type": "application/json"},
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        {"X-API-Key": api_key, "Content-Type": "application/json"},
    ]

    # Варианты базовых URL
    base_urls = [
        "https://proxyma.io/api",
        "https://api.proxyma.io",
        "https://cabinet.proxyma.io/api",
    ]

    # Варианты endpoints для обычных пользователей
    endpoints_to_test = [
        # Баланс
        ("/balance", "GET", "Баланс аккаунта"),
        ("/user/balance", "GET", "Баланс пользователя"),
        ("/account/balance", "GET", "Баланс через account"),

        # Пакеты
        ("/packages", "GET", "Список пакетов"),
        ("/user/packages", "GET", "Пакеты пользователя"),
        (f"/packages/{package_key}", "GET", "Информация о пакете"),
        (f"/package/{package_key}", "GET", "Пакет (singular)"),

        # Residential Unlim (из документации)
        ("/residential-unlim/packages", "GET", "Residential Unlim пакеты"),
        (f"/residential-unlim/packages/{package_key}", "GET", "Residential Unlim пакет"),

        # Профиль пользователя
        ("/profile", "GET", "Профиль"),
        ("/user", "GET", "Данные пользователя"),
        ("/account", "GET", "Аккаунт"),
    ]

    results = []

    for base_url in base_urls:
        for headers_var_idx, headers in enumerate(headers_variants):
            header_type = ["api-key", "Bearer", "X-API-Key"][headers_var_idx]

            for endpoint, method, description in endpoints_to_test:
                url = f"{base_url}{endpoint}"

                try:
                    if method == "GET":
                        response = requests.get(url, headers=headers, timeout=5)
                    else:
                        response = requests.post(url, headers=headers, timeout=5)

                    status = response.status_code

                    # Пропускаем очевидные 404
                    if status == 404:
                        continue

                    result = {
                        'url': url,
                        'header_type': header_type,
                        'status': status,
                        'description': description
                    }

                    if status == 200:
                        try:
                            result['data'] = response.json()
                        except:
                            result['data'] = response.text[:200]

                        print(f"✅ {description}")
                        print(f"   URL: {url}")
                        print(f"   Headers: {header_type}")
                        print(f"   Status: {status}")
                        print(f"   Ответ: {json.dumps(result['data'], indent=2, ensure_ascii=False)[:300]}\n")

                        results.append(result)

                    elif status == 401:
                        print(f"🔐 {description} - Требуется авторизация (401)")
                        print(f"   URL: {url}")
                        print(f"   Headers: {header_type}\n")

                    elif status != 404:
                        print(f"⚠️  {description} - HTTP {status}")
                        print(f"   URL: {url}")
                        print(f"   Headers: {header_type}")
                        print(f"   Ответ: {response.text[:200]}\n")

                except requests.exceptions.Timeout:
                    continue
                except Exception as e:
                    continue

    return results


def main():
    """Тестирование с реальными данными"""

    print("="*70)
    print("🔍 ПОИСК ПРАВИЛЬНЫХ ENDPOINTS ДЛЯ ОБЫЧНЫХ АККАУНТОВ")
    print("="*70)

    # Загружаем данные
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Берем первый аккаунт для теста
    for server in data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            api_key = server.get('Proxyma API Key ', '').strip()
            package_key = server.get('Package Key / ID', '').strip()
            shop = server.get('Магазин', '')

            if api_key and package_key:
                print(f"\n📦 Тестирую аккаунт: {shop}")
                results = test_various_endpoints(api_key, package_key)

                if results:
                    print("\n" + "="*70)
                    print("🎉 НАЙДЕНЫ РАБОЧИЕ ENDPOINTS!")
                    print("="*70)
                    for r in results:
                        print(f"\n✅ {r['description']}")
                        print(f"   URL: {r['url']}")
                        print(f"   Header: {r['header_type']}")
                else:
                    print("\n" + "="*70)
                    print("❌ Рабочие endpoints не найдены")
                    print("="*70)
                    print("\nВозможные причины:")
                    print("1. API ключи в таблице неактивны")
                    print("2. Нужна другая авторизация (токен из кабинета)")
                    print("3. API доступ нужно активировать в настройках")

                break  # Тестируем только первый аккаунт

    print("\n" + "="*70)
    print("💡 РЕКОМЕНДАЦИЯ")
    print("="*70)
    print("\nЕсли рабочие endpoints не найдены:")
    print("1. Зайдите в кабинет Proxyma")
    print("2. Найдите раздел 'API' или 'Настройки'")
    print("3. Проверьте есть ли там документация или примеры")
    print("4. Возможно нужно сгенерировать новый API токен")


if __name__ == "__main__":
    main()
