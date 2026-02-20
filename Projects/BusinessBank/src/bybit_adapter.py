"""
bybit_adapter.py — Парсер экспорта истории транзакций Bybit.

Поддерживаемые форматы экспорта Bybit:
  1. Transaction History CSV (Assets → Transaction History → Export)
     Колонки: Date(UTC), Type, Coin, Amount, Transaction ID, Address, Status

  2. P2P Order History CSV (P2P → Orders → Export)
     Колонки: Order ID, Created Time, Trade Type, Asset, Price, Volume, Total, Status

  3. Spot/Unified Account History
     Колонки: Date(UTC), Symbol, Side, Price, Qty, Amount, Fee, Status

  Также принимает русскоязычный вариант колонок.

Возвращает нормализованный DataFrame:
    date         — datetime операции
    tx_type      — тип: P2P_BUY | P2P_SELL | DEPOSIT | WITHDRAW | TRANSFER_IN | TRANSFER_OUT | FEE | OTHER
    coin         — монета (USDT, BTC и т.д.)
    amount       — сумма в монете (+ = приход, − = расход)
    amount_rub   — сумма в рублях (только для P2P-сделок)
    price_rub    — курс USDT/RUB (только для P2P)
    fee          — комиссия биржи
    purpose      — описание/назначение
    status       — статус (Completed / Cancelled / ...)
    tx_id        — ID транзакции / ордера
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ── Нормализованная схема ──────────────────────────────────────────────────────

BYBIT_COLUMNS = [
    "date",
    "tx_type",
    "coin",
    "amount",       # положительное = приход, отрицательное = расход
    "amount_rub",   # только для P2P
    "price_rub",    # только для P2P
    "fee",
    "purpose",
    "status",
    "tx_id",
]

# Типы транзакций
TX_P2P_BUY      = "P2P_BUY"       # покупка USDT за RUB (приход USDT)
TX_P2P_SELL     = "P2P_SELL"      # продажа USDT за RUB (расход USDT)
TX_DEPOSIT      = "DEPOSIT"       # пополнение с внешнего кошелька
TX_WITHDRAW     = "WITHDRAW"      # вывод на внешний кошелёк (бизнес-платёж)
TX_TRANSFER_IN  = "TRANSFER_IN"   # перевод между субаккаунтами (приход)
TX_TRANSFER_OUT = "TRANSFER_OUT"  # перевод между субаккаунтами (расход)
TX_FEE          = "FEE"           # комиссия биржи
TX_OTHER        = "OTHER"         # прочее


# ── Маппинг типов Bybit → внутренние типы ─────────────────────────────────────

_TYPE_MAP = {
    # английские
    "p2p buy":       TX_P2P_BUY,
    "buy":           TX_P2P_BUY,
    "p2p sell":      TX_P2P_SELL,
    "sell":          TX_P2P_SELL,
    "deposit":       TX_DEPOSIT,
    "withdraw":      TX_WITHDRAW,
    "withdrawal":    TX_WITHDRAW,
    "transfer in":   TX_TRANSFER_IN,
    "transferin":    TX_TRANSFER_IN,
    "transfer out":  TX_TRANSFER_OUT,
    "transferout":   TX_TRANSFER_OUT,
    "trading fee":   TX_FEE,
    "fee":           TX_FEE,
    # русские
    "покупка":       TX_P2P_BUY,
    "продажа":       TX_P2P_SELL,
    "пополнение":    TX_DEPOSIT,
    "вывод":         TX_WITHDRAW,
    "перевод входящий": TX_TRANSFER_IN,
    "перевод исходящий": TX_TRANSFER_OUT,
    "комиссия":      TX_FEE,
}


def _norm_type(raw: str) -> str:
    """Нормализует тип транзакции Bybit → внутренний TX_* тип."""
    key = str(raw).strip().lower()
    return _TYPE_MAP.get(key, TX_OTHER)


def _parse_amount(val) -> float:
    """Разбирает сумму в любом формате (строка или число)."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace(" ", "").replace("\u00a0", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _detect_format(df: pd.DataFrame) -> str:
    """
    Определяет формат экспорта по заголовкам.

    Returns:
        'transaction_history' | 'p2p_orders' | 'spot_history' | 'unknown'
    """
    cols_lower = {c.strip().lower() for c in df.columns}

    # Transaction History: Date(UTC), Type, Coin, Amount
    if {"type", "coin", "amount"}.issubset(cols_lower):
        return "transaction_history"

    # P2P Orders: Order ID, Trade Type, Asset, Volume, Total
    if {"asset", "volume", "total"}.issubset(cols_lower) or \
       {"trade type", "asset"}.issubset(cols_lower):
        return "p2p_orders"

    # Spot: Symbol, Side, Qty
    if {"symbol", "side", "qty"}.issubset(cols_lower):
        return "spot_history"

    # Русские варианты
    if {"тип", "монета", "сумма"}.issubset(cols_lower):
        return "transaction_history"

    if {"тип сделки", "актив"}.issubset(cols_lower):
        return "p2p_orders"

    return "unknown"


