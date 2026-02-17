#!/usr/bin/env python3
"""
Чтение данных серверов из Google Sheets через сервис-аккаунт
Для диагностики проблемы с HTTP 500 ошибками
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# Путь к JSON файлу сервис-аккаунта
SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(__file__),
    'servermanagment.json'
)

# ID вашей таблицы с серверами
# Получить из URL: https://docs.google.com/spreadsheets/d/ЭТОТ_ID/edit
SPREADSHEET_ID = "1wIS9hjLSbIU4PSjXbXyIoh3_KHVBRaX2jDQVj4o51V8"
SHEET_NAME = "Сервера"  # Название листа

def main():
    print("=" * 80)
    print("ЧТЕНИЕ ДАННЫХ СЕРВЕРОВ ИЗ GOOGLE SHEETS")
    print("=" * 80)
    print()

    # Используем глобальную переменную
    service_account_file = SERVICE_ACCOUNT_FILE

    # Проверяем наличие сервис-аккаунта
    if not os.path.exists(service_account_file):
        print(f"[ERROR] Сервис-аккаунт не найден: {service_account_file}")
        print("\nИщем файл в других местах...")

        # Поиск в текущей папке
        local_sa = "service_account.json"
        if os.path.exists(local_sa):
            service_account_file = local_sa
            print(f"[OK] Найден: {local_sa}")
        else:
            print("[ERROR] Создайте файл service_account.json в этой папке")
            print("\nИнструкция:")
            print("1. Скопируйте файл из Projects/FinanceBot/service_account.json")
            print("2. Или создайте новый в Google Cloud Console")
            return

    print(f"[1/5] Подключение к Google Sheets...")
    print(f"      Сервис-аккаунт: {service_account_file}")

    try:
        # Настройка авторизации
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            service_account_file,
            scope
        )
        client = gspread.authorize(creds)

        print("[OK] Авторизация успешна")

        # Открываем таблицу
        print(f"\n[2/5] Открытие таблицы ID: {SPREADSHEET_ID}...")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"[OK] Таблица открыта: {spreadsheet.title}")

        # Получаем лист
        print(f"\n[3/5] Чтение листа '{SHEET_NAME}'...")
        worksheet = spreadsheet.worksheet(SHEET_NAME)

        # Получаем все данные
        all_data = worksheet.get_all_values()

        if not all_data:
            print("[ERROR] Лист пустой!")
            return

        headers = all_data[0]
        data_rows = all_data[1:]

        print(f"[OK] Загружено:")
        print(f"     Строк: {len(data_rows)}")
        print(f"     Колонок: {len(headers)}")

        # Формируем словари
        print(f"\n[4/5] Обработка данных...")
        servers = []
        for row in data_rows:
            server = {}
            for i, header in enumerate(headers):
                server[header] = row[i] if i < len(row) else ""
            servers.append(server)

        print(f"[OK] Обработано {len(servers)} серверов")

        # Анализируем проблемные серверы
        print(f"\n[5/5] АНАЛИЗ ПРОБЛЕМНЫХ СЕРВЕРОВ...")
        print("=" * 80)

        problem_ips = [
            '89.124.71.240',
            '89.124.72.242',
            '91.201.113.127',
            '62.84.101.97',
            '5.35.32.68'
        ]

        # Находим индексы нужных колонок
        ip_col = 'Текущий IP' if 'Текущий IP' in headers else 'IP'
        shop_col = 'Магазин'
        rdp_col = 'RDP IP:Username:Password'

        print("\n>>> ПРОБЛЕМНЫЕ СЕРВЕРЫ <<<")
        print("-" * 80)

        problem_servers = []
        for server in servers:
            ip = server.get(ip_col, server.get('IP', ''))
            if ip in problem_ips:
                problem_servers.append(server)

                shop = server.get(shop_col, 'N/A')
                rdp = server.get(rdp_col, 'N/A')

                print(f"\nIP: {ip} | Магазин: {shop}")

                if rdp and rdp != 'N/A':
                    # Парсим RDP строку: IP:Username:Password
                    parts = rdp.split(':')
                    if len(parts) >= 3:
                        rdp_ip = parts[0]
                        rdp_user = parts[1]
                        rdp_pass = parts[2] if len(parts[2]) > 0 else "ПУСТО"

                        print(f"  RDP IP: {rdp_ip}")
                        print(f"  RDP Username: '{rdp_user}'")
                        print(f"  RDP Password: {'*' * len(rdp_pass)} ({len(rdp_pass)} символов)")

                        # АНАЛИЗ
                        if '\\' in rdp_user:
                            print(f"  ⚠️ WARNING: Username содержит обратный слеш!")
                            print(f"  ⚠️ Формат: {rdp_user}")
                            print(f"  ⚠️ Код добавит еще IP\\, получится: {ip}\\{rdp_user}")
                            print(f"  ⚠️ ЭТО ОШИБКА!")
                        else:
                            print(f"  ✓ Формат username правильный (без слеша)")
                            print(f"  ✓ Код использует: {ip}\\{rdp_user}")

                        # Проверка пароля на спец.символы
                        spec_chars = ['<', '>', '&', '"', "'", '\\']
                        has_spec = any(c in rdp_pass for c in spec_chars)
                        if has_spec:
                            print(f"  ⚠️ WARNING: Пароль содержит спец.символы (<>&\"'\\)")
                            print(f"  ⚠️ Это может ломать XML/SOAP запросы!")
                    else:
                        print(f"  ⚠️ Неправильный формат RDP: {rdp}")
                else:
                    print(f"  ⚠️ RDP данные отсутствуют!")

        print("\n" + "-" * 80)
        print("\n>>> РАБОТАЮЩИЕ СЕРВЕРЫ (для сравнения) <<<")
        print("-" * 80)

        working_count = 0
        for server in servers:
            ip = server.get(ip_col, server.get('IP', ''))
            if ip not in problem_ips and working_count < 3:
                shop = server.get(shop_col, 'N/A')
                rdp = server.get(rdp_col, 'N/A')

                print(f"\nIP: {ip} | Магазин: {shop}")

                if rdp and rdp != 'N/A':
                    parts = rdp.split(':')
                    if len(parts) >= 3:
                        rdp_user = parts[1]
                        rdp_pass = parts[2] if len(parts[2]) > 0 else "ПУСТО"

                        print(f"  Username: '{rdp_user}'")
                        print(f"  Password: {'*' * len(rdp_pass)} ({len(rdp_pass)} символов)")

                        if '\\' in rdp_user:
                            print(f"  ℹ️ Содержит слеш: {rdp_user}")
                        else:
                            print(f"  ✓ Простой формат")

                working_count += 1

        # ВЫВОДЫ
        print("\n" + "=" * 80)
        print("ВЫВОДЫ")
        print("=" * 80)

        print(f"\nНайдено проблемных серверов: {len(problem_servers)} из {len(problem_ips)}")

        # Проверка паттерна
        problem_with_slash = 0
        for s in problem_servers:
            rdp_data = s.get(rdp_col, '')
            if rdp_data:
                parts = rdp_data.split(':')
                if len(parts) > 1 and '\\' in parts[1]:
                    problem_with_slash += 1

        if problem_with_slash > 0:
            print(f"\n❌ НАЙДЕНА ПРОБЛЕМА!")
            print(f"   {problem_with_slash} проблемных серверов имеют \\ в username")
            print(f"   Это вызывает двойной префикс: IP\\IP\\Username")
            print(f"   WinRM возвращает HTTP 500 из-за неверного формата")
            print()
            print("   РЕШЕНИЕ: Убрать IP\\ из колонки RDP в Google Sheets")
            print("   Было: '89.124.71.240:89.124.71.240\\Administrator:password'")
            print("   Стало: '89.124.71.240:Administrator:password'")

        # Сохраняем данные для дальнейшего анализа
        print(f"\n[СОХРАНЕНИЕ] Данные сохранены в servers_full_data.json")
        with open('servers_full_data.json', 'w', encoding='utf-8') as f:
            json.dump({
                'headers': headers,
                'all_servers': servers,
                'problem_servers': problem_servers,
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    except gspread.exceptions.SpreadsheetNotFound:
        print("[ERROR] Таблица не найдена!")
        print("Проверьте:")
        print("1. ID таблицы правильный")
        print("2. Сервис-аккаунт имеет доступ к таблице")
        print("   (Нужно добавить finance-bot@sheets-api-485406.iam.gserviceaccount.com)")
    except gspread.exceptions.WorksheetNotFound:
        print(f"[ERROR] Лист '{SHEET_NAME}' не найден!")
        print("Доступные листы:")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        for sheet in spreadsheet.worksheets():
            print(f"  - {sheet.title}")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
