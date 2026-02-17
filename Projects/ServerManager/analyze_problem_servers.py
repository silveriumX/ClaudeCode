#!/usr/bin/env python3
"""
Анализ проблемных серверов из Google Sheets
"""
import json

# Проблемные IP
PROBLEM_IPS = [
    '89.124.71.240',
    '89.124.72.242',
    '91.201.113.127',
    '62.84.101.97',
    '5.35.32.68'
]

def main():
    print("=" * 80)
    print("АНАЛИЗ ПРОБЛЕМНЫХ СЕРВЕРОВ ИЗ GOOGLE SHEETS")
    print("=" * 80)
    print()

    # Загружаем данные
    with open('servers_full_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    headers = data['headers']
    servers = data['all_servers']

    rdp_col = 'RDP \nIP:Username:Password'

    print(f"[*] Всего серверов в таблице: {len(servers)}")
    print(f"[*] Ищем проблемные IP: {len(PROBLEM_IPS)}")
    print()

    # Ищем проблемные серверы
    problem_servers = []
    for server in servers:
        rdp_data = server.get(rdp_col, '')
        if any(ip in rdp_data for ip in PROBLEM_IPS):
            problem_servers.append(server)

    print("=" * 80)
    print(f"НАЙДЕНО ПРОБЛЕМНЫХ СЕРВЕРОВ: {len(problem_servers)}")
    print("=" * 80)

    if not problem_servers:
        print("\n⚠️ Проблемные IP не найдены в таблице!")
        print("\nВозможные причины:")
        print("1. Эти серверы удалены из таблицы")
        print("2. IP изменились")
        print("3. Проблема в другом листе")
        print("\nПопробуем найти по части IP...")

        # Ищем любые совпадения
        for problem_ip in PROBLEM_IPS:
            print(f"\n>>> Поиск {problem_ip}:")
            found = False
            for server in servers:
                for key, value in server.items():
                    if problem_ip in str(value):
                        print(f"    Найдено в колонке '{key}': {value[:80]}")
                        found = True
                        break
                if found:
                    break
            if not found:
                print(f"    НЕ найдено в таблице!")
    else:
        # Анализируем найденные серверы
        for server in problem_servers:
            shop = server.get('Магазин', 'N/A')
            rdp_data = server.get(rdp_col, 'N/A')
            current_ip = server.get('Текущий IP', 'N/A')
            status = server.get('Статус машины', 'N/A')

            print(f"\n{'=' * 80}")
            print(f"Магазин: {shop}")
            print(f"Статус: {status}")
            print(f"Текущий IP (через 2ip): {current_ip}")
            print("-" * 80)

            # Парсим RDP данные
            if rdp_data and ':' in rdp_data:
                parts = rdp_data.split(':')
                if len(parts) >= 3:
                    rdp_ip = parts[0]
                    rdp_user = parts[1]
                    rdp_pass = ':'.join(parts[2:])  # Пароль может содержать ':'

                    print(f"RDP IP: {rdp_ip}")
                    print(f"RDP Username: '{rdp_user}'")
                    print(f"RDP Password: {'*' * len(rdp_pass)} ({len(rdp_pass)} символов)")
                    print()

                    # ==================== АНАЛИЗ ====================
                    print("АНАЛИЗ:")

                    # 1. Проверка на слеш в username
                    if '\\' in rdp_user:
                        print(f"[ПРОБЛЕМА 1] Username содержит обратный слеш!")
                        print(f"   Username: '{rdp_user}'")
                        print(f"   Код добавит еще {rdp_ip}\\")
                        print(f"   Получится: '{rdp_ip}\\{rdp_user}' (ДВОЙНОЙ ПРЕФИКС!)")
                        print(f"   ЭТО ПРИЧИНА HTTP 500!")
                        print()
                        print(f"   РЕШЕНИЕ: Изменить в Google Sheets на просто 'Administrator'")
                        print(f"   Было: {rdp_data}")
                        print(f"   Должно быть: {rdp_ip}:Administrator:{rdp_pass}")
                    else:
                        print(f"[OK] Username в правильном формате (без слеша): '{rdp_user}'")
                        print(f"  Код использует: {rdp_ip}\\{rdp_user}")
                    print()

                    # 2. Проверка спец.символов в пароле
                    spec_chars = ['<', '>', '&', '"', "'"]
                    found_spec = [c for c in spec_chars if c in rdp_pass]
                    if found_spec:
                        print(f"[ПРОБЛЕМА 2] Пароль содержит спец.символы XML: {found_spec}")
                        print(f"   Это может ломать SOAP/XML запросы!")
                        print(f"   Символы: {', '.join(found_spec)}")
                    else:
                        print(f"[OK] Пароль не содержит опасных спец.символов")
                    print()

                    # 3. Проверка длины
                    if len(rdp_pass) == 0:
                        print(f"[ПРОБЛЕМА 3] Пароль ПУСТОЙ!")
                    elif len(rdp_pass) > 50:
                        print(f"[WARNING] Пароль очень длинный ({len(rdp_pass)} символов)")
                    else:
                        print(f"[OK] Длина пароля нормальная ({len(rdp_pass)} символов)")
            else:
                print(f"[ERROR] Неправильный формат RDP: {rdp_data}")

    # Сравнение с работающими
    print("\n\n" + "=" * 80)
    print("ДЛЯ СРАВНЕНИЯ: РАБОТАЮЩИЕ СЕРВЕРЫ")
    print("=" * 80)

    working_servers = [s for s in servers if s.get('Статус машины') == 'OK Online'][:3]

    for server in working_servers:
        shop = server.get('Магазин', 'N/A')
        rdp_data = server.get(rdp_col, 'N/A')

        if rdp_data and ':' in rdp_data:
            parts = rdp_data.split(':')
            if len(parts) >= 2:
                rdp_ip = parts[0]
                rdp_user = parts[1]

                print(f"\nМагазин: {shop} | IP: {rdp_ip}")
                print(f"  Username: '{rdp_user}'")
                if '\\' in rdp_user:
                    print(f"  [INFO] Этот тоже имеет слеш в username")
                else:
                    print(f"  [OK] Простой формат (работает!)")

    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ ВЫВОД")
    print("=" * 80)
    print()

    if problem_servers:
        print(f"✅ Найдено {len(problem_servers)} проблемных серверов в таблице")
        print("\nПроверьте выводы АНАЛИЗ выше для каждого сервера")
        print("Если есть '❌ ПРОБЛЕМА' - это нужно исправить!")
    else:
        print("⚠️ Проблемные IP не найдены в текущих данных таблицы")
        print("\nВозможные причины:")
        print("1. Эти IP используются в другом листе")
        print("2. Эти серверы временно отключены/удалены")
        print("3. Нужно проверить другую таблицу")

if __name__ == "__main__":
    main()