def _find_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    """Находит первую подходящую колонку из кандидатов (нечувствительно к регистру)."""
    cols_map = {c.strip().lower(): c for c in df.columns}
    for cand in candidates:
        found = cols_map.get(cand.lower())
        if found is not None:
            return found
    return None


# ── Парсеры по форматам ────────────────────────────────────────────────────────

def _parse_transaction_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Формат: Assets → Transaction History → Export

    Типичные колонки:
        Date(UTC) | Type | Coin | Amount | Transaction ID | Address | Status
    """
    date_col   = _find_col(df, "Date(UTC)", "Date", "Дата", "date")
    type_col   = _find_col(df, "Type", "Тип", "type")
    coin_col   = _find_col(df, "Coin", "Монета", "Asset", "coin")
    amount_col = _find_col(df, "Amount", "Сумма", "amount")
    txid_col   = _find_col(df, "Transaction ID", "ID транзакции", "TXID", "tx_id")
    addr_col   = _find_col(df, "Address", "Адрес", "Wallet", "address")
    status_col = _find_col(df, "Status", "Статус", "status")

    rows = []
    for _, row in df.iterrows():
        date_raw = row.get(date_col, "") if date_col else ""
        try:
            dt = pd.to_datetime(date_raw, utc=True).tz_localize(None)
        except Exception:
            try:
                dt = pd.to_datetime(date_raw)
            except Exception:
                continue

        tx_type_raw = str(row.get(type_col, "")) if type_col else ""
        tx_type = _norm_type(tx_type_raw)
        coin = str(row.get(coin_col, "")).strip() if coin_col else ""
        amount = _parse_amount(row.get(amount_col)) if amount_col else 0.0
        status = str(row.get(status_col, "")).strip() if status_col else ""

        # Пропускаем незавершённые
        if status.lower() in ("cancelled", "failed", "отменена", "отменён"):
            continue

        # Знак суммы: расход = отрицательный
        if tx_type in (TX_WITHDRAW, TX_TRANSFER_OUT, TX_P2P_SELL, TX_FEE):
            amount = -abs(amount)
        else:
            amount = abs(amount)

        purpose = str(row.get(addr_col, "")).strip() if addr_col else ""
        tx_id = str(row.get(txid_col, "")).strip() if txid_col else ""

        rows.append({
            "date":       dt,
            "tx_type":    tx_type,
            "coin":       coin,
            "amount":     amount,
            "amount_rub": 0.0,
            "price_rub":  0.0,
            "fee":        0.0,
            "purpose":    purpose,
            "status":     status,
            "tx_id":      tx_id,
        })

    return pd.DataFrame(rows, columns=BYBIT_COLUMNS) if rows else pd.DataFrame(columns=BYBIT_COLUMNS)


def _parse_p2p_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Формат: P2P → My Orders → Export

    Типичные колонки:
        Order ID | Created Time | Trade Type | Asset | Price | Volume | Total | Status | Counterparty
    или:
        Order ID | Created Time | Trader | Type | Crypto | Price | Volume | Total | Status
    """
    date_col    = _find_col(df, "Created Time", "Order Time", "Дата", "Time", "date")
    type_col    = _find_col(df, "Trade Type", "Type", "Тип сделки", "Тип", "Side")
    asset_col   = _find_col(df, "Asset", "Crypto", "Монета", "Coin")
    price_col   = _find_col(df, "Price", "Цена")
    volume_col  = _find_col(df, "Volume", "Количество", "Amount", "Объём")
    total_col   = _find_col(df, "Total", "Итого", "Fiat Amount")
    status_col  = _find_col(df, "Status", "Статус")
    txid_col    = _find_col(df, "Order ID", "ID ордера", "OrderID")
    cp_col      = _find_col(df, "Counterparty", "Trader", "Контрагент")

    rows = []
    for _, row in df.iterrows():
        date_raw = row.get(date_col, "") if date_col else ""
        try:
            dt = pd.to_datetime(date_raw)
        except Exception:
            continue

        type_raw = str(row.get(type_col, "")).strip().lower() if type_col else ""
        # P2P Buy = покупаем USDT (USDT приходит)
        # P2P Sell = продаём USDT (USDT уходит)
        if "buy" in type_raw or "покупка" in type_raw:
            tx_type = TX_P2P_BUY
        elif "sell" in type_raw or "продажа" in type_raw:
            tx_type = TX_P2P_SELL
        else:
            tx_type = TX_OTHER

        status = str(row.get(status_col, "")).strip() if status_col else ""
        if status.lower() in ("cancelled", "failed", "appeal", "отменена", "отменён"):
            continue

        coin = str(row.get(asset_col, "USDT")).strip() if asset_col else "USDT"
        price = _parse_amount(row.get(price_col)) if price_col else 0.0
        volume = _parse_amount(row.get(volume_col)) if volume_col else 0.0
        total_rub = _parse_amount(row.get(total_col)) if total_col else 0.0
        tx_id = str(row.get(txid_col, "")).strip() if txid_col else ""
        counterparty = str(row.get(cp_col, "")).strip() if cp_col else ""

        # Знак: P2P Buy = USDT приходит (+), P2P Sell = уходит (-)
        amount = volume if tx_type == TX_P2P_BUY else -volume

        rows.append({
            "date":       dt,
            "tx_type":    tx_type,
            "coin":       coin,
            "amount":     amount,
            "amount_rub": total_rub if tx_type == TX_P2P_BUY else -total_rub,
            "price_rub":  price,
            "fee":        0.0,
            "purpose":    f"P2P {tx_type} | {counterparty}",
            "status":     status,
            "tx_id":      tx_id,
        })

    return pd.DataFrame(rows, columns=BYBIT_COLUMNS) if rows else pd.DataFrame(columns=BYBIT_COLUMNS)


