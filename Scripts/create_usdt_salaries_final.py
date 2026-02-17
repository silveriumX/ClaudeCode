"""
Финальное создание листа USDT Зарплаты
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Projects', 'FinanceBot'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'Projects', 'FinanceBot', '.env'))

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Читаем ID из .env
SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
SERVICE_ACCOUNT = os.path.join(os.path.dirname(__file__), '..', 'Projects', 'FinanceBot', 'service_account.json')

print(f"Sheets ID: {SHEETS_ID}")
print(f"Service account: {SERVICE_ACCOUNT}")

# Подключаемся
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT, scope)
client = gspread.authorize(creds)

try:
    spreadsheet = client.open_by_key(SHEETS_ID)
    print(f"Spreadsheet found: {spreadsheet.title}\n")

    # Список листов
    all_sheets = spreadsheet.worksheets()
    print("Current sheets:")
    for i, s in enumerate(all_sheets, 1):
        print(f"  {i}. {s.title}")

    # Проверяем USDT
    try:
        usdt = spreadsheet.worksheet('USDT')
        headers = usdt.row_values(1)
        print(f"\nUSDT sheet found, headers: {len(headers)}")
    except:
        print("\nERROR: USDT sheet not found!")
        sys.exit(1)

    # Удаляем старые кракозябры
    print("\nCleaning old sheets...")
    for sheet in all_sheets:
        if 'зарплат' in sheet.title.lower() and sheet.title != 'USDT':
            try:
                print(f"  Deleting: {sheet.title}")
                spreadsheet.del_worksheet(sheet)
            except:
                pass

    # Создаём новый лист
    print("\nCreating USDT Зарплаты...")

    # Используем batch_update для точного контроля
    body = {
        'requests': [{
            'addSheet': {
                'properties': {
                    'title': 'USDT Зарплаты',
                    'gridProperties': {
                        'rowCount': 100,
                        'columnCount': 13
                    }
                }
            }
        }]
    }

    result = spreadsheet.batch_update(body)
    new_sheet_id = result['replies'][0]['addSheet']['properties']['sheetId']
    print(f"  Sheet created with ID: {new_sheet_id}")

    # Получаем лист
    target = spreadsheet.worksheet('USDT Зарплаты')
    print(f"  Sheet found: {target.title}")

    # Копируем заголовки
    print("\nCopying headers...")
    target.update(values=[headers], range_name='A1')
    print("  Headers copied")

    # Форматирование
    print("\nApplying formatting...")
    target.format('A1:M1', {
        'textFormat': {'bold': True, 'fontSize': 10},
        'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85},
        'horizontalAlignment': 'CENTER',
        'verticalAlignment': 'MIDDLE'
    })
    print("  Formatting applied")

    # Ширина колонок
    print("\nSetting column widths...")
    widths = [180, 100, 100, 250, 200, 120, 100, 150, 150, 120, 120, 120, 150]
    requests = []
    for i, width in enumerate(widths):
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': new_sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': i,
                    'endIndex': i + 1
                },
                'properties': {'pixelSize': width},
                'fields': 'pixelSize'
            }
        })

    spreadsheet.batch_update({'requests': requests})
    print(f"  {len(requests)} columns configured")

    # Проверка
    print("\nFinal check:")
    check_headers = target.row_values(1)
    print(f"  Headers count: {len(check_headers)}")
    print(f"  First 3: {check_headers[:3]}")

    print("\nSUCCESS: Sheet USDT Зарплаты is ready!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
