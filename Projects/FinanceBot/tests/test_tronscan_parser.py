"""
Тесты парсера Tronscan — src/utils/tronscan.py
===============================================
Покрываем:
 - extract_hash_from_url   (чистая функция, без сети)
 - parse_transaction        (разбор dict из API)
 - parse_tronscan_url       (интеграция: hash + API + parse, сеть мокается)

Запуск: inv test  или  .venv/Scripts/python -m pytest tests/test_tronscan_parser.py -v
"""
from unittest.mock import MagicMock, patch

import pytest

from src.utils.tronscan import (
    TronTransaction,
    extract_hash_from_url,
    parse_transaction,
    parse_tronscan_url,
)

VALID_HASH = "a9b8acbda7a0631baf1950f5d8008cb8327f795cc56b32b51aa9d9cd4541594e"  # pragma: allowlist secret


# ══════════════════════════════════════════════════════════════════
# extract_hash_from_url
# ══════════════════════════════════════════════════════════════════

class TestExtractHashFromUrl:
    """extract_hash_from_url — чистая функция, сеть не нужна."""

    def test_tronscan_org_url(self):
        url = f"https://tronscan.org/#/transaction/{VALID_HASH}"
        assert extract_hash_from_url(url) == VALID_HASH

    def test_tronscan_io_url(self):
        url = f"https://tronscan.io/#/transaction/{VALID_HASH}"
        assert extract_hash_from_url(url) == VALID_HASH

    def test_raw_hash_64_chars(self):
        assert extract_hash_from_url(VALID_HASH) == VALID_HASH

    def test_raw_hash_with_whitespace(self):
        assert extract_hash_from_url(f"  {VALID_HASH}  ") == VALID_HASH

    def test_uppercase_hash(self):
        upper = VALID_HASH.upper()
        assert extract_hash_from_url(upper) == upper

    def test_random_text_returns_none(self):
        assert extract_hash_from_url("Привет мир") is None

    def test_short_hex_returns_none(self):
        assert extract_hash_from_url("abc123") is None

    def test_empty_string_returns_none(self):
        assert extract_hash_from_url("") is None

    def test_deal_id_text_returns_none(self):
        """Обычный ID сделки (#UD823470) не должен восприниматься как хеш."""
        assert extract_hash_from_url("#UD823470") is None

    def test_arbitrary_number_returns_none(self):
        assert extract_hash_from_url("12345") is None


# ══════════════════════════════════════════════════════════════════
# parse_transaction
# ══════════════════════════════════════════════════════════════════

class TestParseTransaction:
    """parse_transaction — разбирает dict из Tronscan API, сеть не нужна."""

    def _trc20_data(
        self,
        tx_hash=VALID_HASH,
        sender="SENDER_ADDR",
        recipient="RECIPIENT_ADDR",
        amount_str="1500000000",
        decimals=6,
        symbol="USDT",
    ):
        return {
            "hash": tx_hash,
            "ownerAddress": sender,
            "trc20TransferInfo": [
                {
                    "from_address": sender,
                    "to_address": recipient,
                    "amount_str": amount_str,
                    "decimals": decimals,
                    "symbol": symbol,
                }
            ],
        }

    def _trx_data(
        self,
        tx_hash=VALID_HASH,
        sender="SENDER_ADDR",
        recipient="RECIPIENT_ADDR",
        amount_sun=1_500_000_000,
    ):
        return {
            "hash": tx_hash,
            "ownerAddress": sender,
            "contractData": {
                "to_address": recipient,
                "amount": amount_sun,
            },
            "trc20TransferInfo": [],
        }

    # --- TRC20 ---

    def test_trc20_returns_correct_hash(self):
        tx = parse_transaction(self._trc20_data())
        assert tx.tx_hash == VALID_HASH

    def test_trc20_returns_correct_sender(self):
        tx = parse_transaction(self._trc20_data(sender="THZD5HGDdVig5zf4hqtu3LrPMRV7Fd8ts4"))  # pragma: allowlist secret
        assert tx.sender == "THZD5HGDdVig5zf4hqtu3LrPMRV7Fd8ts4"  # pragma: allowlist secret

    def test_trc20_returns_correct_recipient(self):
        tx = parse_transaction(self._trc20_data(recipient="THG8FA1XJy8kRMtFny7yvr1L73j1tjQf54"))  # pragma: allowlist secret
        assert tx.recipient == "THG8FA1XJy8kRMtFny7yvr1L73j1tjQf54"  # pragma: allowlist secret

    def test_trc20_converts_amount_by_decimals(self):
        """1_500_000_000 raw / 10^6 = 1500.0 USDT."""
        tx = parse_transaction(self._trc20_data(amount_str="1500000000", decimals=6))
        assert tx.amount == pytest.approx(1500.0)

    def test_trc20_token_symbol(self):
        tx = parse_transaction(self._trc20_data(symbol="USDT"))
        assert tx.token == "USDT"

    def test_trc20_small_amount(self):
        tx = parse_transaction(self._trc20_data(amount_str="1000000", decimals=6))
        assert tx.amount == pytest.approx(1.0)

    def test_trc20_large_amount(self):
        tx = parse_transaction(self._trc20_data(amount_str="100000000000", decimals=6))
        assert tx.amount == pytest.approx(100000.0)

    # --- TRX ---

    def test_trx_converts_sun_to_trx(self):
        """1_500_000_000 SUN / 1_000_000 = 1500 TRX."""
        tx = parse_transaction(self._trx_data(amount_sun=1_500_000_000))
        assert tx.amount == pytest.approx(1500.0)

    def test_trx_token_is_trx(self):
        tx = parse_transaction(self._trx_data())
        assert tx.token == "TRX"

    def test_trx_returns_correct_recipient(self):
        tx = parse_transaction(self._trx_data(recipient="THG8FA1XJy8kRMtFny7yvr1L73j1tjQf54"))  # pragma: allowlist secret
        assert tx.recipient == "THG8FA1XJy8kRMtFny7yvr1L73j1tjQf54"  # pragma: allowlist secret

    # --- Граничные случаи ---

    def test_missing_recipient_returns_none(self):
        data = {
            "hash": VALID_HASH,
            "ownerAddress": "SENDER",
            "contractData": {},
            "trc20TransferInfo": [],
        }
        assert parse_transaction(data) is None

    def test_trc20_takes_priority_over_trx(self):
        """Если есть trc20TransferInfo — используем его, игнорируем contractData."""
        data = self._trc20_data(amount_str="500000000", decimals=6)
        data["contractData"] = {"to_address": "OTHER_ADDR", "amount": 999_000_000}
        tx = parse_transaction(data)
        assert tx.token == "USDT"
        assert tx.amount == pytest.approx(500.0)


