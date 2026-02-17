"""
Помощник для работы с данными серверов
Примеры использования для общения с Cursor AI
"""

import json
from datetime import datetime
import sys
import io

# Устанавливаем UTF-8 для консоли Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def load_data():
    """Загружает данные из JSON файла"""
    with open('servers_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_server_info(shop_name):
    """Получить информацию о сервере по названию магазина"""
    data = load_data()
    results = []

    for server in data['data']:
        if server.get('Магазин', '').upper() == shop_name.upper():
            results.append(server)

    return results

def get_all_servers_summary():
    """Получить краткую сводку по всем серверам"""
    data = load_data()

    summary = []
    for server in data['data']:
        summary.append({
            'Магазин': server.get('Магазин', 'N/A'),
            'ID': server.get('ID сервера в админке', 'N/A'),
            'Статус': server.get('Статус машины', 'N/A'),
            'Страна': server.get('Страна сервера', 'N/A'),
            'IP': server.get('Текущий IP', 'N/A'),
            'Город': server.get('Текущий город по 2ip.io', 'N/A'),
            'AnyDesk': server.get('anydesk (AD)', 'N/A'),
        })

    return summary

def get_servers_by_status(status='OK Online'):
    """Получить серверы по статусу"""
    data = load_data()
    results = []

    for server in data['data']:
        if server.get('Статус машины', '') == status:
            results.append({
                'Магазин': server.get('Магазин'),
                'ID': server.get('ID сервера в админке'),
                'IP': server.get('Текущий IP'),
                'Город': server.get('Текущий город по 2ip.io'),
            })

    return results

def get_proxy_info():
    """Получить информацию о прокси"""
    data = load_data()
    proxies = []

    for server in data['data']:
        if server.get('Прокси провайдер'):
            proxies.append({
                'Магазин': server.get('Магазин'),
                'Провайдер': server.get('Прокси провайдер'),
                'Статус': server.get('Статус прокси'),
                'Город прокси': server.get('Город прокси который нужен'),
                'Трафик лимит': server.get('Лимит трафика (GB)'),
                'Использовано': server.get('Использовано (GB)'),
                'Осталось': server.get('Осталось (GB)'),
                'Дата истечения': server.get('Дата истечения прокси'),
            })

    return proxies

def search_servers(search_term):
    """Поиск серверов по любому полю"""
    data = load_data()
    results = []

    search_term = search_term.lower()

    for server in data['data']:
        # Ищем во всех полях
        for key, value in server.items():
            if search_term in str(value).lower():
                results.append(server)
                break

    return results

# Примеры использования
if __name__ == "__main__":
    print("=" * 60)
    print("ПРИМЕРЫ ЗАПРОСОВ К ДАННЫМ СЕРВЕРОВ")
    print("=" * 60)

    # Пример 1: Все серверы кратко
    print("\n1. Краткая сводка по всем серверам:")
    summary = get_all_servers_summary()
    for s in summary[:5]:  # Показываем первые 5
        print(f"   {s['Магазин']} (ID: {s['ID']}) - {s['Статус']} - {s['Город']}")
    print(f"   ... и ещё {len(summary) - 5} серверов")

    # Пример 2: Серверы со статусом OK
    print("\n2. Серверы со статусом 'OK Online':")
    online = get_servers_by_status('OK Online')
    print(f"   Всего онлайн: {len(online)}")
    for s in online[:3]:
        print(f"   - {s['Магазин']}: {s['IP']} ({s['Город']})")

    # Пример 3: Информация о конкретном магазине
    print("\n3. Информация о магазине MN:")
    mn_servers = get_server_info('MN')
    if mn_servers:
        for srv in mn_servers:
            print(f"   AnyDesk: {srv.get('anydesk (AD)')}")
            print(f"   RDP: {srv.get('RDP IP:Username:Password')}")
            print(f"   Статус: {srv.get('Статус машины')}")

    # Пример 4: Информация о прокси
    print("\n4. Состояние прокси:")
    proxies = get_proxy_info()
    for p in proxies[:3]:
        if p['Трафик лимит']:
            print(f"   {p['Магазин']}: {p['Использовано']}/{p['Трафик лимит']} GB")

    print("\n" + "=" * 60)
    print("✅ Данные успешно загружены и готовы к анализу!")
    print("=" * 60)
