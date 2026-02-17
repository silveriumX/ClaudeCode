#!/usr/bin/env python3
"""
=============================================================================
CITY MATCHER - Модуль сверки городов (English ↔ Russian)
=============================================================================
Описание:
- Сопоставляет английские названия городов от 2ip.io с русскими ожидаемыми
- Поддерживает множественный выбор ("Краснодар / Сочи / Москва")
- Возвращает статус совпадения для логирования ошибок

Версия: 1.0
Дата: 26.01.2026
=============================================================================
"""

import logging
import re

logger = logging.getLogger(__name__)

# =============================================================================
# МАППИНГ ГОРОДОВ (English → Russian)
# =============================================================================

# Основной маппинг - точное соответствие
CITY_MAP_EN_TO_RU = {
    # Крупные города
    "Moscow": "Москва",
    "Saint Petersburg": "Санкт-Петербург",
    "St. Petersburg": "Санкт-Петербург",
    "St Petersburg": "Санкт-Петербург",
    "Petersburg": "Санкт-Петербург",

    # Южные регионы
    "Krasnodar": "Краснодар",
    "Sochi": "Сочи",
    "Rostov-on-Don": "Ростов-на-Дону",
    "Rostov": "Ростов-на-Дону",

    # Поволжье
    "Kazan": "Казань",
    "Samara": "Самара",
    "Nizhny Novgorod": "Нижний Новгород",
    "Volgograd": "Волгоград",
    "Saratov": "Саратов",
    "Ulyanovsk": "Ульяновск",
    "Perm": "Пермь",

    # Урал
    "Yekaterinburg": "Екатеринбург",
    "Ekaterinburg": "Екатеринбург",
    "Chelyabinsk": "Челябинск",
    "Ufa": "Уфа",
    "Tyumen": "Тюмень",
    "Magnitogorsk": "Магнитогорск",

    # Сибирь
    "Novosibirsk": "Новосибирск",
    "Omsk": "Омск",
    "Krasnoyarsk": "Красноярск",
    "Barnaul": "Барнаул",
    "Irkutsk": "Иркутск",
    "Tomsk": "Томск",
    "Kemerovo": "Кемерово",

    # Дальний Восток
    "Vladivostok": "Владивосток",
    "Khabarovsk": "Хабаровск",

    # Центральная Россия
    "Voronezh": "Воронеж",
    "Tula": "Тула",
    "Ryazan": "Рязань",
    "Lipetsk": "Липецк",
    "Kaluga": "Калуга",
    "Bryansk": "Брянск",
    "Kursk": "Курск",
    "Belgorod": "Белгород",
    "Orel": "Орёл",
    "Tambov": "Тамбов",
    "Ivanovo": "Иваново",
    "Yaroslavl": "Ярославль",
    "Vladimir": "Владимир",
    "Tver": "Тверь",
    "Smolensk": "Смоленск",
    "Kostroma": "Кострома",

    # Северо-Запад
    "Kaliningrad": "Калининград",
    "Murmansk": "Мурманск",
    "Arkhangelsk": "Архангельск",
    "Petrozavodsk": "Петрозаводск",
    "Pskov": "Псков",
    "Veliky Novgorod": "Великий Новгород",
    "Novgorod": "Новгород",
    "Vologda": "Вологда",

    # Юг России / Кавказ
    "Elista": "Элиста",
    "Stavropol": "Ставрополь",
    "Makhachkala": "Махачкала",
    "Vladikavkaz": "Владикавказ",
    "Nalchik": "Нальчик",
    "Grozny": "Грозный",
    "Astrakhan": "Астрахань",
    "Maykop": "Майкоп",

    # Другие
    "Novorossiysk": "Новороссийск",
    "Taganrog": "Таганрог",
    "Orenburg": "Оренбург",
    "Penza": "Пенза",
    "Kirov": "Киров",
    "Cheboksary": "Чебоксары",
    "Saransk": "Саранск",
    "Yoshkar-Ola": "Йошкар-Ола",
    "Izhevsk": "Ижевск",
    "Syktyvkar": "Сыктывкар",
}

# Обратный маппинг (Russian → English) для быстрого поиска
CITY_MAP_RU_TO_EN = {v: k for k, v in CITY_MAP_EN_TO_RU.items()}

# Дополнительные русские варианты написания
CITY_ALIASES_RU = {
    "СПб": "Санкт-Петербург",
    "Питер": "Санкт-Петербург",
    "Санкт Петербург": "Санкт-Петербург",
    "Ростов на Дону": "Ростов-на-Дону",
    "Нижний": "Нижний Новгород",
    "Екб": "Екатеринбург",
    "Новосиб": "Новосибирск",
}


