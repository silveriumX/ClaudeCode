"""
Попытка авторизации через API и получения данных
Будем пробовать разные способы аутентификации
"""

import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def try_login_api(email, password):
    """Попытка авторизации через API для получения токена"""

    print(f"\n🔐 Попытка авторизации: {email}")

    # Возможные endpoints для логина
    login_endpoints = [
        "https://cabinet.proxyma.io/api/login",
        "https://cabinet.proxyma.io/api/auth/login",
        "https://cabinet.proxyma.io/api/user/login",
        "https://proxyma.io/api/login",
        "https://api.proxyma.io/login",
    ]

    for endpoint in login_endpoints:
        try:
            # Пробуем POST с credentials
            payload = {
                "email": email,
                "password": password
            }

            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ Успех! Endpoint: {endpoint}")
                    print(f"Ответ: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                    return data
                except:
                    # Если не JSON, проверяем что не HTML
                    if not response.text.startswith('<!DOCTYPE'):
                        print(f"✅ Успех! Endpoint: {endpoint}")
                        print(f"Ответ: {response.text[:500]}")
                        return response.text

        except Exception as e:
            continue

    print("❌ Не удалось авторизоваться через API")
    return None


def try_api_with_key_variations(api_key, package_key):
    """Пробуем разные варианты использования API ключа"""

    print(f"\n🔑 Тестирование API ключа: {api_key[:20]}...")

    # Базовый URL
    base_url = "https://cabinet.proxyma.io/api"

    # Разные варианты передачи ключа
    auth_methods = [
        # Вариант 1: В заголовке api-key
        {
            "headers": {"api-key": api_key, "Content-Type": "application/json"},
            "params": {},
            "name": "api-key header"
        },
        # Вариант 2: В параметрах URL
        {
            "headers": {"Content-Type": "application/json"},
            "params": {"api_key": api_key},
            "name": "api_key param"
        },
        # Вариант 3: В параметрах URL (другое название)
        {
            "headers": {"Content-Type": "application/json"},
            "params": {"key": api_key},
            "name": "key param"
        },
        # Вариант 4: Bearer токен
        {
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "params": {},
            "name": "Bearer token"
        },
        # Вариант 5: Basic auth с ключом
        {
            "headers": {"Content-Type": "application/json"},
            "params": {},
            "auth": (api_key, ""),
            "name": "Basic auth"
        },
    ]

    endpoints_to_check = [
        "/balance",
        "/packages",
        f"/package/{package_key}",
    ]

    for auth_method in auth_methods:
        for endpoint in endpoints_to_check:
            try:
                url = f"{base_url}{endpoint}"

                request_kwargs = {
                    "headers": auth_method["headers"],
                    "params": auth_method["params"],
                    "timeout": 10
                }

                if "auth" in auth_method:
                    request_kwargs["auth"] = auth_method["auth"]

                response = requests.get(url, **request_kwargs)

                # Проверяем что это не HTML
                content_type = response.headers.get('Content-Type', '')

                if response.status_code == 200 and 'json' in content_type:
                    print(f"\n✅ УСПЕХ! {endpoint}")
                    print(f"   Метод: {auth_method['name']}")
                    print(f"   URL: {url}")

                    try:
                        data = response.json()
                        print(f"   Данные: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                        return {'endpoint': endpoint, 'method': auth_method, 'data': data}
                    except:
                        print(f"   Ответ: {response.text[:500]}")
                        return {'endpoint': endpoint, 'method': auth_method, 'text': response.text}

            except Exception as e:
                continue

    print("❌ Ни один метод не вернул JSON данные")
    return None


def get_all_accounts_data():
    """Получить данные всех аккаунтов"""

    print("="*70)
    print("🚀 ПОЛУЧЕНИЕ ДАННЫХ ЧЕРЕЗ API")
    print("="*70)

    # Загружаем данные из таблицы
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            table_data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Собираем уникальные аккаунты
    accounts = {}

    for server in table_data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            email = server.get('Провайдер логин', '').strip()
            password = server.get('Провайдер пароль', '').strip()
            api_key = server.get('Proxyma API Key ', '').strip()
            package_key = server.get('Package Key / ID', '').strip()
            shop = server.get('Магазин', '')

            if email not in accounts:
                accounts[email] = {
                    'email': email,
                    'password': password,
                    'api_key': api_key,
                    'packages': [],
                    'shops': []
                }

            if package_key:
                accounts[email]['packages'].append({
                    'key': package_key,
                    'shop': shop
                })
                if shop not in accounts[email]['shops']:
                    accounts[email]['shops'].append(shop)

    print(f"\n📊 Найдено аккаунтов: {len(accounts)}\n")

    results = []

    # Пробуем для каждого аккаунта
    for idx, (email, acc_data) in enumerate(accounts.items(), 1):
        print(f"\n{'='*70}")
        print(f"АККАУНТ #{idx}: {', '.join(acc_data['shops'])}")
        print(f"{'='*70}")
        print(f"Email: {email}")

        # Способ 1: Попытка авторизации через API
        login_result = try_login_api(email, acc_data['password'])

        if login_result:
            # Если получили токен, используем его
            results.append({
                'account': email,
                'shops': acc_data['shops'],
                'method': 'login',
                'data': login_result
            })
        else:
            # Способ 2: Используем API ключ напрямую
            if acc_data['api_key'] and acc_data['packages']:
                api_result = try_api_with_key_variations(
                    acc_data['api_key'],
                    acc_data['packages'][0]['key']
                )

                if api_result:
                    results.append({
                        'account': email,
                        'shops': acc_data['shops'],
                        'method': 'api_key',
                        'data': api_result
                    })

    # Итоги
    print("\n" + "="*70)
    print("📊 ИТОГИ")
    print("="*70)

    if results:
        print(f"\n✅ Успешно получены данные для {len(results)} аккаунтов:")
        for r in results:
            print(f"   • {', '.join(r['shops'])} - метод: {r['method']}")
    else:
        print("\n❌ Не удалось получить данные ни для одного аккаунта")
        print("\nВозможные причины:")
        print("1. API требует дополнительную авторизацию (CSRF токен, cookies)")
        print("2. API ключи предназначены только для proxy-строк, не для REST API")
        print("3. Нужно активировать API доступ в настройках кабинета")

    return results


if __name__ == "__main__":
    results = get_all_accounts_data()

    if not results:
        print("\n" + "="*70)
        print("💡 АЛЬТЕРНАТИВНЫЕ РЕШЕНИЯ")
        print("="*70)
        print("\n1. Проверить в кабинете Proxyma раздел 'API'")
        print("2. Возможно нужно сгенерировать специальный токен")
        print("3. Или использовать другой тип API (GraphQL?)")
        print("\n" + "="*70)