def _parse_spot_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Формат: Spot/Unified Account Trade History

    Базовый парсинг — обычно нерелевантен для данного сценария.
    """
    date_col   = _find_col(df, "Date(UTC)", "Date", "Дата")
    symbol_col = _find_col(df, "Symbol", "Символ")
    side_col   = _find_col(df, "Side", "Сторона")
    qty_col    = _find_col(df, "Qty", "Filled Qty", "Количество")
    fee_col    = _find_col(df, "Fee", "Комиссия")
    status_col = _find_col(df, "Status", "Статус")

    rows = []
    for _, row in df.iterrows():
        date_raw = row.get(date_col, "") if date_col else ""
        try:
            dt = pd.to_datetime(date_raw)
        except Exception:
            continue

        side = str(row.get(side_col, "")).strip().lower() if side_col else ""
        tx_type = TX_P2P_BUY if side == "buy" else TX_P2P_SELL
        symbol = str(row.get(symbol_col, "")).strip() if symbol_col else ""
        qty = _parse_amount(row.get(qty_col)) if qty_col else 0.0
        fee = _parse_amount(row.get(fee_col)) if fee_col else 0.0
        status = str(row.get(status_col, "")).strip() if status_col else ""

        amount = qty if tx_type == TX_P2P_BUY else -qty

        rows.append({
            "date":       dt,
            "tx_type":    tx_type,
            "coin":       symbol,
            "amount":     amount,
            "amount_rub": 0.0,
            "price_rub":  0.0,
            "fee":        -abs(fee),
            "purpose":    symbol,
            "status":     status,
            "tx_id":      "",
        })

    return pd.DataFrame(rows, columns=BYBIT_COLUMNS) if rows else pd.DataFrame(columns=BYBIT_COLUMNS)


# ── Публичный API ──────────────────────────────────────────────────────────────

class BybitParser:
    """
    Читает экспорт Bybit (CSV или XLSX) и возвращает нормализованный DataFrame.

    Поддерживает все основные форматы экспорта Bybit (автодетект по заголовкам).
    """

    def parse(self, file_path: Path) -> pd.DataFrame:
        """
        Args:
            file_path: путь к файлу (.csv или .xlsx)

        Returns:
            DataFrame с колонками из BYBIT_COLUMNS
        """
        logger.info("Парсинг Bybit экспорта: %s", file_path.name)

        raw_df = self._read_file(file_path)
        if raw_df is None or raw_df.empty:
            logger.warning("Файл пустой или не удалось прочитать: %s", file_path.name)
            return pd.DataFrame(columns=BYBIT_COLUMNS)

        fmt = _detect_format(raw_df)
        logger.info("Определён формат: %s (строк: %d)", fmt, len(raw_df))

        parsers = {
            "transaction_history": _parse_transaction_history,
            "p2p_orders":          _parse_p2p_orders,
            "spot_history":        _parse_spot_history,
        }

        if fmt not in parsers:
            logger.error(
                "Неизвестный формат Bybit. Колонки файла: %s\n"
                "Поддерживаемые форматы: transaction_history, p2p_orders, spot_history\n"
                "Экспортируйте через: Assets → Transaction History → Export",
                list(raw_df.columns)
            )
            raise ValueError(
                f"Неизвестный формат Bybit-экспорта ({file_path.name}). "
                f"Колонки: {list(raw_df.columns)}"
            )

        df = parsers[fmt](raw_df)

        if df.empty:
            logger.warning("Нет транзакций после парсинга: %s", file_path.name)
            return df

        df = df.sort_values("date").reset_index(drop=True)

        # Только USDT (основная валюта для данного сценария)
        usdt_mask = df["coin"].str.upper().str.contains("USDT|USD", na=False)
        if usdt_mask.any() and not df[~usdt_mask].empty:
            logger.info(
                "Найдено монет: %s (оставляем все)",
                df["coin"].value_counts().to_dict()
            )

        logger.info(
            "Прочитано: %d операций | "
            "Приход USDT: %.2f | Расход USDT: %.2f",
            len(df),
            df[df["amount"] > 0]["amount"].sum(),
            abs(df[df["amount"] < 0]["amount"].sum()),
        )

        return df

    def _read_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Читает CSV или XLSX с несколькими попытками кодировок."""
        suffix = file_path.suffix.lower()

        if suffix == ".xlsx":
            try:
                return pd.read_excel(file_path)
            except Exception as e:
                logger.error("Ошибка чтения XLSX: %s", e)
                return None

        # CSV — пробуем кодировки
        for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
            try:
                df = pd.read_csv(file_path, encoding=enc)
                if not df.empty:
                    return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error("Ошибка чтения CSV (%s): %s", enc, e)
                return None

        logger.error("Не удалось определить кодировку файла: %s", file_path.name)
        return None


