"""
Тесты редактирования типа USDT-перевода
========================================
Покрывает фичу из коммита a367c0e:
- Выбор типа при создании заявки ("Конечный получатель" / "Пополнение площадки")
- sheets.update_request_fields: новый параметр category для USDT (col F)
- edit_usdt_type_menu: кнопки выбора типа
- set_usdt_type_callback: сохранение категории + авто-определение при возврате к expense

Запуск: .venv/Scripts/python -m pytest tests/test_usdt_type_editing.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call

from src import config
from src.sheets import SheetsManager
from src.utils.categories import determine_category


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_usdt_sheets(date: str, amount: float) -> tuple:
    """
    Создать SheetsManager с замоканным USDT-листом содержащим одну заявку.

    Returns:
        (sheets, usdt_ws) — SheetsManager и мок листа USDT.

    Side effects:
        - get_worksheet(SHEET_USDT) → usdt_ws с данными.
        - get_worksheet(<другой лист>) → пустой ws (только заголовок).
        - НЕ подключается к Google Sheets.
    """
    sheets = SheetsManager.__new__(SheetsManager)

    usdt_ws = MagicMock()
    usdt_ws.get_all_values.return_value = [
        ["ID", "Дата", "Сумма", "Кошелёк", "Назначение", "Категория", "Статус"],
        ["REQ-001", date, str(amount), "TRX_wallet123", "зарплата", "Зарплата", "Создана"],
    ]

    empty_ws = MagicMock()
    empty_ws.get_all_values.return_value = [["ID", "Дата", "Сумма"]]

    def _get_ws(name):
        if name == config.SHEET_USDT:
            return usdt_ws
        return empty_ws

    sheets.get_worksheet = MagicMock(side_effect=_get_ws)
    return sheets, usdt_ws


def make_callback_update_mock(data: str, user_data: dict, bot_data: dict):
    """
    Создать (update, context) моки для тестирования CallbackQueryHandler.

    Side effects:
        - update.callback_query.answer — AsyncMock (не делает реального вызова).
        - update.callback_query.edit_message_text — AsyncMock.
    """
    query = AsyncMock()
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock()
    update.callback_query = query

    context = MagicMock()
    context.user_data = user_data
    context.bot_data = bot_data

    return update, context


# ── sheets.update_request_fields — category param ─────────────────────────────

class TestUpdateRequestFieldsCategory:
    """
    Контракт: category=<str> для USDT обновляет col 6 (F: Категория).

    Invariants:
        - Другие колонки при обновлении только category НЕ трогаются.
        - Для RUB category игнорируется (update_cell(6) не вызывается).
    """

    def test_usdt_category_updates_col_6(self):
        """category='Пополнение площадки' → update_cell(row, 6, ...)."""
        sheets, usdt_ws = make_usdt_sheets("15.01.2026", 500.0)

        result = sheets.update_request_fields(
            date="15.01.2026",
            amount=500.0,
            currency=config.CURRENCY_USDT,
            category=config.CATEGORY_INTERNAL_TRANSFER,
        )

        assert result is True
        usdt_ws.update_cell.assert_called_once_with(2, 6, config.CATEGORY_INTERNAL_TRANSFER)

    def test_usdt_none_category_does_not_update_col_6(self):
        """category=None (не передан) → update_cell НЕ вызывается."""
        sheets, usdt_ws = make_usdt_sheets("16.01.2026", 200.0)

        result = sheets.update_request_fields(
            date="16.01.2026",
            amount=200.0,
            currency=config.CURRENCY_USDT,
        )

        assert result is True
        usdt_ws.update_cell.assert_not_called()

    def test_usdt_category_only_updates_col_6_not_others(self):
        """Только col 6 меняется — col 3, 4, 5 не трогаются."""
        sheets, usdt_ws = make_usdt_sheets("17.01.2026", 750.0)

        sheets.update_request_fields(
            date="17.01.2026",
            amount=750.0,
            currency=config.CURRENCY_USDT,
            category="Зарплата",
        )

        calls = usdt_ws.update_cell.call_args_list
        assert len(calls) == 1
        col_updated = calls[0].args[1]
        assert col_updated == 6, f"Ожидался col 6, обновлён col {col_updated}"

    def test_usdt_category_and_purpose_update_both_cols(self):
        """category + purpose → update_cell вызывается дважды (col 5 и col 6)."""
        sheets, usdt_ws = make_usdt_sheets("18.01.2026", 300.0)

        sheets.update_request_fields(
            date="18.01.2026",
            amount=300.0,
            currency=config.CURRENCY_USDT,
            purpose="новое назначение",
            category="Прочее",
        )

        cols_updated = {c.args[1] for c in usdt_ws.update_cell.call_args_list}
        assert 5 in cols_updated  # E: Назначение
        assert 6 in cols_updated  # F: Категория

    def test_row_not_found_returns_false(self):
        """Заявка с другой датой/суммой → False, update_cell не вызывается."""
        sheets, usdt_ws = make_usdt_sheets("19.01.2026", 100.0)

        result = sheets.update_request_fields(
            date="31.12.2025",  # другая дата
            amount=100.0,
            currency=config.CURRENCY_USDT,
            category="Прочее",
        )

        assert result is False
        usdt_ws.update_cell.assert_not_called()


# ── determine_category — Пополнение площадки ──────────────────────────────────

class TestDetermineCategory:
    """Авто-определение категории по ключевым словам в назначении."""

    @pytest.mark.parametrize("purpose,expected", [
        ("пополнение площадки bippapa", "Пополнение площадки"),
        ("транзит на кошелек", "Пополнение площадки"),
        ("P2P перевод на площадку", "Пополнение площадки"),
        ("bippapa transit", "Пополнение площадки"),
        ("зарплата за январь", "Зарплата"),
        ("реклама в интернете", "Маркетинг"),
        ("непонятное что-то", "Прочее"),
        ("", "Прочее"),
    ])
    def test_category_detection(self, purpose, expected):
        assert determine_category(purpose) == expected


# ── edit_usdt_type_menu ────────────────────────────────────────────────────────

class TestEditUsdtTypeMenu:
    """
    Контракт: edit_usdt_type_menu отображает 3 кнопки:
    - 💸 Конечный получатель (callback: set_usdt_type_expense)
    - 🔄 Пополнение площадки / Транзит (callback: set_usdt_type_internal)
    - « Назад (callback: edit_menu_<request_id>_<page>)
    """

    @pytest.mark.asyncio
    async def test_shows_two_type_buttons_and_back(self):
        """Меню содержит ровно 3 кнопки."""
        from src.handlers.edit_handlers import edit_usdt_type_menu

        update, context = make_callback_update_mock(
            data="edit_usdt_type",
            user_data={"edit_request_id": "REQ-TEST-001", "edit_page": 1},
            bot_data={},
        )

        await edit_usdt_type_menu(update, context)

        update.callback_query.edit_message_text.assert_called_once()
        kwargs = update.callback_query.edit_message_text.call_args.kwargs
        keyboard = kwargs["reply_markup"].inline_keyboard
        assert len(keyboard) == 3

    @pytest.mark.asyncio
    async def test_expense_button_callback_data(self):
        """Первая кнопка — callback_data='set_usdt_type_expense'."""
        from src.handlers.edit_handlers import edit_usdt_type_menu

        update, context = make_callback_update_mock(
            data="edit_usdt_type",
            user_data={"edit_request_id": "REQ-001", "edit_page": 1},
            bot_data={},
        )

        await edit_usdt_type_menu(update, context)

        keyboard = update.callback_query.edit_message_text.call_args.kwargs["reply_markup"].inline_keyboard
        assert keyboard[0][0].callback_data == "set_usdt_type_expense"

    @pytest.mark.asyncio
    async def test_internal_button_callback_data(self):
        """Вторая кнопка — callback_data='set_usdt_type_internal'."""
        from src.handlers.edit_handlers import edit_usdt_type_menu

        update, context = make_callback_update_mock(
            data="edit_usdt_type",
            user_data={"edit_request_id": "REQ-001", "edit_page": 1},
            bot_data={},
        )

        await edit_usdt_type_menu(update, context)

        keyboard = update.callback_query.edit_message_text.call_args.kwargs["reply_markup"].inline_keyboard
        assert keyboard[1][0].callback_data == "set_usdt_type_internal"

    @pytest.mark.asyncio
    async def test_back_button_includes_request_id_and_page(self):
        """Кнопка 'Назад' ведёт обратно в меню редактирования заявки."""
        from src.handlers.edit_handlers import edit_usdt_type_menu

        update, context = make_callback_update_mock(
            data="edit_usdt_type",
            user_data={"edit_request_id": "REQ-BACK-42", "edit_page": 3},
            bot_data={},
        )

        await edit_usdt_type_menu(update, context)

        keyboard = update.callback_query.edit_message_text.call_args.kwargs["reply_markup"].inline_keyboard
        back_callback = keyboard[2][0].callback_data
        assert "REQ-BACK-42" in back_callback
        assert "3" in back_callback


# ── set_usdt_type_callback ─────────────────────────────────────────────────────

class TestSetUsdtTypeCallback:
    """
    Контракт:
    - internal → category = CATEGORY_INTERNAL_TRANSFER
    - expense  → category = determine_category(edit_purpose)
    - При успехе: user_data.clear() вызывается
    - При ошибке sheets: user_data НЕ очищается
    """

    def _make_user_data(self, purpose: str = "транзит") -> dict:
        return {
            "edit_date": "20.01.2026",
            "edit_amount": 1000.0,
            "edit_request_id": "REQ-USDT-001",
            "edit_page": 1,
            "edit_purpose": purpose,
        }

    @pytest.mark.asyncio
    async def test_internal_saves_internal_transfer_category(self):
        """'set_usdt_type_internal' → sheets.update_request_fields(category=CATEGORY_INTERNAL_TRANSFER)."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        sheets.update_request_fields.return_value = True

        update, context = make_callback_update_mock(
            data="set_usdt_type_internal",
            user_data=self._make_user_data("транзит"),
            bot_data={"sheets": sheets},
        )

        await set_usdt_type_callback(update, context)

        sheets.update_request_fields.assert_called_once_with(
            date="20.01.2026",
            amount=1000.0,
            currency=config.CURRENCY_USDT,
            category=config.CATEGORY_INTERNAL_TRANSFER,
        )

    @pytest.mark.asyncio
    async def test_expense_auto_detects_category_from_purpose(self):
        """'set_usdt_type_expense' + purpose='зарплата' → category='Зарплата'."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        sheets.update_request_fields.return_value = True

        update, context = make_callback_update_mock(
            data="set_usdt_type_expense",
            user_data=self._make_user_data("зарплата за февраль"),
            bot_data={"sheets": sheets},
        )

        await set_usdt_type_callback(update, context)

        sheets.update_request_fields.assert_called_once_with(
            date="20.01.2026",
            amount=1000.0,
            currency=config.CURRENCY_USDT,
            category="Зарплата",
        )

    @pytest.mark.asyncio
    async def test_expense_unknown_purpose_defaults_to_prochee(self):
        """Неизвестное назначение → 'Прочее'."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        sheets.update_request_fields.return_value = True

        update, context = make_callback_update_mock(
            data="set_usdt_type_expense",
            user_data=self._make_user_data("непонятная строка xyz"),
            bot_data={"sheets": sheets},
        )

        await set_usdt_type_callback(update, context)

        sheets.update_request_fields.assert_called_once_with(
            date="20.01.2026",
            amount=1000.0,
            currency=config.CURRENCY_USDT,
            category="Прочее",
        )

    @pytest.mark.asyncio
    async def test_success_clears_user_data(self):
        """При успешном сохранении user_data очищается."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        sheets.update_request_fields.return_value = True

        user_data = self._make_user_data()
        update, context = make_callback_update_mock(
            data="set_usdt_type_internal",
            user_data=user_data,
            bot_data={"sheets": sheets},
        )
        # Используем реальный dict чтобы проверить clear()
        context.user_data = user_data

        await set_usdt_type_callback(update, context)

        # После успеха user_data должен быть пуст
        assert context.user_data == {}

    @pytest.mark.asyncio
    async def test_failure_preserves_user_data(self):
        """При ошибке sheets user_data НЕ очищается."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        sheets.update_request_fields.return_value = False

        user_data = self._make_user_data()
        update, context = make_callback_update_mock(
            data="set_usdt_type_internal",
            user_data=user_data,
            bot_data={"sheets": sheets},
        )
        context.user_data = user_data

        await set_usdt_type_callback(update, context)

        assert "edit_date" in context.user_data  # не очищен

    @pytest.mark.asyncio
    async def test_no_sheets_sends_error_message(self):
        """Нет sheets в bot_data → сообщение об ошибке, update_request_fields не вызывается."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        update, context = make_callback_update_mock(
            data="set_usdt_type_internal",
            user_data=self._make_user_data(),
            bot_data={},  # нет sheets
        )

        await set_usdt_type_callback(update, context)

        update.callback_query.edit_message_text.assert_called_once()
        text = update.callback_query.edit_message_text.call_args.args[0]
        assert "⚠️" in text or "Ошибка" in text

    @pytest.mark.asyncio
    async def test_missing_date_sends_error_message(self):
        """Нет edit_date в user_data → сообщение об ошибке."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        update, context = make_callback_update_mock(
            data="set_usdt_type_internal",
            user_data={"edit_amount": 500.0},  # нет edit_date
            bot_data={"sheets": sheets},
        )

        await set_usdt_type_callback(update, context)

        sheets.update_request_fields.assert_not_called()
        update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_message_shows_type_label(self):
        """Сообщение об успехе содержит читаемый тип операции."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        sheets.update_request_fields.return_value = True

        update, context = make_callback_update_mock(
            data="set_usdt_type_internal",
            user_data=self._make_user_data(),
            bot_data={"sheets": sheets},
        )

        await set_usdt_type_callback(update, context)

        text = update.callback_query.edit_message_text.call_args.args[0]
        assert "Пополнение" in text or "Транзит" in text

    @pytest.mark.asyncio
    async def test_success_message_has_back_to_request_button(self):
        """После успеха кнопка 'Вернуться к заявке' с правильным request_id."""
        from src.handlers.edit_handlers import set_usdt_type_callback

        sheets = MagicMock()
        sheets.update_request_fields.return_value = True

        update, context = make_callback_update_mock(
            data="set_usdt_type_internal",
            user_data=self._make_user_data(),
            bot_data={"sheets": sheets},
        )

        await set_usdt_type_callback(update, context)

        kwargs = update.callback_query.edit_message_text.call_args.kwargs
        keyboard = kwargs["reply_markup"].inline_keyboard
        back_data = keyboard[0][0].callback_data
        assert "REQ-USDT-001" in back_data
