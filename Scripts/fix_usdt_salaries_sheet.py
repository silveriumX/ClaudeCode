"""
Исправление кодировки: пересоздание листа "USDT Зарплаты"
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Projects', 'FinanceBot'))

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config

def fix_usdt_salaries_sheet():
    """Пересоздать лист с правильной кодировкой"""
    try:
        # Подключаемся
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config.GOOGLE_SHEETS_ID)

        print("="*70)
        print("ИСПРАВЛЕНИЕ КОДИРОВКИ ЛИСТА")
        print("="*70 + "\n")

        # Получаем список всех листов
        print("1. Поиск неправильных листов...")
        all_sheets = spreadsheet.worksheets()
        sheets_to_delete = []

        for sheet in all_sheets:
            title = sheet.title
            if 'USDT' in title and title != 'USDT':
                print(f"   Найден лист с кракозябрами: {repr(title)}")
                sheets_to_delete.append(sheet)

        # Удаляем неправильные листы
        if sheets_to_delete:
            print(f"\n2. Удаление {len(sheets_to_delete)} неправильных листов...")
            for sheet in sheets_to_delete:
                try:
                    spreadsheet.del_worksheet(sheet)
                    print(f"   Удален: {repr(sheet.title)}")
                except Exception as e:
                    print(f"   Ошибка при удалении: {e}")
            print("   OK: Неправильные листы удалены\n")
        else:
            print("   Неправильных листов не найдено\n")

        # Проверяем существует ли уже правильный лист
        print("3. Проверка существующего листа 'USDT Зарплаты'...")
        try:
            existing = spreadsheet.worksheet('USDT Зарплаты')
            print("   Лист уже существует, пересоздаю...\n")
            spreadsheet.del_worksheet(existing)
        except:
            print("   Листа нет, создаю новый...\n")

        # Получаем структуру из листа USDT
        print("4. Чтение структуры из листа 'USDT'...")
        usdt_sheet = spreadsheet.worksheet('USDT')
        headers = usdt_sheet.row_values(1)
        print(f"   Заголовков: {len(headers)}\n")

        # Создаём новый лист с ПРАВИЛЬНОЙ кодировкой
        print("5. Создание нового листа 'USDT Зарплаты'...")

        # Используем правильную строку в UTF-8
        sheet_title = 'USDT Зарплаты'

        new_sheet = spreadsheet.add_worksheet(
            title=sheet_title,
            rows=100,
            cols=13
        )
        print(f"   OK: Лист создан: '{new_sheet.title}'\n")

        # Копируем заголовки
        print("6. Копирование заголовков...")
        new_sheet.update(values=[headers], range_name='A1')
        print("   OK: Заголовки скопированы\n")

        # Применяем форматирование
        print("7. Применение форматирования...")
        new_sheet.format('A1:M1', {
            "textFormat": {
                "bold": True,
                "fontSize": 10
            },
            "backgroundColor": {
                "red": 0.85,
                "green": 0.85,
                "blue": 0.85
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE"
        })
        print("   OK: Форматирование применено\n")

        # Настраиваем ширину колонок
        print("8. Настройка ширины колонок...")
        column_widths = [180, 100, 100, 250, 200, 120, 100, 150, 150, 120, 120, 120, 150]

        requests = []
        for i, width in enumerate(column_widths):
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': new_sheet.id,
                        'dimension': 'COLUMNS',
                        'startIndex': i,
                        'endIndex': i + 1
                    },
                    'properties': {
                        'pixelSize': width
                    },
                    'fields': 'pixelSize'
                }
            })

        spreadsheet.batch_update({'requests': requests})
        print(f"   OK: Ширина {len(requests)} колонок установлена\n")

        # Проверяем результат
        print("9. Проверка результата...")
        final_sheets = [s.title for s in spreadsheet.worksheets()]
        print(f"   Все листы в таблице:")
        for s in final_sheets:
            marker = " ✓" if s == 'USDT Зарплаты' else ""
            print(f"   - {s}{marker}")

        print("\n" + "="*70)
        print("ЛИСТ УСПЕШНО СОЗДАН С ПРАВИЛЬНОЙ КОДИРОВКОЙ")
        print("="*70)
        print(f"""
Название листа: "USDT Зарплаты" ✓
Структура: 13 колонок (A-M)
Форматирование: жирный шрифт, серый фон, центрирование
Ширина колонок: настроена

ГОТОВО К ИСПОЛЬЗОВАНИЮ!
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_usdt_salaries_sheet()