def parse_bybit(file_path: Path) -> pd.DataFrame:
    """Единая точка входа для парсинга Bybit экспорта."""
    return BybitParser().parse(file_path)


def classify_bybit_tx(row: pd.Series) -> dict:
    """
    Классификатор транзакций Bybit для ДБЗ журнала.

    Возвращает dict с ключами: category, subcategory, pnl_sign, comment
    """
    tx_type = row.get("tx_type", TX_OTHER)
    coin = str(row.get("coin", "")).upper()
    purpose = str(row.get("purpose", ""))
    amount = float(row.get("amount", 0))

    if tx_type == TX_P2P_BUY:
        return {
            "category":    "Покупка USDT",
            "subcategory": "P2P (личные карты → Bybit)",
            "pnl_sign":    "internal",  # не влияет на P&L напрямую
            "comment":     f"P2P покупка {abs(amount):.2f} {coin}",
        }

    if tx_type == TX_P2P_SELL:
        return {
            "category":    "Продажа USDT",
            "subcategory": "P2P (Bybit → личные карты)",
            "pnl_sign":    "internal",
            "comment":     f"P2P продажа {abs(amount):.2f} {coin}",
        }

    if tx_type == TX_WITHDRAW:
        # Вывод с Bybit = бизнес-платёж (карго, доставка и т.д.)
        _CARGO_RE = re.compile(
            r"карго|cargo|доставка|delivery|склад|warehouse|посредник|агент",
            re.IGNORECASE
        )
        if _CARGO_RE.search(purpose):
            subcat = "Карго / Доставка"
        else:
            subcat = "Бизнес-платёж USDT"
        return {
            "category":    "Расходы USDT",
            "subcategory": subcat,
            "pnl_sign":    "expense",   # расход в P&L
            "comment":     purpose[:80] or f"Вывод {abs(amount):.2f} {coin}",
        }

    if tx_type == TX_DEPOSIT:
        return {
            "category":    "Пополнение USDT",
            "subcategory": "Внешний депозит",
            "pnl_sign":    "internal",
            "comment":     f"Депозит {abs(amount):.2f} {coin}",
        }

    if tx_type in (TX_TRANSFER_IN, TX_TRANSFER_OUT):
        return {
            "category":    "Внутренний перевод Bybit",
            "subcategory": "Между субаккаунтами",
            "pnl_sign":    "internal",
            "comment":     purpose[:80],
        }

    if tx_type == TX_FEE:
        return {
            "category":    "Комиссия Bybit",
            "subcategory": "Trading Fee",
            "pnl_sign":    "expense",
            "comment":     f"Комиссия {abs(amount):.4f} {coin}",
        }

    return {
        "category":    "Прочее USDT",
        "subcategory": "",
        "pnl_sign":    "manual",
        "comment":     purpose[:80],
    }
