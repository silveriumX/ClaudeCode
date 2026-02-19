"""
Тесты для USDT-платёжных фиксов (февраль 2026).

Покрывают изменения:
1. sheets._find_columns_by_headers: 'id транзакции' → deal_id
2. payment.enter_account: пропуск USDT-вопроса для USDT-заявок
3. payment.handle_receipt_upload: TronScan URL как чек
4. payment.get_payment_conversation_handler: TEXT handler в UPLOAD_RECEIPT
5. payment.mark_paid_callback: USDT-специфичный промпт

Запуск: python -m pytest tests/test_usdt_fixes.py -v
Или:    python tests/test_usdt_fixes.py
"""
import asyncio
import inspect
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

PASS = "[ OK ]"
FAIL = "[FAIL]"
WARN = "[WARN]"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def ok(self, msg: str):
        self.passed.append(msg)

    def fail(self, msg: str):
        self.failed.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def print_summary(self) -> bool:
        total = len(self.passed) + len(self.failed)
        status = PASS if not self.failed else FAIL
        print(f"\n{status} [{self.name}]")
        for m in self.passed:
            print(f"   + {m}")
        for m in self.failed:
            print(f"   - {m}")
        for m in self.warnings:
            print(f"   ! {m}")
        rate = (len(self.passed) / total * 100) if total else 0
        print(f"   {len(self.passed)}/{total} ({rate:.0f}%)")
        return not self.failed


# ─────────────────────────────────────────────────────────────────────────────
# 1. _find_columns_by_headers: алиасы deal_id
# ─────────────────────────────────────────────────────────────────────────────

