"""
Тесты flow оплаты USDT через Tronscan — payment.py
====================================================
Покрываем enter_deal_id и usdt_enter_manual_callback:

Кейсы:
  A. Tronscan URL / хеш — автоматический режим
     A1. OK: кошелёк и сумма совпадают → подтверждение
     A2. Кошелёк не совпадает → ошибка + кнопка "Ввести вручную"
     A3. Сумма не совпадает → ошибка + кнопка
     A4. Кошелёк И сумма не совпадают → обе ошибки + кнопка
     A5. API вернул None (timeout/ошибка) → ошибка + кнопка
  B. Обычный текст — ручной режим
     B1. Произвольный текст (deal ID) → спрашивает аккаунт
     B2. Дефис "-" → deal_id="" → спрашивает аккаунт
  C. Флаг usdt_manual установлен (после кнопки "Ввести вручную")
     C1. Любой текст, даже хеш → сохраняется как deal_id, не лезет в API
     C2. Флаг сбрасывается после использования
  D. usdt_enter_manual_callback — нажата кнопка "Ввести вручную"
     D1. Устанавливает флаг, возвращает ENTER_DEAL_ID

Запуск: inv test  или  .venv/Scripts/python -m pytest tests/test_tronscan_payment_flow.py -v
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src import config
from src.handlers.payment import (
    ENTER_ACCOUNT,
    ENTER_DEAL_ID,
    CONFIRM_PAYMENT,
    enter_deal_id,
    usdt_enter_manual_callback,
)

VALID_HASH = "a9b8acbda7a0631baf1950f5d8008cb8327f795cc56b32b51aa9d9cd4541594e"
TRONSCAN_URL = f"https://tronscan.org/#/transaction/{VALID_HASH}"

WALLET_OK = "THG8FA1XJy8kRMtFny7yvr1L73j1tjQf54"
WALLET_WRONG = "TWRONG1111111111111111111111111111"
SENDER = "THZD5HGDdVig5zf4hqtu3LrPMRV7Fd8ts4"
AMOUNT_OK = 1500.0
AMOUNT_WRONG = 999.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_update(text: str) -> MagicMock:
    """Фейковый Update с текстовым сообщением."""
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def make_context(
    currency: str = config.CURRENCY_USDT,
    wallet: str = WALLET_OK,
    amount: float = AMOUNT_OK,
    usdt_manual: bool = False,
) -> MagicMock:
    """Фейковый context с user_data заявки."""
    ctx = MagicMock()
    ctx.user_data = {
        "payment_currency": currency,
        "payment_request": {
            "card_or_phone": wallet,
            "amount": amount,
            "date": "20.02.2026",
        },
        "payment_amount": amount,
    }
    if usdt_manual:
        ctx.user_data["usdt_manual"] = True
    return ctx


def make_tx(
    recipient: str = WALLET_OK,
    amount: float = AMOUNT_OK,
    tx_hash: str = VALID_HASH,
    sender: str = SENDER,
):
    """Фейковая TronTransaction."""
    from src.utils.tronscan import TronTransaction
    return TronTransaction(
        tx_hash=tx_hash,
        sender=sender,
        recipient=recipient,
        amount=amount,
        token="USDT",
    )


# ── A. Tronscan URL — автоматический режим ────────────────────────────────────

class TestTronscanAutoMode:

    @pytest.mark.asyncio
    async def test_a1_valid_tx_goes_to_confirmation(self):
        """A1: кошелёк и сумма совпадают → auto-fill → CONFIRM_PAYMENT."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context()

        with patch("src.handlers.payment.parse_tronscan_url", return_value=make_tx()), \
             patch("src.handlers.payment.show_payment_confirmation_message",
                   new=AsyncMock(return_value=CONFIRM_PAYMENT)) as mock_confirm:
            result = await enter_deal_id(update, ctx)

        assert result == CONFIRM_PAYMENT
        mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_a1_deal_id_set_to_tx_hash(self):
        """A1: deal_id сохраняется как полный tx_hash."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context()

        with patch("src.handlers.payment.parse_tronscan_url", return_value=make_tx()), \
             patch("src.handlers.payment.show_payment_confirmation_message",
                   new=AsyncMock(return_value=CONFIRM_PAYMENT)):
            await enter_deal_id(update, ctx)

        assert ctx.user_data["deal_id"] == VALID_HASH

    @pytest.mark.asyncio
    async def test_a1_account_name_set_to_sender(self):
        """A1: account_name = sender-кошелёк из транзакции."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context()

        with patch("src.handlers.payment.parse_tronscan_url", return_value=make_tx()), \
             patch("src.handlers.payment.show_payment_confirmation_message",
                   new=AsyncMock(return_value=CONFIRM_PAYMENT)):
            await enter_deal_id(update, ctx)

        assert ctx.user_data["account_name"] == SENDER

    @pytest.mark.asyncio
    async def test_a1_amount_usdt_set(self):
        """A1: amount_usdt = tx.amount."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context()

        with patch("src.handlers.payment.parse_tronscan_url", return_value=make_tx()), \
             patch("src.handlers.payment.show_payment_confirmation_message",
                   new=AsyncMock(return_value=CONFIRM_PAYMENT)):
            await enter_deal_id(update, ctx)

        assert ctx.user_data["amount_usdt"] == pytest.approx(AMOUNT_OK)

    @pytest.mark.asyncio
    async def test_a2_wrong_wallet_returns_enter_deal_id(self):
        """A2: неверный кошелёк → ошибка → остаёмся в ENTER_DEAL_ID."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(wallet=WALLET_OK)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(recipient=WALLET_WRONG)):
            result = await enter_deal_id(update, ctx)

        assert result == ENTER_DEAL_ID

    @pytest.mark.asyncio
    async def test_a2_wrong_wallet_message_contains_both_wallets(self):
        """A2: сообщение об ошибке показывает оба кошелька."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(wallet=WALLET_OK)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(recipient=WALLET_WRONG)):
            await enter_deal_id(update, ctx)

        call_text = update.message.reply_text.call_args_list[-1][0][0]
        assert WALLET_OK in call_text
        assert WALLET_WRONG in call_text

    @pytest.mark.asyncio
    async def test_a2_wrong_wallet_reply_has_manual_button(self):
        """A2: в ответе есть кнопка 'Ввести вручную'."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(wallet=WALLET_OK)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(recipient=WALLET_WRONG)):
            await enter_deal_id(update, ctx)

        call_kwargs = update.message.reply_text.call_args_list[-1][1]
        markup = call_kwargs.get("reply_markup")
        assert markup is not None
        buttons_flat = [b.callback_data for row in markup.inline_keyboard for b in row]
        assert "usdt_enter_manual" in buttons_flat

    @pytest.mark.asyncio
    async def test_a3_wrong_amount_returns_enter_deal_id(self):
        """A3: неверная сумма → ошибка → ENTER_DEAL_ID."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(amount=AMOUNT_OK)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(amount=AMOUNT_WRONG)):
            result = await enter_deal_id(update, ctx)

        assert result == ENTER_DEAL_ID

    @pytest.mark.asyncio
    async def test_a3_wrong_amount_message_contains_both_amounts(self):
        """A3: сообщение показывает сумму из заявки и из транзакции."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(amount=AMOUNT_OK)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(amount=AMOUNT_WRONG)):
            await enter_deal_id(update, ctx)

        call_text = update.message.reply_text.call_args_list[-1][0][0]
        assert str(AMOUNT_OK) in call_text or "1500" in call_text
        assert str(AMOUNT_WRONG) in call_text or "999" in call_text

    @pytest.mark.asyncio
    async def test_a4_both_wrong_shows_two_errors(self):
        """A4: и кошелёк, и сумма неверны → обе ошибки в одном сообщении."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(wallet=WALLET_OK, amount=AMOUNT_OK)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(recipient=WALLET_WRONG, amount=AMOUNT_WRONG)):
            result = await enter_deal_id(update, ctx)

        assert result == ENTER_DEAL_ID
        call_text = update.message.reply_text.call_args_list[-1][0][0]
        assert WALLET_WRONG in call_text
        assert str(AMOUNT_WRONG) in call_text or "999" in call_text

    @pytest.mark.asyncio
    async def test_a5_api_failure_returns_enter_deal_id(self):
        """A5: API вернул None → ошибка → ENTER_DEAL_ID."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context()

        with patch("src.handlers.payment.parse_tronscan_url", return_value=None):
            result = await enter_deal_id(update, ctx)

        assert result == ENTER_DEAL_ID

    @pytest.mark.asyncio
    async def test_a5_api_failure_reply_has_manual_button(self):
        """A5: после ошибки API — кнопка 'Ввести вручную'."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context()

        with patch("src.handlers.payment.parse_tronscan_url", return_value=None):
            await enter_deal_id(update, ctx)

        call_kwargs = update.message.reply_text.call_args_list[-1][1]
        markup = call_kwargs.get("reply_markup")
        assert markup is not None
        buttons_flat = [b.callback_data for row in markup.inline_keyboard for b in row]
        assert "usdt_enter_manual" in buttons_flat

    @pytest.mark.asyncio
    async def test_amount_tolerance_001_usdt_is_ok(self):
        """Разница 0.005 USDT (меньше допуска 0.01) должна считаться совпадением."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(amount=1500.0)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(amount=1500.005)), \
             patch("src.handlers.payment.show_payment_confirmation_message",
                   new=AsyncMock(return_value=CONFIRM_PAYMENT)):
            result = await enter_deal_id(update, ctx)

        assert result == CONFIRM_PAYMENT

    @pytest.mark.asyncio
    async def test_amount_tolerance_exceeded_is_error(self):
        """Разница 0.02 USDT (больше допуска) → ошибка."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(amount=1500.0)

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(amount=1500.02)):
            result = await enter_deal_id(update, ctx)

        assert result == ENTER_DEAL_ID

    @pytest.mark.asyncio
    async def test_wallet_comparison_case_insensitive(self):
        """Сравнение кошельков без учёта регистра."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(wallet=WALLET_OK.upper())

        with patch("src.handlers.payment.parse_tronscan_url",
                   return_value=make_tx(recipient=WALLET_OK.lower())), \
             patch("src.handlers.payment.show_payment_confirmation_message",
                   new=AsyncMock(return_value=CONFIRM_PAYMENT)):
            result = await enter_deal_id(update, ctx)

        assert result == CONFIRM_PAYMENT


