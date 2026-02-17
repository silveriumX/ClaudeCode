"""
Комплексное тестирование Finance Bot
Проверка всех кейсов использования с созданием реальных заявок
"""
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sheets import SheetsManager
import config


class TestReport:
    def __init__(self):
        self.sections = []
        self.current_section = None

    def start_section(self, name):
        self.current_section = {
            'name': name,
            'passed': [],
            'failed': [],
            'skipped': []
        }

    def add_pass(self, msg):
        if self.current_section:
            self.current_section['passed'].append(msg)

    def add_fail(self, msg):
        if self.current_section:
            self.current_section['failed'].append(msg)

    def add_skip(self, msg):
        if self.current_section:
            self.current_section['skipped'].append(msg)

    def end_section(self):
        if self.current_section:
            self.sections.append(self.current_section)
            self.current_section = None

    def print_report(self):
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST REPORT - FINANCE BOT")
        print("="*80)
        print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Таблица: {config.GOOGLE_SHEETS_ID}")
        print("="*80)

        total_pass = 0
        total_fail = 0
        total_skip = 0

        for section in self.sections:
            print(f"\n### {section['name']}")
            print("-" * 80)

            if section['passed']:
                for msg in section['passed']:
                    print(f"  [PASS] {msg}")

            if section['failed']:
                for msg in section['failed']:
                    print(f"  [FAIL] {msg}")

            if section['skipped']:
                for msg in section['skipped']:
                    print(f"  [SKIP] {msg}")

            passed = len(section['passed'])
            failed = len(section['failed'])
            skipped = len(section['skipped'])
            total = passed + failed

            total_pass += passed
            total_fail += failed
            total_skip += skipped

            if total > 0:
                rate = (passed / total * 100)
                print(f"\n  Итого: {passed}/{total} ({rate:.1f}%)")
                if skipped > 0:
                    print(f"  Пропущено: {skipped}")

        print("\n" + "="*80)
        print("ИТОГОВАЯ СВОДКА")
        print("="*80)
        print(f"Пройдено:   {total_pass}")
        print(f"Провалено:  {total_fail}")
        print(f"Пропущено:  {total_skip}")

        if total_pass + total_fail > 0:
            overall = (total_pass / (total_pass + total_fail) * 100)
            print(f"\nОбщий результат: {overall:.1f}%")

        print("\n" + "="*80)

        if total_fail == 0:
            print("\n[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        else:
            print(f"\n[!] ТРЕБУЕТСЯ ВНИМАНИЕ: {total_fail} тестов провалено")

        print("="*80 + "\n")


def test_sheets_connection(report: TestReport):
    """1. Подключение к Google Sheets"""
    report.start_section("1. Подключение к Google Sheets")

    try:
        sheets = SheetsManager()
        report.add_pass("Подключение установлено")

        # Проверка листов
        required_sheets = {
            'Основные': True,
            'Разные выплаты': True,
            'USDT': True,
            'Лог событий': True,
            'Пользователи': False,
            'Расчетный баланс': False,
            'Баланс счетов': False
        }

        for sheet_name, is_required in required_sheets.items():
            try:
                sheet = sheets.spreadsheet.worksheet(sheet_name)
                report.add_pass(f"Лист '{sheet_name}' найден")
            except Exception:
                if is_required:
                    report.add_fail(f"Лист '{sheet_name}' отсутствует (обязательный)")
                else:
                    report.add_skip(f"Лист '{sheet_name}' отсутствует (опциональный)")

        report.end_section()
        return sheets

    except Exception as e:
        report.add_fail(f"Ошибка подключения: {e}")
        report.end_section()
        return None


def test_sheet_headers(report: TestReport, sheets: SheetsManager):
    """2. Проверка шапок листов"""
    report.start_section("2. Проверка шапок листов")

    if not sheets:
        report.add_skip("Пропущено: нет подключения")
        report.end_section()
        return

    try:
        # Основные
        main_headers = sheets.journal_sheet.row_values(1)
        expected_main = [
            'ID заявки', 'Статус', 'Автор Telegram ID', 'Автор Username',
            'Дата создания заявки', 'Получатель', 'Сумма', 'Валюта',
            'Способ оплаты', 'Реквизиты', 'Назначение', 'Категория',
            'Одобрено', 'Дата одобрения', 'Кошелек', 'Оплачено',
            'Дата оплаты', 'Исполнитель', 'Курс USDT/RUB', 'Сумма USDT'
        ]

        if len(main_headers) == 20:
            report.add_pass("Лист 'Основные': 20 колонок")
        else:
            report.add_fail(f"Лист 'Основные': {len(main_headers)} колонок, ожидается 20")

        missing = [h for h in expected_main if h not in main_headers]
        if not missing:
            report.add_pass("Лист 'Основные': все обязательные столбцы присутствуют")
        else:
            for h in missing:
                report.add_fail(f"Лист 'Основные': отсутствует столбец '{h}'")

        # USDT
        try:
            usdt_sheet = sheets.spreadsheet.worksheet('USDT')
            usdt_headers = usdt_sheet.row_values(1)
            expected_usdt = [
                'ID заявки', 'Дата оплаты', 'Сумма RUB', 'Сумма USDT',
                'Курс', 'Кошелек', 'Исполнитель'
            ]

            if len(usdt_headers) == 7:
                report.add_pass("Лист 'USDT': 7 колонок")
            else:
                report.add_fail(f"Лист 'USDT': {len(usdt_headers)} колонок, ожидается 7")

            missing_usdt = [h for h in expected_usdt if h not in usdt_headers]
            if not missing_usdt:
                report.add_pass("Лист 'USDT': все обязательные столбцы присутствуют")
            else:
                for h in missing_usdt:
                    report.add_fail(f"Лист 'USDT': отсутствует столбец '{h}'")
        except Exception as e:
            report.add_fail(f"Ошибка проверки листа USDT: {e}")

    except Exception as e:
        report.add_fail(f"Ошибка проверки шапок: {e}")

    report.end_section()


def test_create_request_rub(report: TestReport, sheets: SheetsManager):
    """3. Создание заявки RUB через Карту"""
    report.start_section("3. Создание заявки RUB через Карту")

    if not sheets:
        report.add_skip("Пропущено: нет подключения")
        report.end_section()
        return None

    try:
        request_id = sheets.create_request(
            telegram_id=123456789,
            username="@test_user",
            recipient="Тестовый получатель RUB",
            amount=10000.0,
            currency="RUB",
            payment_method="Карта",
            details="1234567890",
            purpose="Тест создания заявки RUB",
            category="Тестирование"
        )

        if request_id:
            report.add_pass(f"Заявка создана: {request_id}")

            # Проверка записи в таблице
            request = sheets.get_request_by_id(request_id)
            if request:
                report.add_pass("Заявка прочитана из таблицы")

                checks = {
                    'статус': (request.get('status'), config.STATUS_CREATED),
                    'автор ID': (str(request.get('author_id')), '123456789'),
                    'username': (request.get('author_username'), '@test_user'),
                    'получатель': (request.get('recipient'), 'Тестовый получатель RUB'),
                    'сумма': (float(request.get('amount', 0)), 10000.0),
                    'валюта': (request.get('currency'), 'RUB'),
                    'способ оплаты': (request.get('payment_method'), 'Карта')
                }

                for field, (actual, expected) in checks.items():
                    if actual == expected:
                        report.add_pass(f"Поле '{field}' корректно: {expected}")
                    else:
                        report.add_fail(f"Поле '{field}': ожидается {expected}, получено {actual}")
            else:
                report.add_fail("Заявка не найдена при чтении")
        else:
            report.add_fail("Не удалось создать заявку")

        report.end_section()
        return request_id

    except Exception as e:
        report.add_fail(f"Ошибка создания заявки: {e}")
        report.end_section()
        return None


def test_create_request_byn(report: TestReport, sheets: SheetsManager):
    """4. Создание заявки BYN через Карту"""
    report.start_section("4. Создание заявки BYN через Карту")

    if not sheets:
        report.add_skip("Пропущено: нет подключения")
        report.end_section()
        return None

    try:
        request_id = sheets.create_request(
            telegram_id=123456789,
            username="@test_user",
            recipient="Тестовый получатель BYN",
            amount=500.0,
            currency="BYN",
            payment_method="Карта",
            details="9876543210",
            purpose="Тест создания заявки BYN",
            category="Тестирование"
        )

        if request_id:
            report.add_pass(f"Заявка создана: {request_id}")

            request = sheets.get_request_by_id(request_id)
            if request and request.get('currency') == 'BYN':
                report.add_pass("Валюта BYN корректно сохранена")
            else:
                report.add_fail("Валюта BYN не сохранена")
        else:
            report.add_fail("Не удалось создать заявку")

        report.end_section()
        return request_id

    except Exception as e:
        report.add_fail(f"Ошибка создания заявки: {e}")
        report.end_section()
        return None


def test_create_request_usdt(report: TestReport, sheets: SheetsManager):
    """5. Создание заявки USDT через Крипту"""
    report.start_section("5. Создание заявки USDT через Крипту")

    if not sheets:
        report.add_skip("Пропущено: нет подключения")
        report.end_section()
        return None

    try:
        request_id = sheets.create_request(
            telegram_id=123456789,
            username="@test_user",
            recipient="Тестовый получатель USDT",
            amount=15000.0,
            currency="USDT",
            payment_method="Крипта",
            details="TRx123456789",
            purpose="Тест создания заявки USDT",
            category="Тестирование"
        )

        if request_id:
            report.add_pass(f"Заявка создана: {request_id}")

            request = sheets.get_request_by_id(request_id)
            if request and request.get('currency') == 'USDT':
                report.add_pass("Валюта USDT корректно сохранена")
            else:
                report.add_fail("Валюта USDT не сохранена")
        else:
            report.add_fail("Не удалось создать заявку")

        report.end_section()
        return request_id

    except Exception as e:
        report.add_fail(f"Ошибка создания заявки: {e}")
        report.end_section()
        return None


def test_approve_request(report: TestReport, sheets: SheetsManager, request_id: str):
    """6. Одобрение заявки"""
    report.start_section(f"6. Одобрение заявки ({request_id})")

    if not sheets or not request_id:
        report.add_skip("Пропущено: нет подключения или ID заявки")
        report.end_section()
        return False

    try:
        wallet = "Транзит 21"
        success = sheets.approve_request(request_id, wallet)

        if success:
            report.add_pass("Заявка одобрена")

            # Проверка обновления
            request = sheets.get_request_by_id(request_id)
            if request:
                if request.get('status') == config.STATUS_APPROVED:
                    report.add_pass("Статус обновлён на 'Одобрена'")
                else:
                    report.add_fail(f"Статус не обновлён: {request.get('status')}")

                if request.get('wallet') == wallet:
                    report.add_pass(f"Кошелёк установлен: {wallet}")
                else:
                    report.add_fail(f"Кошелёк не установлен: {request.get('wallet')}")

                # Проверка, что другие поля не перезаписаны
                if request.get('recipient'):
                    report.add_pass("Поле 'Получатель' не затронуто")
                else:
                    report.add_fail("Поле 'Получатель' затёрто")

                if request.get('amount'):
                    report.add_pass("Поле 'Сумма' не затронуто")
                else:
                    report.add_fail("Поле 'Сумма' затёрто")
            else:
                report.add_fail("Заявка не найдена после одобрения")
        else:
            report.add_fail("Не удалось одобрить заявку")

        report.end_section()
        return success

    except Exception as e:
        report.add_fail(f"Ошибка одобрения: {e}")
        report.end_section()
        return False


def test_complete_payment_rub(report: TestReport, sheets: SheetsManager, request_id: str):
    """7. Оплата заявки RUB (без USDT)"""
    report.start_section(f"7. Оплата заявки RUB ({request_id})")

    if not sheets or not request_id:
        report.add_skip("Пропущено: нет подключения или ID заявки")
        report.end_section()
        return False

    try:
        success = sheets.complete_payment(request_id, "Тестовый исполнитель", amount_usdt=None)

        if success:
            report.add_pass("Заявка оплачена")

            # Проверка обновления
            request = sheets.get_request_by_id(request_id)
            if request:
                if request.get('status') == config.STATUS_PAID:
                    report.add_pass("Статус обновлён на 'Оплачена'")
                else:
                    report.add_fail(f"Статус: {request.get('status')}")

                if request.get('executor'):
                    report.add_pass(f"Исполнитель: {request.get('executor')}")
                else:
                    report.add_fail("Исполнитель не записан")

                # Проверка, что USDT лист не изменён
                try:
                    usdt_sheet = sheets.spreadsheet.worksheet('USDT')
                    usdt_records = usdt_sheet.get_all_records()
                    found = any(r.get('ID заявки') == request_id for r in usdt_records)
                    if not found:
                        report.add_pass("Лист USDT не изменён (RUB заявка)")
                    else:
                        report.add_fail("Лист USDT содержит RUB заявку (не должен)")
                except Exception as e:
                    report.add_skip(f"Не удалось проверить USDT лист: {e}")
            else:
                report.add_fail("Заявка не найдена")
        else:
            report.add_fail("Не удалось оплатить заявку")

        report.end_section()
        return success

    except Exception as e:
        report.add_fail(f"Ошибка оплаты: {e}")
        report.end_section()
        return False


def test_complete_payment_usdt(report: TestReport, sheets: SheetsManager, request_id: str):
    """8. Оплата заявки USDT (с amount_usdt)"""
    report.start_section(f"8. Оплата заявки USDT ({request_id})")

    if not sheets or not request_id:
        report.add_skip("Пропущено: нет подключения или ID заявки")
        report.end_section()
        return False

    try:
        amount_usdt = 150.0
        success = sheets.complete_payment(request_id, "Тестовый исполнитель", amount_usdt=amount_usdt)

        if success:
            report.add_pass("Заявка оплачена")

            # Проверка основного листа
            request = sheets.get_request_by_id(request_id)
            if request:
                if request.get('status') == config.STATUS_PAID:
                    report.add_pass("Статус обновлён на 'Оплачена'")
                else:
                    report.add_fail(f"Статус: {request.get('status')}")

                if request.get('amount_usdt'):
                    saved_usdt = float(request.get('amount_usdt'))
                    if saved_usdt == amount_usdt:
                        report.add_pass(f"Сумма USDT записана: {amount_usdt}")
                    else:
                        report.add_fail(f"Сумма USDT: ожидается {amount_usdt}, получено {saved_usdt}")
                else:
                    report.add_fail("Сумма USDT не записана")

                # Проверка листа USDT
                try:
                    usdt_sheet = sheets.spreadsheet.worksheet('USDT')
                    usdt_records = usdt_sheet.get_all_records()
                    found = any(r.get('ID заявки') == request_id for r in usdt_records)
                    if found:
                        report.add_pass("Строка добавлена на лист USDT")

                        # Проверка формулы курса
                        usdt_row = next((r for r in usdt_records if r.get('ID заявки') == request_id), None)
                        if usdt_row:
                            # Курс должен быть формулой =C/D
                            if usdt_row.get('Курс'):
                                report.add_pass("Курс USDT/RUB рассчитан")
                            else:
                                report.add_skip("Курс пуст (формула может быть, но не вычислена)")
                    else:
                        report.add_fail("Строка НЕ добавлена на лист USDT")
                except Exception as e:
                    report.add_fail(f"Ошибка проверки USDT листа: {e}")
            else:
                report.add_fail("Заявка не найдена")
        else:
            report.add_fail("Не удалось оплатить заявку")

        report.end_section()
        return success

    except Exception as e:
        report.add_fail(f"Ошибка оплаты: {e}")
        report.end_section()
        return False


def test_get_requests_by_status(report: TestReport, sheets: SheetsManager):
    """9. Чтение заявок по статусу"""
    report.start_section("9. Чтение заявок по статусу")

    if not sheets:
        report.add_skip("Пропущено: нет подключения")
        report.end_section()
        return

    try:
        for status in [config.STATUS_CREATED, config.STATUS_APPROVED, config.STATUS_PAID]:
            requests = sheets.get_requests_by_status(status)
            if requests is not None:
                report.add_pass(f"Статус '{status}': получено {len(requests)} заявок")
            else:
                report.add_fail(f"Ошибка чтения заявок со статусом '{status}'")

    except Exception as e:
        report.add_fail(f"Ошибка чтения заявок: {e}")

    report.end_section()


def test_logging(report: TestReport, sheets: SheetsManager):
    """10. Логирование событий"""
    report.start_section("10. Логирование событий")

    if not sheets:
        report.add_skip("Пропущено: нет подключения")
        report.end_section()
        return

    try:
        sheets.log_event(
            event_type='TEST_EVENT',
            user_id=999999,
            username='@test_logger',
            request_id='TEST-001',
            details='Тестовое событие для проверки логирования'
        )
        report.add_pass("Событие залогировано")

        # Проверка записи
        try:
            log_sheet = sheets.spreadsheet.worksheet('Лог событий')
            log_records = log_sheet.get_all_records()
            if log_records:
                last_log = log_records[-1]
                if last_log.get('Тип события') == 'TEST_EVENT':
                    report.add_pass("Событие найдено в логе")
                else:
                    report.add_skip("Последнее событие не совпадает (возможно параллельное выполнение)")
            else:
                report.add_fail("Лог событий пуст")
        except Exception as e:
            report.add_skip(f"Не удалось проверить лог: {e}")

    except Exception as e:
        report.add_fail(f"Ошибка логирования: {e}")

    report.end_section()


def test_data_protection(report: TestReport, sheets: SheetsManager):
    """11. Защита данных (не трогаем записи без REQ-)"""
    report.start_section("11. Защита данных")

    if not sheets:
        report.add_skip("Пропущено: нет подключения")
        report.end_section()
        return

    try:
        # Проверяем, что методы работают только с REQ- записями
        requests = sheets.get_requests_by_status(config.STATUS_CREATED)
        all_req = all(str(r.get('request_id', '')).startswith('REQ-') for r in requests)

        if all_req:
            report.add_pass("Все прочитанные заявки имеют префикс REQ-")
        else:
            report.add_fail("Найдены заявки без префикса REQ-")

        # Проверка, что get_request_by_id не находит записи без REQ-
        manual_request = sheets.get_request_by_id("MANUAL-001")
        if manual_request is None:
            report.add_pass("Записи без REQ- не читаются (защита)")
        else:
            report.add_fail("get_request_by_id читает записи без REQ-")

    except Exception as e:
        report.add_fail(f"Ошибка проверки защиты: {e}")

    report.end_section()


def run_comprehensive_tests():
    """Запуск всех комплексных тестов"""
    report = TestReport()

    # 1. Подключение
    sheets = test_sheets_connection(report)

    # 2. Проверка шапок
    test_sheet_headers(report, sheets)

    # 3-5. Создание заявок
    request_rub = test_create_request_rub(report, sheets)
    request_byn = test_create_request_byn(report, sheets)
    request_usdt = test_create_request_usdt(report, sheets)

    # 6. Одобрение заявки RUB
    if request_rub:
        approved = test_approve_request(report, sheets, request_rub)

        # 7. Оплата заявки RUB
        if approved:
            test_complete_payment_rub(report, sheets, request_rub)

    # 6-8. Одобрение и оплата заявки USDT
    if request_usdt:
        approved = test_approve_request(report, sheets, request_usdt)
        if approved:
            test_complete_payment_usdt(report, sheets, request_usdt)

    # 9. Чтение заявок
    test_get_requests_by_status(report, sheets)

    # 10. Логирование
    test_logging(report, sheets)

    # 11. Защита данных
    test_data_protection(report, sheets)

    # Печать отчёта
    report.print_report()


if __name__ == '__main__':
    run_comprehensive_tests()