# ══════════════════════════════════════════════════════════════════
# parse_tronscan_url (интеграционный, сеть мокается)
# ══════════════════════════════════════════════════════════════════

class TestParseTronscanUrl:
    """parse_tronscan_url — мокаем requests.get."""

    def _mock_response(self, data: dict):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = data
        return resp

    def _api_data(self):
        return {
            "hash": VALID_HASH,
            "ownerAddress": "THZD5HGDdVig5zf4hqtu3LrPMRV7Fd8ts4",  # pragma: allowlist secret
            "trc20TransferInfo": [
                {
                    "to_address": "THG8FA1XJy8kRMtFny7yvr1L73j1tjQf54",  # pragma: allowlist secret
                    "amount_str": "1500000000",
                    "decimals": 6,
                    "symbol": "USDT",
                }
            ],
        }

    def test_valid_url_returns_transaction(self):
        url = f"https://tronscan.org/#/transaction/{VALID_HASH}"
        with patch("src.utils.tronscan.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(self._api_data())
            tx = parse_tronscan_url(url)
        assert isinstance(tx, TronTransaction)
        assert tx.tx_hash == VALID_HASH
        assert tx.amount == pytest.approx(1500.0)

    def test_raw_hash_returns_transaction(self):
        with patch("src.utils.tronscan.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(self._api_data())
            tx = parse_tronscan_url(VALID_HASH)
        assert tx is not None
        assert tx.token == "USDT"

    def test_invalid_url_returns_none_without_api_call(self):
        with patch("src.utils.tronscan.requests.get") as mock_get:
            result = parse_tronscan_url("не ссылка")
        mock_get.assert_not_called()
        assert result is None

    def test_api_timeout_returns_none(self):
        import requests as req_lib
        url = f"https://tronscan.org/#/transaction/{VALID_HASH}"
        with patch("src.utils.tronscan.requests.get", side_effect=req_lib.exceptions.Timeout):
            tx = parse_tronscan_url(url)
        assert tx is None

    def test_api_empty_response_returns_none(self):
        url = f"https://tronscan.org/#/transaction/{VALID_HASH}"
        with patch("src.utils.tronscan.requests.get") as mock_get:
            mock_get.return_value = self._mock_response({})  # нет ключа "hash"
            tx = parse_tronscan_url(url)
        assert tx is None

    def test_api_called_with_correct_hash(self):
        url = f"https://tronscan.org/#/transaction/{VALID_HASH}"
        with patch("src.utils.tronscan.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(self._api_data())
            parse_tronscan_url(url)
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["hash"] == VALID_HASH
