"""
Скрипт для работы с Proxyma API
Проверка возможностей API и управление пакетами прокси
"""

import requests
import json
import sys
import io

# Устанавливаем UTF-8 для консоли Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ProxymaAPI:
    """Класс для работы с Proxyma API"""

    BASE_URL = "https://api.proxyma.io"

    def __init__(self, api_key, package_id=None):
        """
        Args:
            api_key: API ключ от Proxyma
            package_id: ID пакета прокси (опционально)
        """
        self.api_key = api_key
        self.package_id = package_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def get_package_info(self):
        """Получить информацию о пакете"""
        if not self.package_id:
            print("❌ Package ID не указан")
            return None

        try:
            url = f"{self.BASE_URL}/package/{self.package_id}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка получения данных: HTTP {response.status_code}")
                print(f"Ответ: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return None

    def get_packages_list(self):
        """Получить список всех пакетов"""
        try:
            url = f"{self.BASE_URL}/packages"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка получения списка: HTTP {response.status_code}")
                print(f"Ответ: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return None

    def extend_package(self, auto_renew=False):
        """
        Продлить пакет

        Args:
            auto_renew: Включить автопродление (если поддерживается API)
        """
        if not self.package_id:
            print("❌ Package ID не указан")
            return False

        try:
            url = f"{self.BASE_URL}/package/{self.package_id}/extend"
            payload = {
                "auto_renew": auto_renew
            }
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)

            if response.status_code == 200:
                print(f"✅ Пакет {self.package_id} продлён")
                return True
            else:
                print(f"❌ Ошибка продления: HTTP {response.status_code}")
                print(f"Ответ: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return False

    def check_api_endpoints(self):
        """Проверить доступные эндпоинты API"""
        print("\n🔍 Проверка доступных API endpoints...")

        # Список возможных эндпоинтов для проверки
        endpoints = [
            ("/packages", "GET", "Список пакетов"),
            ("/package/{id}", "GET", "Информация о пакете"),
            ("/package/{id}/extend", "POST", "Продление пакета"),
            ("/package/{id}/settings", "GET", "Настройки пакета"),
            ("/package/{id}/settings", "PUT", "Изменение настроек"),
            ("/balance", "GET", "Баланс аккаунта"),
            ("/proxies", "GET", "Список прокси"),
        ]

        print("\n📋 Возможные endpoints:")
        for endpoint, method, description in endpoints:
            print(f"   {method:6} {endpoint:30} - {description}")

        return endpoints


def test_api_with_data_from_table():
    """Тестирование API с данными из таблицы серверов"""

    print("="*70)
    print("🔍 ПРОВЕРКА PROXYMA API")
    print("="*70)

    # Загружаем данные из таблицы
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        print("Запустите сначала: python google_sheets_reader.py")
        return

    # Собираем уникальные API ключи и пакеты
    proxyma_accounts = {}

    for server in data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            api_key = server.get('Proxyma API Key ', '').strip()
            package_id = server.get('Package Key / ID', '').strip()
            shop = server.get('Магазин', '')

            if api_key and package_id:
                if api_key not in proxyma_accounts:
                    proxyma_accounts[api_key] = {
                        'packages': [],
                        'shops': []
                    }
                if package_id not in [p['id'] for p in proxyma_accounts[api_key]['packages']]:
                    proxyma_accounts[api_key]['packages'].append({
                        'id': package_id,
                        'shop': shop
                    })
                if shop not in proxyma_accounts[api_key]['shops']:
                    proxyma_accounts[api_key]['shops'].append(shop)

    print(f"\n📊 Найдено аккаунтов Proxyma: {len(proxyma_accounts)}")

    # Тестируем каждый аккаунт
    for idx, (api_key, info) in enumerate(proxyma_accounts.items(), 1):
        print(f"\n{'='*70}")
        print(f"🔑 Аккаунт {idx} (Магазины: {', '.join(info['shops'])})")
        print(f"{'='*70}")
        print(f"API Key: {api_key[:20]}...")
        print(f"Пакетов: {len(info['packages'])}")

        # Создаем API клиент
        api = ProxymaAPI(api_key)

        # Показываем доступные endpoints
        api.check_api_endpoints()

        # Пробуем получить список пакетов
        print("\n📦 Попытка получить список пакетов...")
        packages = api.get_packages_list()

        if packages:
            print(f"✅ Успешно! Получено данных")
            print(f"Ответ API: {json.dumps(packages, indent=2, ensure_ascii=False)[:500]}...")

        # Проверяем каждый пакет
        for pkg in info['packages']:
            print(f"\n📦 Проверка пакета {pkg['id']} ({pkg['shop']})...")
            api.package_id = pkg['id']
            pkg_info = api.get_package_info()

            if pkg_info:
                print(f"✅ Данные получены!")
                print(f"Информация: {json.dumps(pkg_info, indent=2, ensure_ascii=False)[:300]}...")


def enable_auto_renewal_all():
    """Включить автопродление на всех пакетах"""

    print("="*70)
    print("🔄 ВКЛЮЧЕНИЕ АВТОПРОДЛЕНИЯ НА ВСЕХ ПАКЕТАХ")
    print("="*70)

    # Загружаем данные
    try:
        with open('servers_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл servers_data.json не найден")
        return

    # Собираем пакеты
    packages_to_renew = []

    for server in data['data']:
        provider = server.get('Провайдер', '')
        if provider == 'proxyma':
            api_key = server.get('Proxyma API Key ', '').strip()
            package_id = server.get('Package Key / ID', '').strip()
            shop = server.get('Магазин', '')

            if api_key and package_id:
                packages_to_renew.append({
                    'api_key': api_key,
                    'package_id': package_id,
                    'shop': shop
                })

    print(f"\n📊 Найдено пакетов для автопродления: {len(packages_to_renew)}")

    # Подтверждение
    print("\n⚠️  ВНИМАНИЕ: Эта операция попытается включить автопродление на всех пакетах!")
    confirm = input("Продолжить? (yes/no): ")

    if confirm.lower() != 'yes':
        print("❌ Отменено")
        return

    # Включаем автопродление
    success = 0
    failed = 0

    for pkg in packages_to_renew:
        print(f"\n🔄 {pkg['shop']}: пакет {pkg['package_id'][:20]}...")
        api = ProxymaAPI(pkg['api_key'], pkg['package_id'])

        if api.extend_package(auto_renew=True):
            success += 1
        else:
            failed += 1

    print("\n" + "="*70)
    print(f"✅ Успешно: {success}")
    print(f"❌ Ошибок: {failed}")
    print("="*70)


def main():
    """Главное меню"""

    print("\n" + "="*70)
    print("🔧 PROXYMA API - УПРАВЛЕНИЕ ПАКЕТАМИ")
    print("="*70)
    print("\nВыберите действие:")
    print("1. Проверить API (тест доступных эндпоинтов)")
    print("2. Включить автопродление на всех пакетах")
    print("3. Показать информацию о всех пакетах")
    print("0. Выход")

    choice = input("\nВаш выбор: ")

    if choice == "1":
        test_api_with_data_from_table()
    elif choice == "2":
        enable_auto_renewal_all()
    elif choice == "3":
        test_api_with_data_from_table()
    else:
        print("До свидания!")


if __name__ == "__main__":
    main()
