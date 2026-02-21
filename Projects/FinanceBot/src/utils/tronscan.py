"""
Tronscan transaction parser.

Принимает ссылку вида:
    https://tronscan.org/#/transaction/HASH
    https://tronscan.io/#/transaction/HASH

Возвращает: hash, sender, recipient, amount, token.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TRONSCAN_API = "https://apilist.tronscan.org/api/transaction-info"

# 1 TRX = 1_000_000 SUN
SUN_PER_TRX = 1_000_000


@dataclass
class TronTransaction:
    tx_hash: str
    sender: str
    recipient: str
    amount: float
    token: str  # "TRX", "USDT", etc.

    def __str__(self) -> str:
        return (
            f"Hash:      {self.tx_hash}\n"
            f"Sender:    {self.sender}\n"
            f"Recipient: {self.recipient}\n"
            f"Amount:    {self.amount} {self.token}"
        )


def extract_hash_from_url(url: str) -> Optional[str]:
    """Вытащить tx hash из Tronscan-ссылки."""
    # https://tronscan.org/#/transaction/ABC123...
    match = re.search(r"transaction/([a-fA-F0-9]{64})", url)
    if match:
        return match.group(1)
    # На случай если передали просто хеш без URL
    if re.fullmatch(r"[a-fA-F0-9]{64}", url.strip()):
        return url.strip()
    return None


def fetch_transaction(tx_hash: str, timeout: int = 15) -> Optional[dict]:
    """Получить данные транзакции через Tronscan API."""
    try:
        response = requests.get(
            TRONSCAN_API,
            params={"hash": tx_hash},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not data or "hash" not in data:
            logger.error("Транзакция не найдена: %s", tx_hash)
            return None
        return data
    except requests.exceptions.Timeout:
        logger.error("Timeout при запросе к Tronscan API")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP ошибка: %s", e)
        return None
    except requests.exceptions.RequestException as e:
        logger.exception("Ошибка запроса к Tronscan API: %s", e)
        return None


def parse_transaction(data: dict) -> Optional[TronTransaction]:
    """
    Разобрать ответ Tronscan API.

    Поддерживает:
    - TRX-переводы (contractType == 1)
    - TRC20-переводы (USDT, USDC и т.п.)
    """
    tx_hash = data.get("hash", "")
    sender = data.get("ownerAddress", "")

    # --- TRC20 transfer ---
    trc20_info = data.get("trc20TransferInfo") or []
    if trc20_info:
        info = trc20_info[0]  # берём первый трансфер
        recipient = info.get("to_address", "")
        symbol = info.get("symbol", "TOKEN")
        decimals = int(info.get("decimals", 6))
        raw_amount = int(info.get("amount_str", info.get("amount", 0)))
        amount = raw_amount / (10 ** decimals)
        return TronTransaction(
            tx_hash=tx_hash,
            sender=sender,
            recipient=recipient,
            amount=amount,
            token=symbol,
        )

    # --- TRX transfer (contractType = 1) ---
    contract_data = data.get("contractData", {})
    recipient = contract_data.get("to_address", data.get("toAddress", ""))
    raw_amount = contract_data.get("amount", 0)
    amount = raw_amount / SUN_PER_TRX

    if not recipient:
        logger.warning("Не удалось определить получателя: %s", data)
        return None

    return TronTransaction(
        tx_hash=tx_hash,
        sender=sender,
        recipient=recipient,
        amount=amount,
        token="TRX",
    )


def parse_tronscan_url(url: str) -> Optional[TronTransaction]:
    """
    Главная функция — принять ссылку, вернуть транзакцию.

    Args:
        url: Tronscan-ссылка или голый tx hash

    Returns:
        TronTransaction или None при ошибке
    """
    tx_hash = extract_hash_from_url(url)
    if not tx_hash:
        logger.error("Не удалось извлечь tx hash из: %s", url)
        return None

    logger.info("Запрашиваю транзакцию: %s", tx_hash)
    data = fetch_transaction(tx_hash)
    if not data:
        return None

    return parse_transaction(data)


# --- CLI / быстрая проверка ---
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Использование: python tronscan_parser.py <tronscan_url_or_hash>")
        sys.exit(1)

    tx = parse_tronscan_url(sys.argv[1])
    if tx:
        print(tx)
    else:
        print("Не удалось разобрать транзакцию")
        sys.exit(1)