class CityMatcher:
    """
    Класс для сверки городов между английской и русской версиями
    """

    def __init__(self):
        self.en_to_ru = CITY_MAP_EN_TO_RU.copy()
        self.ru_aliases = CITY_ALIASES_RU.copy()

    def normalize_city_ru(self, city_ru: str) -> str:
        """Нормализует русское название города"""
        if not city_ru:
            return ""

        city = city_ru.strip()

        # Проверяем алиасы
        if city in self.ru_aliases:
            return self.ru_aliases[city]

        return city

    def translate_en_to_ru(self, city_en: str) -> str:
        """Переводит английское название города на русский"""
        if not city_en:
            return ""

        city = city_en.strip()

        # Точное совпадение
        if city in self.en_to_ru:
            return self.en_to_ru[city]

        # Нечувствительный к регистру поиск
        city_lower = city.lower()
        for en, ru in self.en_to_ru.items():
            if en.lower() == city_lower:
                return ru

        # Не найдено - возвращаем как есть
        return city

    def parse_expected_cities(self, expected_str: str) -> list:
        """
        Парсит строку ожидаемых городов

        Поддерживает форматы:
        - "Москва"
        - "Краснодар / Сочи / Москва"
        - "Краснодар, Сочи, Москва"
        - "Краснодар или Москва"
        """
        if not expected_str:
            return []

        # Разделители: / , или or
        cities = re.split(r'\s*[/,]\s*|\s+или\s+|\s+or\s+', expected_str, flags=re.IGNORECASE)

        # Нормализуем каждый город
        result = []
        for city in cities:
            city = city.strip()
            if city:
                normalized = self.normalize_city_ru(city)
                result.append(normalized)

        return result

    def match(self, actual_en: str, expected_ru: str) -> dict:
        """
        Сверяет фактический город (English) с ожидаемым (Russian)

        Args:
            actual_en: Город от 2ip.io (English)
            expected_ru: Ожидаемый город из Google Sheets (Russian, возможно несколько)

        Returns:
            dict: {
                'is_match': bool,           # Совпадает или нет
                'actual_city_en': str,      # Фактический город (EN)
                'actual_city_ru': str,      # Фактический город (RU перевод)
                'expected_cities': list,    # Список допустимых городов (RU)
                'matched_city': str,        # Какой город совпал (или '')
                'error_type': str,          # 'ok', 'city_mismatch', 'city_unknown', 'no_expected'
                'message': str              # Человекочитаемое сообщение
            }
        """
        result = {
            'is_match': False,
            'actual_city_en': actual_en or '',
            'actual_city_ru': '',
            'expected_cities': [],
            'matched_city': '',
            'error_type': 'ok',
            'message': ''
        }

        # Проверка на пустые значения
        if not expected_ru:
            result['error_type'] = 'no_expected'
            result['message'] = 'Ожидаемый город не указан'
            result['is_match'] = True  # Если не указан - не проверяем
            return result

        if not actual_en or actual_en == 'ERROR' or actual_en == 'N/A':
            result['error_type'] = 'city_unknown'
            result['message'] = f'Не удалось определить город (2ip.io вернул: {actual_en})'
            return result

        # Переводим фактический город
        actual_ru = self.translate_en_to_ru(actual_en)
        result['actual_city_ru'] = actual_ru

        # Парсим ожидаемые города
        expected_cities = self.parse_expected_cities(expected_ru)
        result['expected_cities'] = expected_cities

        if not expected_cities:
            result['error_type'] = 'no_expected'
            result['message'] = 'Ожидаемый город не указан'
            result['is_match'] = True
            return result

        # Сверяем
        for expected in expected_cities:
            if actual_ru.lower() == expected.lower():
                result['is_match'] = True
                result['matched_city'] = expected
                result['error_type'] = 'ok'
                result['message'] = f'Город совпадает: {actual_ru}'
                return result

        # Не совпало
        result['error_type'] = 'city_mismatch'
        if len(expected_cities) == 1:
            result['message'] = f'Город не совпадает: {actual_ru} (ожидался {expected_cities[0]})'
        else:
            result['message'] = f'Город не совпадает: {actual_ru} (ожидался один из: {", ".join(expected_cities)})'

        return result

    def is_error(self, result: dict) -> bool:
        """Проверяет, является ли результат ошибкой (для логирования)"""
        return result['error_type'] in ('city_mismatch', 'city_unknown')


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def check_city(actual_en: str, expected_ru: str) -> dict:
    """
    Быстрая функция для проверки города

    Args:
        actual_en: Город от 2ip.io (English)
        expected_ru: Ожидаемый город из Google Sheets (Russian)

    Returns:
        dict с результатом проверки
    """
    matcher = CityMatcher()
    return matcher.match(actual_en, expected_ru)


def format_city_status(result: dict) -> str:
    """Форматирует результат для вывода в Google Sheets"""
    if result['is_match']:
        return f"OK ({result['actual_city_ru']})"
    else:
        return f"ERROR: {result['message']}"


# =============================================================================
# ТЕСТЫ
# =============================================================================

if __name__ == "__main__":
    # Тесты
    matcher = CityMatcher()

    tests = [
        ("Saint Petersburg", "Санкт-Петербург"),
        ("Perm", "Пермь"),
        ("Tula", "Тула"),
        ("Elista", "Элиста"),
        ("Krasnodar", "Краснодар / Сочи / Москва"),
        ("Moscow", "Краснодар / Сочи / Москва"),
        ("Sochi", "Краснодар / Сочи / Москва"),
        ("Novosibirsk", "Краснодар / Сочи / Москва"),  # Должен быть mismatch
        ("ERROR", "Москва"),  # Ошибка определения
        ("Moscow", ""),  # Нет ожидаемого
    ]

    print("=" * 70)
    print("ТЕСТЫ CITY MATCHER")
    print("=" * 70)

    for actual, expected in tests:
        result = matcher.match(actual, expected)
        status = "OK" if result['is_match'] else "FAIL"
        print(f"\n{status}: {actual} vs '{expected}'")
        print(f"  -> {result['message']}")
        print(f"  -> error_type: {result['error_type']}")
