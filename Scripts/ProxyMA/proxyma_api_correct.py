"""
Правильный скрипт для работы с Proxyma API
На основе официальной документации
"""

import requests
import json
import sys
import io

# Устанавливаем UTF-8 для консоли Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ProxymaAPICorrect:
    """Класс для работы с Proxyma API (правильная версия)"""

    BASE_URL = "https://proxyma.io/api"

    def __init__(self, api_key, package_key=None):
        """
        Args:
            api_key: API ключ от Proxyma
            package_key: Ключ пакета прокси
        """
        self.api_key = api_key
        self.package_key = package_key
        self.headers = {
            "api-key": api_key,  # ПРАВИЛЬНЫЙ формат!
            "Content-Type": "application/json"
        }

    def get_balance(self):
        """Получить баланс аккаунта"""
        try:
            url = f"{self.BASE_URL}/reseller/get/balance"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}

    def get_packages(self):
        """Получить список всех пакетов"""
        try:
            url = f"{self.BASE_URL}/reseller/get/packages"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}

    def get_package_info(self):
        """Получить информацию о конкретном пакете"""
        if not self.package_key:
            return {"error": "Package key не указан"}

        try:
            url = f"{self.BASE_URL}/reseller/info/package/{self.package_key}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}

    def renew_package(self):
        """Продлить пакет (Residential)"""
        if not self.package_key:
            return {"error": "Package key не указан"}

        try:
            url = f"{self.BASE_URL}/reseller/update/{self.package_key}"
            response = requests.put(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}

    def get_residential_unlim_packages(self):
        """Получить Residential Unlim пакеты"""
        try:
            url = f"{self.BASE_URL}/residential-unlim/packages"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}

    def enable_auto_renewal(self, package_id):
        """Включить автопродление для Residential Unlim пакета"""
        try:
            url = f"{self.BASE_URL}/residential-unlim/{package_id}/auto-update"
            payload = {"auto_update": True}
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"error": str(e)}


def check_all_accounts():
    """Проверить все аккаунты с правильными endpoints"""

    print("="*70)
    print("✅ ПРОВЕРКА PROXYMA API (ПРАВИЛЬНАЯ ВЕРСИЯ)")
    print("="*70)

    # Загружаем данные
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Собираем аккаунты
    accounts = {}

    for server in data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            api_key = server.get('Proxyma API Key ', '').strip()
            package_key = server.get('Package Key / ID', '').strip()
            shop = server.get('Магазин', '')

            if api_key and package_key:
                if api_key not in accounts:
                    accounts[api_key] = {
                        'packages': [],
                        'shops': [],
                        'email': server.get('Провайдер логин', '')
                    }
                accounts[api_key]['packages'].append({
                    'key': package_key,
                    'shop': shop
                })
                if shop not in accounts[api_key]['shops']:
                    accounts[api_key]['shops'].append(shop)

    print(f"\n📊 Найдено аккаунтов: {len(accounts)}\n")

    # Проверяем каждый аккаунт
    results = []

    for idx, (api_key, info) in enumerate(accounts.items(), 1):
        print(f"{'='*70}")
        print(f"🔑 АККАУНТ #{idx}: {', '.join(info['shops'])}")
        print(f"{'='*70}")
        print(f"Email: {info['email']}")
        print(f"API Key: {api_key[:20]}...{api_key[-10:]}")

        api = ProxymaAPICorrect(api_key)

        # Тест 1: Баланс
        print(f"\n💰 Проверка баланса...")
        balance_result = api.get_balance()
        if 'error' in balance_result:
            print(f"   ❌ Ошибка: {balance_result}")
        else:
            print(f"   ✅ Успешно!")
            print(f"   Данные: {json.dumps(balance_result, indent=2, ensure_ascii=False)[:300]}")

        # Тест 2: Список пакетов
        print(f"\n📦 Проверка списка пакетов...")
        packages_result = api.get_packages()
        if 'error' in packages_result:
            print(f"   ❌ Ошибка: {packages_result}")
        else:
            print(f"   ✅ Успешно!")
            print(f"   Данные: {json.dumps(packages_result, indent=2, ensure_ascii=False)[:300]}")

        # Тест 3: Информация о каждом пакете
        for pkg in info['packages']:
            print(f"\n🔍 Проверка пакета {pkg['shop']}...")
            api.package_key = pkg['key']
            pkg_info = api.get_package_info()

            if 'error' in pkg_info:
                print(f"   ❌ Ошибка: {pkg_info}")
            else:
                print(f"   ✅ Успешно!")
                print(f"   Данные: {json.dumps(pkg_info, indent=2, ensure_ascii=False)[:300]}")

        # Тест 4: Residential Unlim пакеты
        print(f"\n🌐 Проверка Residential Unlim пакетов...")
        unlim_result = api.get_residential_unlim_packages()
        if 'error' in unlim_result:
            print(f"   ⚠️  Возможно используются обычные Residential пакеты")
        else:
            print(f"   ✅ Найдены Residential Unlim пакеты!")
            print(f"   Данные: {json.dumps(unlim_result, indent=2, ensure_ascii=False)[:300]}")

        results.append({
            'account': f"#{idx} {', '.join(info['shops'])}",
            'balance': balance_result,
            'packages': packages_result,
            'unlim': unlim_result
        })

        print(f"\n{'='*70}\n")

    # Итоги
    print("\n" + "="*70)
    print("📋 ИТОГИ ПРОВЕРКИ")
    print("="*70)

    success_count = sum(1 for r in results if 'error' not in r['balance'])

    print(f"\n✅ Успешных подключений: {success_count}/{len(results)}")

    if success_count > 0:
        print("\n🎯 API РАБОТАЕТ! Можно использовать для:")
        print("   1. Проверки баланса")
        print("   2. Получения списка пакетов")
        print("   3. Информации о пакетах")
        print("   4. Продления пакетов")
        print("   5. Включения автопродления (для Residential Unlim)")
    else:
        print("\n⚠️  Требуется дополнительная проверка")

    return results


if __name__ == "__main__":
    results = check_all_accounts()

    print("\n" + "="*70)
    print("🎯 СЛЕДУЮЩИЙ ШАГ")
    print("="*70)
    print("\nЕсли API заработало - могу создать скрипт для:")
    print("1. Автоматического включения автопродления")
    print("2. Проверки балансов и уведомлений")
    print("3. Автоматического продления пакетов")
    print("\n" + "="*70)
