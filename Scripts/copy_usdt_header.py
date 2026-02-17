"""
Копирование шапки и форматирования из USDT в USDT Зарплаты
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Projects', 'FinanceBot'))

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config

def copy_usdt_header():
    """Скопировать шапку и форматирование из USDT в USDT Зарплаты"""
    try:
        # Подключаемся
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config.GOOGLE_SHEETS_ID)

        print("="*70)
        print("КОПИРОВАНИЕ ШАПКИ USDT -> USDT ЗАРПЛАТЫ")
        print("="*70 + "\n")

        # Получаем исходный лист USDT
        print("1. Чтение листа USDT...")
        usdt_sheet = spreadsheet.worksheet('USDT')

        # Получаем первую строку (заголовки)
        headers = usdt_sheet.row_values(1)
        print(f"   Заголовков найдено: {len(headers)}")
        print(f"   Заголовки: {', '.join(headers)}\n")

        # Получаем целевой лист
        print("2. Открытие листа USDT Зарплаты...")
        target_sheet = spreadsheet.worksheet('USDT Зарплаты')
        print(f"   OK: Лист найден\n")

        # Очищаем первую строку на всякий случай
        print("3. Очистка первой строки...")
        target_sheet.batch_clear(['A1:M1'])
        print("   OK: Очищено\n")

        # Копируем заголовки
        print("4. Копирование заголовков...")
        target_sheet.update(values=[headers], range_name='A1:M1')
        print("   OK: Заголовки скопированы\n")

        # Копируем форматирование
        print("5. Применение форматирования...")

        # Применяем форматирование: жирный шрифт + серый фон
        target_sheet.format('A1:M1', {
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

        # Настройка ширины колонок
        print("6. Настройка ширины колонок...")
        column_widths = {
            'A': 180,  # ID заявки
            'B': 100,  # Дата
            'C': 100,  # Сумма USDT
            'D': 250,  # Адрес кошелька
            'E': 200,  # Назначение
            'F': 120,  # Категория
            'G': 100,  # Статус
            'H': 150,  # ID транзакции
            'I': 150,  # Название аккаунта
            'J': 120,  # Исполнитель
            'K': 120,  # Telegram ID
            'L': 120,  # Username
            'M': 150,  # Полное имя
        }

        requests = []
        for i, (col, width) in enumerate(column_widths.items()):
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': target_sheet.id,
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
        print("7. Проверка результата...")
        check_headers = target_sheet.row_values(1)
        print(f"   Заголовков в USDT Зарплаты: {len(check_headers)}")
        print(f"   Первые 5: {', '.join(check_headers[:5])}\n")

        print("="*70)
        print("КОПИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")
        print("="*70)
        print(f"""
СТРУКТУРА ЛИСТА "USDT ЗАРПЛАТЫ":

{chr(10).join([f'{chr(65+i)}: {h}' for i, h in enumerate(headers)])}

Форматирование применено:
- Жирный шрифт
- Серый фон
- Выравнивание по центру
- Ширина колонок настроена

Лист готов к использованию!
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    copy_usdt_header()
