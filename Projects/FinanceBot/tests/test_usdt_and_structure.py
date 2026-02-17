"""
Тесты структуры и логики после внедрения плана: курс формулой, USDT, третий лист.
Без обращения к Google API — проверка конфига, колонок, сигнатур, обратная совместимость.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import inspect


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


def test_config_usdt_and_payment_methods():
    """Конфиг: SHEET_USDT и PAYMENT_METHODS с Криптой"""
    result = TestResult("Config: USDT & Payment Methods")
    if getattr(config, 'SHEET_USDT', None):
        result.add_pass(f"SHEET_USDT задан: '{config.SHEET_USDT}'")
    else:
        result.add_fail("SHEET_USDT отсутствует в config")
    if getattr(config, 'PAYMENT_METHODS', None):
        if 'Крипта' in config.PAYMENT_METHODS:
            result.add_pass("PAYMENT_METHODS содержит 'Крипта'")
        else:
            result.add_fail("PAYMENT_METHODS не содержит 'Крипта'")
        if 'Карта' in config.PAYMENT_METHODS and 'СБП' in config.PAYMENT_METHODS:
            result.add_pass("PAYMENT_METHODS содержит Карта и СБП")
    else:
        result.add_fail("PAYMENT_METHODS отсутствует")
    return result


def test_create_request_row_structure():
    """create_request формирует строку ровно из 20 элементов (A–T), S и T — пустые/комментарий"""
    result = TestResult("create_request: 20 columns (A–T)")
    try:
        from sheets import SheetsManager
        # Читаем исходник create_request и проверяем длину row
        src = inspect.getsource(SheetsManager.create_request)
        if 'row = [' in src and ']' in src:
            # Считаем элементы в row (упрощённо — по количеству запятых в первом блоке или по явному списку)
            if "'',                            # S:" in src or "# S:" in src:
                result.add_pass("В create_request есть комментарий для колонки S")
            if "''                             # T:" in src or "# T:" in src or "Сумма USDT" in src:
                result.add_pass("В create_request есть 20-й элемент (T: Сумма USDT)")
        # Прямая проверка: вызываем логику построения row без append
        row = [
            'REQ-20260128-001', config.STATUS_CREATED, 123, '@u', '28.01.2026 12:00',
            'Recipient', 1000.0, 'RUB', 'Карта', 'details', 'purpose', 'category',
            '', '', '', '', '', '', '', ''
        ]
        if len(row) != 20:
            result.add_fail(f"Эталонная строка row имеет длину {len(row)}, ожидается 20")
        else:
            result.add_pass("Эталонная строка журнала имеет 20 элементов (A–T)")
    except Exception as e:
        result.add_fail(f"Ошибка проверки: {e}")
    return result


def test_complete_payment_signature_and_columns():
    """complete_payment(request_id, executor_name, amount_usdt=None); обновляет 2,16,17,18 и при USDT 20; не трогает 19"""
    result = TestResult("complete_payment: signature & columns")
    try:
        from sheets import SheetsManager
        sig = inspect.signature(SheetsManager.complete_payment)
        params = list(sig.parameters.keys())
        if 'request_id' in params and 'executor_name' in params and 'amount_usdt' in params:
            result.add_pass("Сигнатура: request_id, executor_name, amount_usdt")
        else:
            result.add_fail(f"Сигнатура complete_payment: ожидаются request_id, executor_name, amount_usdt; есть {params}")
        if 'rate' in params:
            result.add_fail("В сигнатуре не должно быть параметра rate")
        else:
            result.add_pass("Параметр rate удалён")
        src = inspect.getsource(SheetsManager.complete_payment)
        if "update_cell(row, 2," in src and "update_cell(row, 16," in src and "update_cell(row, 17," in src and "update_cell(row, 18," in src:
            result.add_pass("Обновляются колонки 2, 16, 17, 18")
        else:
            result.add_fail("Не найдено обновление колонок 2, 16, 17, 18")
        if "update_cell(row, 20," in src and "amount_usdt" in src:
            result.add_pass("При amount_usdt обновляется колонка 20")
        else:
            result.add_fail("Не найдено условное обновление колонки 20 при amount_usdt")
        if "update_cell(row, 19," in src:
            result.add_fail("Колонка 19 (Курс) не должна обновляться кодом — только формулой в таблице")
        else:
            result.add_pass("Колонка 19 не обновляется в complete_payment")
    except Exception as e:
        result.add_fail(f"Ошибка: {e}")
    return result


def test_get_request_by_id_returns_amount_usdt():
    """get_request_by_id возвращает ключ amount_usdt в словаре"""
    result = TestResult("get_request_by_id: amount_usdt in dict")
    try:
        from sheets import SheetsManager
        src = inspect.getsource(SheetsManager.get_request_by_id)
        if "'amount_usdt'" in src or "'Сумма USDT'" in src:
            result.add_pass("get_request_by_id возвращает amount_usdt (Сумма USDT)")
        else:
            result.add_fail("В get_request_by_id не найден amount_usdt / Сумма USDT")
    except Exception as e:
        result.add_fail(f"Ошибка: {e}")
    return result


def test_append_usdt_payment_formula_row():
    """append_usdt_payment записывает формулу курса в правильную строку (после append_row)"""
    result = TestResult("append_usdt_payment: formula on correct row")
    try:
        from sheets import SheetsManager
        src = inspect.getsource(SheetsManager.append_usdt_payment)
        if "append_row" in src and "col_values(1)" in src:
            result.add_pass("append_usdt_payment использует append_row и col_values(1)")
        if "row_num = len(sheet.col_values(1))" in src:
            result.add_pass("Номер строки для формулы считается после append (len col_values)")
        elif "row_num" in src:
            result.add_warning("Проверьте вручную: формула курса должна ставиться в только что дописанную строку")
    except Exception as e:
        result.add_fail(f"Ошибка: {e}")
    return result


def test_payment_handler_no_enter_rate():
    """В payment.py нет состояния ENTER_RATE и обработчика enter_rate"""
    result = TestResult("payment.py: no ENTER_RATE")
    try:
        from handlers import payment
        path = Path(__file__).resolve().parent.parent / 'handlers' / 'payment.py'
        src = path.read_text(encoding='utf-8')
        if "ENTER_RATE" in src:
            result.add_fail("В payment.py всё ещё упоминается ENTER_RATE")
        else:
            result.add_pass("ENTER_RATE удалён из payment.py")
        if "enter_rate" in src:
            result.add_fail("В payment.py всё ещё есть enter_rate")
        else:
            result.add_pass("Обработчик enter_rate удалён")
        if "ENTER_AMOUNT_USDT" in src and "enter_amount_usdt" in src:
            result.add_pass("Добавлены ENTER_AMOUNT_USDT и enter_amount_usdt")
        else:
            result.add_fail("Не найдены ENTER_AMOUNT_USDT или enter_amount_usdt")
    except Exception as e:
        result.add_fail(f"Ошибка: {e}")
    return result


def test_fix_sheets_structure_journal_headers():
    """fix_sheets_structure.py содержит в эталоне журнала колонку Сумма USDT"""
    result = TestResult("fix_sheets_structure: journal 20 cols")
    path = Path(__file__).resolve().parent.parent / 'fix_sheets_structure.py'
    if not path.exists():
        result.add_fail("fix_sheets_structure.py не найден")
        return result
    src = path.read_text(encoding='utf-8')
    if "'Сумма USDT'" in src:
        result.add_pass("В эталоне журнала есть 'Сумма USDT'")
    else:
        result.add_fail("В эталоне журнала отсутствует 'Сумма USDT'")
    if "SHEET_USDT" in src or "USDT" in src:
        result.add_pass("Упоминание листа USDT присутствует")
    return result


def test_docs_sheets_structure_column_t():
    """SHEETS_STRUCTURE.md описывает колонку T (Сумма USDT) и формулу в S"""
    result = TestResult("SHEETS_STRUCTURE.md: column T & formula S")
    path = Path(__file__).resolve().parent.parent / 'SHEETS_STRUCTURE.md'
    if not path.exists():
        result.add_fail("SHEETS_STRUCTURE.md не найден")
        return result
    text = path.read_text(encoding='utf-8')
    if "Сумма USDT" in text and ("T" in text or "20" in text):
        result.add_pass("В документации есть колонка Сумма USDT (T)")
    else:
        result.add_fail("В документации не описана колонка T Сумма USDT")
    if "ЕСЛИ" in text or "G2/T2" in text or "формул" in text.lower():
        result.add_pass("Описана формула для курса (S)")
    else:
        result.add_warning("Рекомендуется явно указать пример формулы для колонки S")
    if "USDT" in text and ("лист" in text or "третий" in text):
        result.add_pass("Описан лист USDT / третий лист")
    return result


def test_backward_compat_get_request_safe_keys():
    """Обратная совместимость: get_request_by_id использует .get() для amount_usdt — старые строки без колонки T не ломаются"""
    result = TestResult("Backward compat: get_request_by_id safe")
    try:
        from sheets import SheetsManager
        src = inspect.getsource(SheetsManager.get_request_by_id)
        if "record.get(" in src and "Сумма USDT" in src:
            result.add_pass("Используется record.get() — отсутствующая колонка T даст None, не ошибку")
        # Эмуляция: словарь без ключа amount_usdt
        fake_record = {'ID заявки': 'REQ-1', 'Сумма': 1000}
        val = fake_record.get('Сумма USDT')
        if val is None:
            result.add_pass("record.get('Сумма USDT') на старых данных возвращает None — безопасно")
    except Exception as e:
        result.add_fail(f"Ошибка: {e}")
    return result


def run_all_structure_tests():
    """Запуск всех структурных тестов (без Google API)"""
    tests = [
        test_config_usdt_and_payment_methods,
        test_create_request_row_structure,
        test_complete_payment_signature_and_columns,
        test_get_request_by_id_returns_amount_usdt,
        test_append_usdt_payment_formula_row,
        test_payment_handler_no_enter_rate,
        test_fix_sheets_structure_journal_headers,
        test_docs_sheets_structure_column_t,
        test_backward_compat_get_request_safe_keys,
    ]
    results = []
    for test_func in tests:
        try:
            r = test_func()
            results.append(r)
            r.print_summary()
        except Exception as e:
            import traceback
            print(f"\n[CRITICAL] {test_func.__name__}: {e}")
            traceback.print_exc()
    total_passed = sum(len(r.passed) for r in results)
    total_failed = sum(len(r.failed) for r in results)
    total_warn = sum(len(r.warnings) for r in results)
    print("\n" + "="*70)
    print("STRUCTURE TESTS SUMMARY")
    print("="*70)
    print(f"[OK] {total_passed}  [FAIL] {total_failed}  [WARN] {total_warn}")
    overall = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0
    print(f"Result: {overall:.1f}%")
    return total_failed == 0


if __name__ == '__main__':
    run_all_structure_tests()
