#!/usr/bin/env python3
"""
=============================================================================
PROXYMA API - Модуль для работы с Proxyma.io API
=============================================================================
Описание:
- Получение списка пакетов прокси
- Получение детальной информации о пакете
- Получение баланса аккаунта
- Получение тарифов и цен
Версия: 3.0
Дата: 04.01.2026
API Документация: https://api.proxyma.io/
=============================================================================
"""

import requests
import logging

# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================
logger = logging.getLogger(__name__)

# =============================================================================
# КЛАСС: ProxymaAPI - Работа с Proxyma API
# =============================================================================
class ProxymaAPI:
    """
    Класс для взаимодействия с Proxyma.io API

    Используется для:
    - Получения информации о residential прокси пакетах
    - Проверки баланса ресселлер аккаунта
    - Получения информации о тарифах

    API Endpoint: https://api.proxyma.io/api
    Аутентификация: API Key в заголовке 'api-key'
    """

    def __init__(self, api_key):
        """
        Инициализация Proxyma API клиента

        Args:
            api_key (str): API ключ из личного кабинета Proxyma
        """
        self.api_key = api_key
        self.base_url = "https://api.proxyma.io/api"

        # Заголовки для всех запросов
        self.headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }

    # =========================================================================
    # МЕТОД: Получение списка всех пакетов
    # =========================================================================
    def get_packages(self):
        """
        Получает список всех residential пакетов ресселлера

        API Endpoint: GET /reseller/get/packages

        Returns:
            list: Список пакетов
                [
                    {
                        'package_key': str,  # Уникальный ключ пакета
                        'title': str,        # Название пакета
                        'created_at': str,   # Дата создания
                        'status': str        # Статус (active/expired)
                    },
                    ...
                ]

        Example:
            >>> api = ProxymaAPI('your-api-key')
            >>> packages = api.get_packages()
            >>> for pkg in packages:
            ...     print(pkg['title'], pkg['package_key'])
        """
        try:
            url = f"{self.base_url}/reseller/get/packages"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Проверка статуса в ответе
                if data.get('result', {}).get('status') == 200:
                    return data['result']['data']

            logger.warning(f"Failed to get packages, status: {response.status_code}")
            return []

        except Exception as e:
            logger.error(f"Error getting packages: {e}")
            return []

    # =========================================================================
    # МЕТОД: Получение детальной информации о пакете
    # =========================================================================
    def get_package_info(self, package_key):
        """
        Получает детальную информацию о конкретном пакете

        Включает:
        - Использованный и лимит трафика
        - Дату истечения
        - Статус активности

        API Endpoint: GET /reseller/info/package/{package_key}

        Args:
            package_key (str): Уникальный ключ пакета

        Returns:
            dict or None: Информация о пакете
                {
                    'traffic': {
                        'usage': float,      # Использовано GB
                        'limit': float       # Лимит GB
                    },
                    'expired_at': str,       # Дата истечения (YYYY-MM-DD)
                    'status': str            # Статус (active/expired)
                }

        Example:
            >>> api = ProxymaAPI('your-api-key')
            >>> info = api.get_package_info('abc123def456')
            >>> print(f"Used: {info['traffic']['usage']} GB")
            >>> print(f"Expires: {info['expired_at']}")
        """
        try:
            url = f"{self.base_url}/reseller/info/package/{package_key}"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Проверка статуса в ответе
                if data.get('result', {}).get('status') == 200:
                    return data['result']['data']

            logger.warning(f"Failed to get package info for {package_key}, status: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Error getting package info: {e}")
            return None

    # =========================================================================
    # МЕТОД: Получение баланса аккаунта
    # =========================================================================
    def get_balance(self):
        """
        Получает баланс ресселлер аккаунта

        API Endpoint: GET /reseller/get/balance

        Returns:
            str or None: Баланс в формате "$XX.XX" или None при ошибке

        Example:
            >>> api = ProxymaAPI('your-api-key')
            >>> balance = api.get_balance()
            >>> print(f"Balance: {balance}")
            Balance: $45.50
        """
        try:
            url = f"{self.base_url}/reseller/get/balance"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Баланс возвращается в поле 'message'
                if data.get('result', {}).get('status') == 200:
                    return data['result']['message']

            logger.warning(f"Failed to get balance, status: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None

    # =========================================================================
    # МЕТОД: Получение списка тарифов
    # =========================================================================
    def get_tariffs(self):
        """
        Получает список всех доступных тарифов с ценами

        API Endpoint: GET /reseller/get/tariffs

        Returns:
            list: Список тарифов
                [
                    {
                        'tariff_id': int,    # ID тарифа
                        'name': str,         # Название (например, "Nebula Set")
                        'price': str,        # Цена (например, "30")
                        'traffic': str       # Объём трафика (например, "10 GB")
                    },
                    ...
                ]

        Example:
            >>> api = ProxymaAPI('your-api-key')
            >>> tariffs = api.get_tariffs()
            >>> for tariff in tariffs:
            ...     print(f"{tariff['name']}: ${tariff['price']}")
        """
        try:
            url = f"{self.base_url}/reseller/get/tariffs"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                if data.get('result', {}).get('status') == 200:
                    return data['result']['data']

            logger.warning(f"Failed to get tariffs, status: {response.status_code}")
            return []

        except Exception as e:
            logger.error(f"Error getting tariffs: {e}")
            return []

    # =========================================================================
    # МЕТОД: Получение цены конкретного тарифа
    # =========================================================================
    def get_tariff_price(self, tariff_name):
        """
        Получает цену конкретного тарифа по его названию

        Используется для определения стоимости продления пакета

        Args:
            tariff_name (str): Название тарифа (например, "Nebula Set")

        Returns:
            str or None: Цена тарифа или None если не найден

        Example:
            >>> api = ProxymaAPI('your-api-key')
            >>> price = api.get_tariff_price('Nebula Set')
            >>> print(f"Price: ${price}")
            Price: $30
        """
        # Получаем все тарифы
        tariffs = self.get_tariffs()

        # Ищем тариф по названию
        for tariff in tariffs:
            if tariff['name'] == tariff_name:
                return tariff['price']

        logger.warning(f"Tariff '{tariff_name}' not found")
        return None

# =============================================================================
# КОНЕЦ МОДУЛЯ
# =============================================================================
