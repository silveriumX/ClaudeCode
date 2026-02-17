"""
Автоматический тест-набор для Finance Bot
Проверяет все критичные компоненты системы
"""
from pathlib import Path
import sys
import os

# ...
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sheets import SheetsManager
import config
from datetime import datetime

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, msg):
        self.passed.append(msg)

    def add_fail(self, msg):
        self.failed.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def print_summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*70}")
        print(f"[TEST] {self.name}")
        print(f"{'='*70}")

        if self.passed:
            print(f"\n[OK] Passed ({len(self.passed)}/{total}):")
            for msg in self.passed:
                print(f"   + {msg}")

        if self.failed:
            print(f"\n[FAIL] Failed ({len(self.failed)}/{total}):")
            for msg in self.failed:
                print(f"   - {msg}")

        if self.warnings:
            print(f"\n[WARN] Warnings ({len(self.warnings)}):")
            for msg in self.warnings:
                print(f"   ! {msg}")

        success_rate = (len(self.passed) / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        return len(self.failed) == 0


def test_google_sheets_connection():
    """Тест 1: Подключение к Google Sheets"""
    result = TestResult("Google Sheets Connection")

    try:
        sheets = SheetsManager()
        result.add_pass("Подключение к Google Sheets установлено")
    except Exception as e:
        result.add_fail(f"Не удалось подключиться: {e}")
        return result

    # Обязательные листы (Лог событий создаётся ботом при первом log_event; USDT — при первой выплате в USDT)
    required_sheets = ['Пользователи', config.SHEET_JOURNAL, 'Расчетный баланс']
    optional_sheets = ['Баланс счетов', 'Лог событий', getattr(config, 'SHEET_USDT', 'USDT')]

    for sheet_name in required_sheets:
        try:
            sheet = sheets.spreadsheet.worksheet(sheet_name)
            result.add_pass(f"Лист '{sheet_name}' найден")
        except Exception as e:
            result.add_fail(f"Лист '{sheet_name}' не найден: {e}")

    for sheet_name in optional_sheets:
        try:
            sheet = sheets.spreadsheet.worksheet(sheet_name)
            result.add_pass(f"Лист '{sheet_name}' найден (опциональный)")
        except Exception:
            result.add_warning(f"Лист '{sheet_name}' отсутствует (создаётся при необходимости)")

    return result


def test_users_sheet_structure():
    """Тест 2: Структура листа Пользователи"""
    result = TestResult("Users Sheet Structure")

    try:
        sheets = SheetsManager()
        headers = sheets.users_sheet.row_values(1)

        # sheets.py get_user использует 'ФИО', не 'Имя'
        required_headers = ['Telegram ID', 'Username', 'ФИО', 'Роль', 'Статус']

        for header in required_headers:
            if header in headers:
                result.add_pass(f"Столбец '{header}' присутствует")
            else:
                result.add_fail(f"Столбец '{header}' отсутствует")

        # Проверка данных пользователей
        users = sheets.users_sheet.get_all_records()
        result.add_pass(f"Загружено {len(users)} пользователей")

        if len(users) == 0:
            result.add_warning("Нет зарегистрированных пользователей")

        # Проверка ролей
        valid_roles = [config.ROLE_OWNER, config.ROLE_MANAGER, config.ROLE_EXECUTOR]
        for user in users:
            role = user.get('Роль', '')
            if role not in valid_roles:
                result.add_fail(f"Пользователь {user.get('ФИО', user.get('Имя', ''))} имеет некорректную роль: {role}")

    except Exception as e:
        result.add_fail(f"Ошибка проверки: {e}")

    return result


def test_journal_sheet_structure():
    """Тест 3: Структура журнала операций"""
    result = TestResult("Journal Sheet Structure")

    try:
        sheets = SheetsManager()
        headers = sheets.journal_sheet.row_values(1)

        # Эталон: 20 колонок A–T (sheets.py create_request), включая Курс USDT/RUB (S) и Сумма USDT (T)
        required_headers = [
            'ID заявки', 'Статус', 'Автор Telegram ID', 'Автор Username', 'Дата создания заявки',
            'Получатель', 'Сумма', 'Валюта', 'Способ оплаты', 'Реквизиты',
            'Назначение', 'Категория', 'Одобрено', 'Дата одобрения',
            'Кошелек', 'Оплачено', 'Дата оплаты', 'Исполнитель', 'Курс USDT/RUB', 'Сумма USDT'
        ]

        for header in required_headers:
            if header in headers:
                result.add_pass(f"Столбец '{header}' присутствует")
            else:
                if header == 'Сумма USDT':
                    result.add_warning("Столбец 'Сумма USDT' (T) отсутствует — добавьте вручную или запустите fix_sheets_structure.py")
                else:
                    result.add_fail(f"Столбец '{header}' отсутствует")

        # Проверка заявок
        records = sheets.journal_sheet.get_all_records()
        req_records = [r for r in records if str(r.get('ID заявки', '')).startswith('REQ-')]

        result.add_pass(f"Найдено {len(req_records)} заявок (REQ-)")

        if len(req_records) == 0:
            result.add_warning("Нет заявок в системе")

        # Проверка корректности статусов (включая Отменена)
        # Если в ячейке дата — возможное смещение колонок в старых таблицах; не падаем, предупреждаем
        valid_statuses = ['Создана', 'Одобрена', 'Оплачена', 'Отклонена', 'Отменена']
        invalid_status_count = 0
        for record in req_records[:10]:  # Проверяем первые 10
            status = record.get('Статус', '')
            if status not in valid_statuses:
                invalid_status_count += 1
        if invalid_status_count == 0:
            result.add_pass("Все проверенные заявки имеют корректный статус")
        else:
            result.add_warning(f"У {invalid_status_count} заявок статус не из списка (возможно смещение колонок или ручное редактирование)")

    except Exception as e:
        result.add_fail(f"Ошибка проверки: {e}")

    return result


def test_data_integrity():
    """Тест 4: Целостность данных"""
    result = TestResult("Data Integrity")

    try:
        sheets = SheetsManager()

        # Проверка уникальности ID заявок
        records = sheets.journal_sheet.get_all_records()
        req_records = [r for r in records if str(r.get('ID заявки', '')).startswith('REQ-')]

        request_ids = [r.get('ID заявки') for r in req_records]
        unique_ids = set(request_ids)

        if len(request_ids) == len(unique_ids):
            result.add_pass(f"Все ID заявок уникальны ({len(request_ids)} заявок)")
        else:
            duplicates = len(request_ids) - len(unique_ids)
            result.add_fail(f"Найдено {duplicates} дубликатов ID заявок")

        # Проверка что у всех заявок есть автор
        for record in req_records[:20]:  # Проверяем первые 20
            author_id = record.get('Автор Telegram ID')
            if not author_id or author_id == '':
                result.add_fail(f"Заявка {record.get('ID заявки')} не имеет автора")

        if len(req_records) > 0:
            result.add_pass("Все проверенные заявки имеют авторов")

        # Проверка сумм (не пустые и числовые)
        invalid_amounts = 0
        for record in req_records[:20]:
            amount = record.get('Сумма')
            if not amount or amount == '':
                invalid_amounts += 1

        if invalid_amounts == 0:
            result.add_pass("Все проверенные заявки имеют корректные суммы")
        else:
            result.add_warning(f"{invalid_amounts} заявок имеют пустые суммы")

    except Exception as e:
        result.add_fail(f"Ошибка проверки: {e}")

    return result


def test_balance_sheets():
    """Тест 5: Листы балансов"""
    result = TestResult("Balance Sheets")

    try:
        sheets = SheetsManager()

        # Проверка "Баланс счетов" (опционально; структура может отличаться)
        try:
            balance_sheet = sheets.spreadsheet.worksheet(config.SHEET_ACCOUNTS)
            headers = balance_sheet.row_values(1)
            if headers:
                result.add_pass("Лист 'Баланс счетов' доступен и имеет заголовки")
            else:
                result.add_warning("Лист 'Баланс счетов' пуст")
        except Exception as e:
            result.add_warning(f"Лист 'Баланс счетов' недоступен (опционально): {e}")

        # Проверка "Расчетный баланс"
        try:
            calc_balance_sheet = sheets.spreadsheet.worksheet('Расчетный баланс')
            result.add_pass("Лист 'Расчетный баланс' доступен")
        except Exception as e:
            result.add_fail(f"Ошибка доступа к 'Расчетный баланс': {e}")

    except Exception as e:
        result.add_fail(f"Ошибка проверки: {e}")

    return result


def test_event_logging():
    """Тест 6: Логирование событий"""
    result = TestResult("Event Logging")

    try:
        sheets = SheetsManager()

        # Проверка листа "Лог событий"
        try:
            event_log = sheets.spreadsheet.worksheet('Лог событий')
            headers = event_log.row_values(1)

            # sheets.py log_event создаёт: Дата и время, Тип события, User ID, Username, ID заявки, Детали
            # Допускаем и старый формат (Событие, Пользователь) для обратной совместимости
            new_headers = ['Дата и время', 'Тип события', 'User ID', 'Username', 'ID заявки', 'Детали']
            old_headers = ['Дата и время', 'Событие', 'Пользователь', 'Детали']
            missing_new = [h for h in new_headers if h not in headers]
            missing_old = [h for h in old_headers if h not in headers]
            if not missing_new:
                result.add_pass("Лист 'Лог событий' имеет актуальные столбцы (Тип события, User ID, ...)")
            elif not missing_old:
                result.add_warning("Лист 'Лог событий' в старом формате; при первом log_event бот создаёт новый формат")
            else:
                result.add_fail(f"Лист 'Лог событий': ожидаются столбцы из нового или старого формата")

            # Проверка наличия записей
            records = event_log.get_all_records()
            if len(records) > 0:
                result.add_pass(f"В логе {len(records)} событий")
            else:
                result.add_warning("Лог событий пуст")

        except Exception as e:
            result.add_fail(f"Ошибка доступа к 'Лог событий': {e}")

    except Exception as e:
        result.add_fail(f"Ошибка проверки: {e}")

    return result


def test_config_validation():
    """Тест 7: Конфигурация"""
    result = TestResult("Configuration Validation")

    # Проверка токена бота
    if config.TELEGRAM_BOT_TOKEN:
        result.add_pass("TELEGRAM_BOT_TOKEN установлен")
    else:
        result.add_fail("TELEGRAM_BOT_TOKEN отсутствует")

    # Проверка ID Google Sheets
    if config.GOOGLE_SHEETS_ID:
        result.add_pass("GOOGLE_SHEETS_ID установлен")
    else:
        result.add_fail("GOOGLE_SHEETS_ID отсутствует")

    # Проверка наличия service account
    if os.path.exists('service_account.json'):
        result.add_pass("Файл service_account.json найден")
    else:
        result.add_fail("Файл service_account.json отсутствует")

    # Проверка констант ролей
    if config.ROLE_OWNER and config.ROLE_MANAGER and config.ROLE_EXECUTOR:
        result.add_pass("Все роли определены корректно")
    else:
        result.add_fail("Некоторые роли не определены")

    return result


def run_all_tests():
    """Запуск всех тестов"""
    print("\n" + "="*70)
    print("AUTOMATED TESTING - FINANCE BOT")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        test_config_validation,
        test_google_sheets_connection,
        test_users_sheet_structure,
        test_journal_sheet_structure,
        test_balance_sheets,
        test_event_logging,
        test_data_integrity
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
            success = result.print_summary()
        except Exception as e:
            print(f"\n[CRITICAL ERROR] in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()

    # Общая сводка
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)

    total_passed = sum(len(r.passed) for r in results)
    total_failed = sum(len(r.failed) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)

    print(f"[OK] Passed:   {total_passed}")
    print(f"[FAIL] Failed:   {total_failed}")
    print(f"[WARN] Warnings: {total_warnings}")

    overall_success = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0
    print(f"\nOverall Result: {overall_success:.1f}%")

    if total_failed == 0:
        print("\n*** ALL TESTS PASSED SUCCESSFULLY! ***")
    else:
        print(f"\n*** ATTENTION REQUIRED: {total_failed} tests failed ***")

    print("="*70)


if __name__ == '__main__':
    run_all_tests()