def test_find_columns_deal_id_aliases():
    """_find_columns_by_headers распознаёт все алиасы deal_id."""
    r = TestResult("_find_columns_by_headers: deal_id aliases")
    try:
        from sheets import SheetsManager
        fn = SheetsManager._find_columns_by_headers

        cases = {
            'id сделки':     ['ID сделки'],
            'deal_id':        ['deal_id'],
            'id транзакции':  ['ID транзакции'],
            'transaction_id': ['transaction_id'],
            'txid':           ['txid'],
        }
        for alias_name, headers in cases.items():
            result = fn(headers)
            if result.get('deal_id') == 0:
                r.ok(f"Алиас '{alias_name}' → deal_id=0")
            else:
                r.fail(f"Алиас '{alias_name}' не распознан как deal_id (got {result})")

        # Смешанный заголовок — убеждаемся, что нужная колонка находится в правильной позиции
        mixed_headers = ['ID заявки', 'Дата', 'Сумма', 'ID транзакции', 'Статус']
        m = fn(mixed_headers)
        if m.get('deal_id') == 3:
            r.ok("'ID транзакции' в смешанных заголовках → deal_id=3")
        else:
            r.fail(f"'ID транзакции' в смешанных заголовках: ожидался deal_id=3, got {m.get('deal_id')}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_find_columns_does_not_regress():
    """_find_columns_by_headers не сломала существующие маппинги."""
    r = TestResult("_find_columns_by_headers: обратная совместимость")
    try:
        from sheets import SheetsManager
        fn = SheetsManager._find_columns_by_headers

        # Стандартный набор заголовков основного листа
        headers = [
            'ID заявки', 'Дата', 'Сумма', 'Валюта',
            'Получатель', 'Номер карты/телефона', 'Банк', 'Реквизиты',
            'Назначение', 'Категория', 'Статус', 'ID сделки',
            'Название аккаунта', 'Сумма USDT', 'Курс',
            'Исполнитель', 'Telegram ID инициатора', 'Username', 'Полное имя', 'Чек'
        ]
        m = fn(headers)

        checks = [
            ('request_id', 0),
            ('status', 10),
            ('deal_id', 11),
            ('account_name', 12),
            ('amount_usdt', 13),
            ('executor', 15),
            ('receipt_url', 19),
        ]
        for field, expected_idx in checks:
            got = m.get(field)
            if got == expected_idx:
                r.ok(f"'{field}' → колонка {expected_idx}")
            else:
                r.fail(f"'{field}': ожидался {expected_idx}, got {got}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_find_columns_usdt_sheet_headers():
    """_find_columns_by_headers корректно маппит заголовки USDT листа."""
    r = TestResult("_find_columns_by_headers: USDT лист")
    try:
        from sheets import SheetsManager
        fn = SheetsManager._find_columns_by_headers

        # Реальные заголовки USDT листа согласно create_request
        usdt_headers = [
            'ID заявки',          # A:0  → request_id
            'Дата',               # B:1  → date
            'Сумма',              # C:2  → amount
            'Адрес кошелька',     # D:3  → card_or_phone
            'Назначение',         # E:4  → purpose
            'Категория',          # F:5  → category
            'Статус',             # G:6  → status
            'ID транзакции',      # H:7  → deal_id  ← КЛЮЧЕВОЙ FIX
            'Название аккаунта',  # I:8  → account_name
            'Исполнитель',        # J:9  → executor
            'Telegram ID инициатора',  # K:10 → author_id
            'Username инициатора',     # L:11 → author_username
            'Полное имя инициатора',   # M:12 → author_fullname
            'Чек',                # N:13 → receipt_url
        ]
        m = fn(usdt_headers)

        if m.get('deal_id') == 7:
            r.ok("'ID транзакции' (col H, index 7) → deal_id=7")
        else:
            r.fail(f"deal_id: ожидался 7, got {m.get('deal_id')} — fix не работает!")

        if m.get('receipt_url') == 13:
            r.ok("'Чек' (col N, index 13) → receipt_url=13")
        else:
            r.fail(f"receipt_url: ожидался 13, got {m.get('receipt_url')}")

        if m.get('status') == 6:
            r.ok("'Статус' (col G, index 6) → status=6")
        else:
            r.fail(f"status: ожидался 6, got {m.get('status')}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 2. enter_account: пропуск USDT-вопроса
# ─────────────────────────────────────────────────────────────────────────────

def test_enter_account_usdt_branch_in_source():
    """enter_account содержит ветку для USDT: пропуск вопроса про USDT."""
    r = TestResult("enter_account: USDT branch (source check)")
    try:
        from handlers import payment
        src = inspect.getsource(payment.enter_account)

        if 'CURRENCY_USDT' in src:
            r.ok("Ветка CURRENCY_USDT присутствует в enter_account")
        else:
            r.fail("В enter_account нет проверки CURRENCY_USDT")

        if 'show_payment_confirmation_message' in src:
            r.ok("При USDT вызывается show_payment_confirmation_message напрямую")
        else:
            r.fail("Не найден вызов show_payment_confirmation_message в USDT-ветке")

        if "payment_amount" in src and "amount_usdt" in src:
            r.ok("amount_usdt устанавливается из payment_amount в USDT-ветке")
        else:
            r.fail("Не найдено присвоение amount_usdt = payment_amount")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_enter_account_usdt_skips_question():
    """enter_account для USDT не задаёт вопрос 'Была ли оплата в USDT?'."""
    r = TestResult("enter_account: USDT не спрашивает про USDT-оплату")

    async def _run():
        from handlers import payment
        from src import config

        update = MagicMock()
        update.message = AsyncMock()
        update.message.text = "Business Account"
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.user_data = {
            'payment_currency': config.CURRENCY_USDT,
            'payment_amount': 500.0,
            'payment_request': {},
            'deal_id': 'abc123',
        }

        result_state = await payment.enter_account(update, context)

        # Не должен был спрашивать "Была ли оплата в USDT?"
        for call in update.message.reply_text.call_args_list:
            text_arg = call.args[0] if call.args else ''
            if 'USDT' in text_arg and 'была' in text_arg.lower():
                r.fail(f"Был отправлен вопрос 'Была ли оплата в USDT?': {text_arg!r}")
                return

        # amount_usdt должен быть установлен
        if context.user_data.get('amount_usdt') == 500.0:
            r.ok("amount_usdt установлен в 500.0 (= payment_amount)")
        else:
            r.fail(f"amount_usdt не установлен корректно: {context.user_data.get('amount_usdt')}")

        # Должен НЕ вернуть ENTER_USDT
        if result_state == payment.ENTER_USDT:
            r.fail("enter_account вернул ENTER_USDT для USDT-заявки — вопрос НЕ пропущен")
        else:
            r.ok(f"enter_account вернул {result_state} (не ENTER_USDT) — вопрос пропущен")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_enter_account_non_usdt_asks_question():
    """enter_account для RUB по-прежнему задаёт вопрос про USDT."""
    r = TestResult("enter_account: RUB задаёт вопрос про USDT-оплату")

    async def _run():
        from handlers import payment
        from src import config

        update = MagicMock()
        update.message = AsyncMock()
        update.message.text = "Savings Account"
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.user_data = {
            'payment_currency': config.CURRENCY_RUB,
            'payment_amount': 10000.0,
            'payment_request': {},
            'deal_id': '',
        }

        result_state = await payment.enter_account(update, context)

        if result_state == payment.ENTER_USDT:
            r.ok("enter_account вернул ENTER_USDT для RUB-заявки")
        else:
            r.fail(f"enter_account вернул {result_state}, ожидался ENTER_USDT для RUB")

        # Должен был отправить сообщение с кнопками
        if update.message.reply_text.called:
            r.ok("reply_text был вызван (вопрос задан)")
        else:
            r.fail("reply_text не был вызван для RUB-заявки")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 3. handle_receipt_upload: TronScan URL
# ─────────────────────────────────────────────────────────────────────────────

def test_receipt_upload_url_in_source():
    """handle_receipt_upload содержит обработку текстовых URL."""
    r = TestResult("handle_receipt_upload: URL branch (source check)")
    try:
        from handlers import payment
        src = inspect.getsource(payment.handle_receipt_upload)

        if 'update.message.text' in src:
            r.ok("Проверка update.message.text присутствует")
        else:
            r.fail("Нет обработки update.message.text в handle_receipt_upload")

        if "startswith('http')" in src:
            r.ok("Валидация https:// присутствует")
        else:
            r.fail("Нет проверки startswith('http') для URL")

        if 'update_receipt_url' in src:
            r.ok("update_receipt_url вызывается для URL")
        else:
            r.fail("update_receipt_url не вызывается в URL-ветке")

        if 'ConversationHandler.END' in src:
            r.ok("При успешном URL возвращается END")
        else:
            r.fail("Не найден возврат END после сохранения URL")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_receipt_upload_valid_url():
    """handle_receipt_upload сохраняет валидный TronScan URL и завершает разговор."""
    r = TestResult("handle_receipt_upload: валидный TronScan URL")

    async def _run():
        from handlers import payment
        from telegram.ext import ConversationHandler

        url = "https://tronscan.org/#/transaction/d70f3e4fe5c7efa3"

        update = MagicMock()
        update.message = AsyncMock()
        update.message.text = url
        update.message.photo = None
        update.message.document = None
        update.message.reply_text = AsyncMock()

        mock_sheets = MagicMock()
        mock_sheets.update_receipt_url = MagicMock(return_value=True)

        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets, 'drive_manager': MagicMock()}
        context.user_data = {
            'payment_date': '17.02.2026',
            'payment_amount': 1233.0,
            'payment_currency': 'USDT',
            'payment_request_id': 'REQ-20260217-162447-8F6260CC',
            'payment_request': {'author_id': '123456', 'purpose': 'Test'},
            'executor_name': 'Dave',
        }
        context.bot = AsyncMock()

        state = await payment.handle_receipt_upload(update, context)

        # update_receipt_url должен быть вызван с правильным URL
        if mock_sheets.update_receipt_url.called:
            call_kwargs = mock_sheets.update_receipt_url.call_args
            # Проверяем, что URL передан
            args = call_kwargs.args if call_kwargs.args else []
            kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
            all_args = list(args) + list(kwargs.values())
            if url in all_args:
                r.ok(f"update_receipt_url вызван с правильным URL")
            else:
                r.fail(f"update_receipt_url вызван с неверными аргументами: {call_kwargs}")
        else:
            r.fail("update_receipt_url не был вызван")

        if state == ConversationHandler.END:
            r.ok("handle_receipt_upload вернул END для валидного URL")
        else:
            r.fail(f"handle_receipt_upload вернул {state}, ожидался END")

        # reply_text должен был сообщить об успехе
        if update.message.reply_text.called:
            reply_text = update.message.reply_text.call_args.args[0]
            if url in reply_text:
                r.ok("Ответ пользователю содержит URL чека")
            else:
                r.warn(f"Ответ не содержит URL: {reply_text!r}")
        else:
            r.fail("reply_text не вызван после сохранения URL")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_receipt_upload_invalid_url():
    """handle_receipt_upload отклоняет текст без https:// и возвращает UPLOAD_RECEIPT."""
    r = TestResult("handle_receipt_upload: невалидный URL отклоняется")

    async def _run():
        from handlers import payment

        update = MagicMock()
        update.message = AsyncMock()
        update.message.text = "это не ссылка"
        update.message.photo = None
        update.message.document = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {'sheets': MagicMock(), 'drive_manager': MagicMock()}
        context.user_data = {
            'payment_date': '17.02.2026',
            'payment_amount': 500.0,
            'payment_currency': 'USDT',
            'payment_request_id': 'REQ-123',
            'payment_request': {},
        }

        state = await payment.handle_receipt_upload(update, context)

        if state == payment.UPLOAD_RECEIPT:
            r.ok("Невалидный URL → остаёмся в UPLOAD_RECEIPT")
        else:
            r.fail(f"Невалидный URL → state={state}, ожидался UPLOAD_RECEIPT")

        if update.message.reply_text.called:
            reply_text = update.message.reply_text.call_args.args[0]
            if 'https' in reply_text.lower() or 'ссылка' in reply_text.lower():
                r.ok("Пользователю сообщено про требование https://")
            else:
                r.warn(f"Сообщение об ошибке не информативно: {reply_text!r}")
        else:
            r.fail("reply_text не вызван после невалидного URL")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_receipt_upload_url_no_drive_needed():
    """handle_receipt_upload с URL работает даже без drive_manager."""
    r = TestResult("handle_receipt_upload: URL не требует DriveManager")

    async def _run():
        from handlers import payment
        from telegram.ext import ConversationHandler

        url = "https://tronscan.org/#/transaction/abc123"

        update = MagicMock()
        update.message = AsyncMock()
        update.message.text = url
        update.message.photo = None
        update.message.document = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        # drive_manager ОТСУТСТВУЕТ
        context.bot_data = {'sheets': MagicMock(), 'drive_manager': None}
        context.user_data = {
            'payment_date': '19.02.2026',
            'payment_amount': 100.0,
            'payment_currency': 'USDT',
            'payment_request_id': 'REQ-999',
            'payment_request': {'author_id': ''},
        }
        context.bot = AsyncMock()

        state = await payment.handle_receipt_upload(update, context)

        if state == ConversationHandler.END:
            r.ok("URL-чек сохранён без drive_manager → END")
        else:
            r.fail(f"URL-чек без drive_manager → state={state}, ожидался END")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 4. ConversationHandler: TEXT handler в UPLOAD_RECEIPT
# ─────────────────────────────────────────────────────────────────────────────

def test_upload_receipt_state_has_text_handler():
    """UPLOAD_RECEIPT state содержит MessageHandler с filters.TEXT."""
    r = TestResult("ConversationHandler: TEXT handler в UPLOAD_RECEIPT")
    try:
        from handlers.payment import get_payment_conversation_handler
        from telegram.ext import ConversationHandler, MessageHandler, filters

        handler = get_payment_conversation_handler()
        upload_state = handler.states.get(4)  # UPLOAD_RECEIPT = 5-й state (index 5), значение 5

        # Найдём UPLOAD_RECEIPT по значению константы
        from handlers.payment import UPLOAD_RECEIPT
        upload_handlers = handler.states.get(UPLOAD_RECEIPT, [])

        if not upload_handlers:
            r.fail(f"UPLOAD_RECEIPT state (={UPLOAD_RECEIPT}) не найден в states")
            return r

        has_text = any(
            isinstance(h, MessageHandler) and
            hasattr(h, 'filters') and
            'TEXT' in str(type(h.filters))
            for h in upload_handlers
        )

        # Также проверяем по source
        from handlers import payment as pay_mod
        src = inspect.getsource(pay_mod.get_payment_conversation_handler)
        if 'filters.TEXT' in src and 'handle_receipt_upload' in src:
            r.ok("filters.TEXT + handle_receipt_upload найдены в определении ConversationHandler")
        else:
            r.fail("filters.TEXT & handle_receipt_upload не найдены в get_payment_conversation_handler")

        photo_count = sum(
            1 for h in upload_handlers
            if isinstance(h, MessageHandler) and 'PHOTO' in str(type(h.filters))
        )
        r.ok(f"UPLOAD_RECEIPT state содержит {len(upload_handlers)} handlers")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 5. mark_paid_callback: USDT-специфичный промпт
# ─────────────────────────────────────────────────────────────────────────────

def test_mark_paid_callback_usdt_prompt():
    """mark_paid_callback показывает 'ID транзакции TronScan' для USDT."""
    r = TestResult("mark_paid_callback: USDT prompt")

    async def _run():
        from handlers import payment

        query = AsyncMock()
        query.data = "mark_paid"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        context = MagicMock()
        context.user_data = {'payment_currency': 'USDT'}

        await payment.mark_paid_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if 'TronScan' in text or 'транзакци' in text.lower():
                r.ok(f"USDT prompt содержит 'TronScan'/'транзакции': {text!r}")
            else:
                r.fail(f"USDT prompt не содержит 'TronScan': {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_mark_paid_callback_rub_prompt():
    """mark_paid_callback показывает 'ID сделки' для RUB."""
    r = TestResult("mark_paid_callback: RUB prompt")

    async def _run():
        from handlers import payment

        query = AsyncMock()
        query.data = "mark_paid"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        context = MagicMock()
        context.user_data = {'payment_currency': 'RUB'}

        await payment.mark_paid_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if 'сделки' in text.lower():
                r.ok(f"RUB prompt содержит 'ID сделки': {text!r}")
            else:
                r.fail(f"RUB prompt не содержит 'ID сделки': {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 6. receipt_choice_callback: USDT-специфичный промпт
# ─────────────────────────────────────────────────────────────────────────────

def test_receipt_choice_usdt_prompt():
    """receipt_choice_callback для USDT упоминает TronScan."""
    r = TestResult("receipt_choice_callback: USDT TronScan prompt")

    async def _run():
        from handlers import payment

        query = AsyncMock()
        query.data = "receipt_yes"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        context = MagicMock()
        context.user_data = {'payment_currency': 'USDT'}

        await payment.receipt_choice_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if 'TronScan' in text or 'ссылка' in text.lower():
                r.ok(f"USDT receipt prompt упоминает TronScan/ссылку: {text!r}")
            else:
                r.fail(f"USDT receipt prompt не упоминает TronScan: {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    # sheets
    test_find_columns_deal_id_aliases,
    test_find_columns_does_not_regress,
    test_find_columns_usdt_sheet_headers,
    # enter_account
    test_enter_account_usdt_branch_in_source,
    test_enter_account_usdt_skips_question,
    test_enter_account_non_usdt_asks_question,
    # handle_receipt_upload
    test_receipt_upload_url_in_source,
    test_receipt_upload_valid_url,
    test_receipt_upload_invalid_url,
    test_receipt_upload_url_no_drive_needed,
    # ConversationHandler
    test_upload_receipt_state_has_text_handler,
    # mark_paid_callback
    test_mark_paid_callback_usdt_prompt,
    test_mark_paid_callback_rub_prompt,
    # receipt_choice_callback
    test_receipt_choice_usdt_prompt,
]


def run_all() -> bool:
    print("=" * 70)
    print("USDT Payment Fixes — Test Suite")
    print("=" * 70)
    results = []
    for fn in ALL_TESTS:
        try:
            r = fn()
            results.append(r)
            r.print_summary()
        except Exception as e:
            import traceback
            print(f"\n[CRITICAL] {fn.__name__}: {e}")
            traceback.print_exc()

    total_pass = sum(len(r.passed) for r in results)
    total_fail = sum(len(r.failed) for r in results)
    total_warn = sum(len(r.warnings) for r in results)

    print("\n" + "=" * 70)
    print("ИТОГО")
    print("=" * 70)
    print(f"  Тестов: {len(results)}")
    print(f"  Checks: {PASS} {total_pass}  {FAIL} {total_fail}  {WARN} {total_warn}")
    ok = total_fail == 0
    print(f"  Результат: {'ВСЕ ПРОШЛИ' if ok else 'ЕСТЬ ОШИБКИ'}")
    return ok


if __name__ == '__main__':
    success = run_all()
    sys.exit(0 if success else 1)