# ── B. Ручной режим (не Tronscan) ────────────────────────────────────────────

class TestManualMode:

    @pytest.mark.asyncio
    async def test_b1_arbitrary_text_goes_to_enter_account(self):
        """B1: обычный текст → сохраняется deal_id → ENTER_ACCOUNT."""
        update = make_update("#UD823470")
        ctx = make_context()

        result = await enter_deal_id(update, ctx)

        assert result == ENTER_ACCOUNT
        assert ctx.user_data["deal_id"] == "#UD823470"

    @pytest.mark.asyncio
    async def test_b2_dash_saves_empty_deal_id(self):
        """B2: "-" → deal_id="" → ENTER_ACCOUNT."""
        update = make_update("-")
        ctx = make_context()

        result = await enter_deal_id(update, ctx)

        assert result == ENTER_ACCOUNT
        assert ctx.user_data["deal_id"] == ""

    @pytest.mark.asyncio
    async def test_b1_asks_for_account_name(self):
        """B1: бот просит ввести название аккаунта."""
        update = make_update("wire transfer")
        ctx = make_context()

        await enter_deal_id(update, ctx)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0].lower()
        assert "аккаунт" in call_text

    @pytest.mark.asyncio
    async def test_non_usdt_currency_uses_manual_flow(self):
        """Не-USDT валюта всегда идёт в ручной режим, Tronscan не вызывается."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(currency=config.CURRENCY_RUB)

        with patch("src.handlers.payment.parse_tronscan_url") as mock_parse:
            result = await enter_deal_id(update, ctx)

        mock_parse.assert_not_called()
        assert result == ENTER_ACCOUNT


# ── C. Флаг usdt_manual ────────────────────────────────────────────────────────

class TestUsdtManualFlag:

    @pytest.mark.asyncio
    async def test_c1_hash_with_flag_skips_api(self):
        """C1: хеш + флаг usdt_manual → API не вызывается → ENTER_ACCOUNT."""
        update = make_update(VALID_HASH)
        ctx = make_context(usdt_manual=True)

        with patch("src.handlers.payment.parse_tronscan_url") as mock_parse:
            result = await enter_deal_id(update, ctx)

        mock_parse.assert_not_called()
        assert result == ENTER_ACCOUNT

    @pytest.mark.asyncio
    async def test_c1_hash_with_flag_saved_as_deal_id(self):
        """C1: хеш сохраняется как deal_id без верификации."""
        update = make_update(VALID_HASH)
        ctx = make_context(usdt_manual=True)

        with patch("src.handlers.payment.parse_tronscan_url"):
            await enter_deal_id(update, ctx)

        assert ctx.user_data["deal_id"] == VALID_HASH

    @pytest.mark.asyncio
    async def test_c2_flag_is_cleared_after_use(self):
        """C2: флаг usdt_manual сбрасывается после первого использования."""
        update = make_update("some deal id")
        ctx = make_context(usdt_manual=True)

        with patch("src.handlers.payment.parse_tronscan_url"):
            await enter_deal_id(update, ctx)

        assert "usdt_manual" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_c1_url_with_flag_skips_api(self):
        """C1: даже полная Tronscan URL + флаг → не идём в API."""
        update = make_update(TRONSCAN_URL)
        ctx = make_context(usdt_manual=True)

        with patch("src.handlers.payment.parse_tronscan_url") as mock_parse:
            result = await enter_deal_id(update, ctx)

        mock_parse.assert_not_called()
        assert result == ENTER_ACCOUNT


# ── D. usdt_enter_manual_callback ─────────────────────────────────────────────

class TestUsdtEnterManualCallback:

    @pytest.mark.asyncio
    async def test_d1_sets_manual_flag(self):
        """D1: нажата кнопка → usdt_manual = True в user_data."""
        query = MagicMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        ctx = MagicMock()
        ctx.user_data = {}

        result = await usdt_enter_manual_callback(update, ctx)

        assert ctx.user_data.get("usdt_manual") is True

    @pytest.mark.asyncio
    async def test_d1_returns_enter_deal_id(self):
        """D1: после нажатия кнопки остаёмся в состоянии ENTER_DEAL_ID."""
        query = MagicMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        ctx = MagicMock()
        ctx.user_data = {}

        result = await usdt_enter_manual_callback(update, ctx)

        assert result == ENTER_DEAL_ID

    @pytest.mark.asyncio
    async def test_d1_edits_message_with_prompt(self):
        """D1: бот редактирует сообщение, просит ввести TX ID."""
        query = MagicMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        ctx = MagicMock()
        ctx.user_data = {}

        await usdt_enter_manual_callback(update, ctx)

        query.edit_message_text.assert_called_once()
        call_text = query.edit_message_text.call_args[0][0].lower()
        assert "tx id" in call_text or "сделки" in call_text or "транзакци" in call_text
