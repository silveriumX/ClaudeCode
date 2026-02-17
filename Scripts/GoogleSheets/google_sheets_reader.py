"""
Скрипт для чтения Google Sheets таблицы с серверами
Позволяет Cursor AI анализировать данные из таблицы
"""

import requests
import csv
import json
from datetime import datetime
import os
import sys

# Устанавливаем UTF-8 для консоли Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class GoogleSheetsReader:
    def __init__(self, spreadsheet_id, sheet_name='Сервера'):
        """
        Args:
            spreadsheet_id: ID таблицы из URL
            sheet_name: Название листа (по умолчанию 'Сервера')
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.data = []
        self.headers = []

    def fetch_data(self):
        """Получает данные из Google Sheets через публичный CSV экспорт"""
        # URL для экспорта листа в CSV формате
        url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={self.sheet_name}"

        try:
            print(f"📥 Загружаю данные из таблицы...")
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                # Парсим CSV
                lines = response.text.splitlines()
                reader = csv.reader(lines)

                rows = list(reader)
                if len(rows) > 0:
                    self.headers = rows[0]  # Первая строка - заголовки
                    self.data = rows[1:]    # Остальное - данные

                    print(f"✅ Загружено {len(self.data)} строк данных")
                    print(f"📊 Колонок: {len(self.headers)}")
                    return True
            else:
                print(f"❌ Ошибка загрузки: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def save_to_json(self, filename='servers_data.json'):
        """Сохраняет данные в JSON формате"""
        data_with_headers = []

        for row in self.data:
            row_dict = {}
            for i, header in enumerate(self.headers):
                if i < len(row):
                    row_dict[header] = row[i]
                else:
                    row_dict[header] = ""
            data_with_headers.append(row_dict)

        output = {
            'last_updated': datetime.now().isoformat(),
            'total_rows': len(self.data),
            'headers': self.headers,
            'data': data_with_headers
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"💾 Данные сохранены в {filename}")
        return filename

    def save_to_csv(self, filename='servers_data.csv'):
        """Сохраняет данные в CSV формате"""
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            writer.writerows(self.data)

        print(f"💾 Данные сохранены в {filename}")
        return filename

    def get_server_by_name(self, shop_name):
        """Находит сервер по названию магазина"""
        results = []
        shop_index = self.headers.index('Магазин') if 'Магазин' in self.headers else 0

        for row in self.data:
            if len(row) > shop_index and row[shop_index] == shop_name:
                server_dict = {self.headers[i]: row[i] if i < len(row) else ""
                              for i in range(len(self.headers))}
                results.append(server_dict)

        return results

    def get_all_shops(self):
        """Возвращает список всех магазинов"""
        shop_index = self.headers.index('Магазин') if 'Магазин' in self.headers else 0
        shops = set()

        for row in self.data:
            if len(row) > shop_index and row[shop_index]:
                shops.add(row[shop_index])

        return sorted(list(shops))

    def get_statistics(self):
        """Возвращает статистику по серверам"""
        stats = {
            'total_servers': len(self.data),
            'shops': {},
            'countries': {},
            'statuses': {},
            'providers': {}
        }

        # Индексы колонок
        shop_idx = self.headers.index('Магазин') if 'Магазин' in self.headers else -1
        country_idx = self.headers.index('Страна сервера') if 'Страна сервера' in self.headers else -1
        status_idx = self.headers.index('Статус машины') if 'Статус машины' in self.headers else -1
        provider_idx = self.headers.index('Прокси провайдер') if 'Прокси провайдер' in self.headers else -1

        for row in self.data:
            # Подсчет по магазинам
            if shop_idx >= 0 and len(row) > shop_idx and row[shop_idx]:
                stats['shops'][row[shop_idx]] = stats['shops'].get(row[shop_idx], 0) + 1

            # Подсчет по странам
            if country_idx >= 0 and len(row) > country_idx and row[country_idx]:
                stats['countries'][row[country_idx]] = stats['countries'].get(row[country_idx], 0) + 1

            # Подсчет по статусам
            if status_idx >= 0 and len(row) > status_idx and row[status_idx]:
                stats['statuses'][row[status_idx]] = stats['statuses'].get(row[status_idx], 0) + 1

            # Подсчет по провайдерам
            if provider_idx >= 0 and len(row) > provider_idx and row[provider_idx]:
                stats['providers'][row[provider_idx]] = stats['providers'].get(row[provider_idx], 0) + 1

        return stats

    def print_summary(self):
        """Выводит краткую сводку"""
        stats = self.get_statistics()

        print("\n" + "="*60)
        print("📊 СТАТИСТИКА ПО СЕРВЕРАМ")
        print("="*60)
        print(f"\n🖥️  Всего серверов: {stats['total_servers']}")

        if stats['shops']:
            print(f"\n🏪 По магазинам:")
            for shop, count in sorted(stats['shops'].items()):
                print(f"   {shop}: {count}")

        if stats['countries']:
            print(f"\n🌍 По странам:")
            for country, count in sorted(stats['countries'].items()):
                print(f"   {country}: {count}")

        if stats['statuses']:
            print(f"\n📡 По статусам:")
            for status, count in sorted(stats['statuses'].items()):
                print(f"   {status}: {count}")

        print("\n" + "="*60)


def main():
    """Основная функция"""
    # ID вашей таблицы
    SPREADSHEET_ID = "1wIS9hjLSbIU4PSjXbXyIoh3_KHVBRaX2jDQVj4o51V8"

    # Создаем reader
    reader = GoogleSheetsReader(SPREADSHEET_ID, sheet_name='Сервера')

    # Загружаем данные
    if reader.fetch_data():
        # Сохраняем в оба формата
        reader.save_to_json('servers_data.json')
        reader.save_to_csv('servers_data.csv')

        # Выводим статистику
        reader.print_summary()

        print("\n✅ Готово! Теперь Cursor AI может анализировать данные из файлов:")
        print("   📄 servers_data.json - для программного анализа")
        print("   📊 servers_data.csv - для просмотра в Excel/Sheets")

        return True
    else:
        print("\n❌ Не удалось загрузить данные")
        print("\n💡 Проверьте:")
        print("   1. Таблица доступна по ссылке (права на просмотр)")
        print("   2. Название листа правильное ('Сервера')")
        print("   3. Есть подключение к интернету")
        return False


if __name__ == "__main__":
    main()
