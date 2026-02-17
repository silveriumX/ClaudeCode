"""
Финальная проверка всех заявок
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Projects', 'FinanceBot'))

from sheets import SheetsManager
import config

sheets = SheetsManager()

print("="*70)
print("ПРОВЕРКА ЗАЯВОК")
print("="*70 + "\n")

print("1. Листы в таблице:")
all_sheets = [s.title for s in sheets.spreadsheet.worksheets()]
for i, s in enumerate(all_sheets, 1):
    marker = " OK" if s in ['Основные', 'Разные выплаты', 'USDT', 'USDT Зарплаты'] else ""
    print(f"  {i}. {s}{marker}")

print(f"\n2. Заявки пользователя 8127547204:")
user_id = '8127547204'

created = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=user_id)
print(f"  Создано: {len(created)}")
for r in created[:5]:
    print(f"    - {r.get('request_id')}: {r.get('amount')} {r.get('currency')} [{r.get('sheet_name')}]")

paid = sheets.get_requests_by_status(config.STATUS_PAID, author_id=user_id)
print(f"\n  Оплачено: {len(paid)}")
for r in paid[:5]:
    print(f"    - {r.get('request_id')}: {r.get('amount')} {r.get('currency')} [{r.get('sheet_name')}]")

print(f"\n3. Всего в системе:")
all_created = sheets.get_requests_by_status(config.STATUS_CREATED)
all_paid = sheets.get_requests_by_status(config.STATUS_PAID)
print(f"  Создано: {len(all_created)}")
print(f"  Оплачено: {len(all_paid)}")

print(f"\n4. Тест поиска оплаченной заявки:")
if all_paid:
    test_req = all_paid[0]
    req_id = test_req.get('request_id')
    print(f"  Test ID: {req_id}")
    print(f"  Amount: {test_req.get('amount')} {test_req.get('currency')}")
    print(f"  Sheet: {test_req.get('sheet_name')}")

    print(f"\n  Поиск через get_request_by_request_id...")
    found = sheets.get_request_by_request_id(req_id)
    if found:
        print(f"  OK: НАЙДЕНА! Лист: {found.get('sheet_name')}")
    else:
        print(f"  ERROR: НЕ НАЙДЕНА!")
else:
    print("  Нет оплаченных заявок")

print("\n" + "="*70)
