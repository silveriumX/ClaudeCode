"""
Скрипт создания листа "USDT Зарплаты" в Google Sheets
Копирует структуру из листа "USDT"
"""
import sys
import os

# Добавляем путь к модулям FinanceBot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Projects', 'FinanceBot'))

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config

def create_usdt_salaries_sheet():
    """Создать лист USDT Зарплаты"""
    try:
        # Подключаемся к Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)

        # Открываем таблицу
        spreadsheet = client.open_by_key(config.GOOGLE_SHEETS_ID)

        print("="*70)
        print("СОЗДАНИЕ ЛИСТА 'USDT Зарплаты'")
        print("="*70 + "\n")

        # Проверяем существует ли уже лист
        try:
            existing = spreadsheet.worksheet('USDT Зарплаты')
            print("⚠️  Лист 'USDT Зарплаты' уже существует!")
            print(f"   Строк: {existing.row_count}, Колонок: {existing.col_count}\n")

            response = input("Пересоздать лист? (yes/no): ")
            if response.lower() != 'yes':
                print("Отменено.")
                return

            # Удаляем старый лист
            spreadsheet.del_worksheet(existing)
            print("✓ Старый лист удалён\n")
        except:
            pass

        # Копируем структуру из листа USDT
        print("1. Получение структуры из листа 'USDT'...")
        usdt_sheet = spreadsheet.worksheet('USDT')

        # Получаем заголовки (первая строка)
        headers = usdt_sheet.row_values(1)
        print(f"   Заголовков: {len(headers)}")
        print(f"   Структура: {', '.join(headers[:5])}...\n")

        # Создаём новый лист
        print("2. Создание нового листа...")
        new_sheet = spreadsheet.add_worksheet(
            title='USDT Зарплаты',
            rows=100,
            cols=len(headers)
        )
        print("   ✓ Лист создан\n")

        # Копируем заголовки
        print("3. Копирование заголовков...")
        new_sheet.update('A1:M1', [headers])
        print("   ✓ Заголовки скопированы\n")

        # Форматирование (опционально)
        print("4. Применение форматирования...")
        # Жирный шрифт для заголовков
        new_sheet.format('A1:M1', {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
        })
        print("   ✓ Форматирование применено\n")

        print("="*70)
        print("ЛИСТ 'USDT Зарплаты' СОЗДАН УСПЕШНО")
        print("="*70)
        print(f"""
СТРУКТУРА ЛИСТА (как в USDT):
{chr(10).join([f'{i+1}. {h}' for i, h in enumerate(headers)])}

СЛЕДУЮЩИЕ ШАГИ:
1. Задеплоить обновлённый код на сервер
2. Создать тестовую заявку: зарплата в USDT
3. Проверить что она попала в лист "USDT Зарплаты"
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_usdt_salaries_sheet()
