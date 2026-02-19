"""
FinanceBot Google Sheets adapter.

Reads paid expenses from FinanceBot Sheets and normalizes to unified journal schema.

Side effects:
    None. Read-only access to Google Sheets. Source data is never modified.

Invariants:
    - Output always has UNIFIED_COLUMNS columns.
    - amount is always positive (magnitude).
    - amount_rub is None when conversion rate is unknown.

Returns on error:
    Empty DataFrame with UNIFIED_COLUMNS. Error is logged.
"""
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread

logger = logging.getLogger(__name__)

# Unified output columns produced by this module
UNIFIED_COLUMNS = [
    "date",         # datetime
    "amount",       # float, positive
    "currency",     # str: RUB, USDT, BYN, KZT, CNY
    "amount_rub",   # float or None — amount converted to RUB
    "source",       # always 'financebot'
    "source_sheet", # original sheet name
    "tx_type",      # always 'Расход'
    "category",     # expense category from FinanceBot
    "recipient",    # payee
    "purpose",      # payment description
    "entity",       # legal entity code (DBZ, MN…) or '' if not detected
    "is_shared",    # True when entity == ''
    "account_name", # FinanceBot account name (e.g. BitPapa)
    "tx_id",        # FinanceBot request_id
]

# Column maps (0-based) — copied from FinanceBot src/sheets.py
_COL_MAIN = {
    "request_id": 0, "date": 1, "amount": 2, "currency": 3,
    "recipient": 4, "card_or_phone": 5, "bank": 6, "details": 7,
    "purpose": 8, "category": 9, "status": 10, "deal_id": 11,
    "account_name": 12, "amount_usdt": 13, "rate": 14,
}

_COL_USDT = {
    "request_id": 0, "date": 1, "amount": 2,
    "card_or_phone": 3, "purpose": 4, "category": 5,
    "status": 6, "deal_id": 7, "account_name": 8,
}

_COL_CNY = {
    "request_id": 0, "date": 1, "amount": 2,
    "bank": 3, "card_or_phone": 4, "qr_code_link": 5,
    "purpose": 6, "category": 7, "status": 8,
    "deal_id": 9, "account_name": 10,
}

# (sheet_name, col_map, fixed_currency or None to read from row)
_SHEET_CONFIGS = [
    ("Основные",            _COL_MAIN, None),
    ("Фактические расходы", _COL_MAIN, "RUB"),
    ("USDT",                _COL_USDT, "USDT"),
    ("CNY",                 _COL_CNY,  "CNY"),
]


def _cell(row: list, col_map: dict, key: str, default: str = "") -> str:
    idx = col_map.get(key)
    if idx is None or idx >= len(row):
        return default
    return str(row[idx]).strip()


def _parse_date(s: str) -> Optional[datetime]:
    """Parse DD.MM.YYYY → datetime, or None on failure."""
    try:
        return datetime.strptime(s.strip(), "%d.%m.%Y")
    except (ValueError, AttributeError):
        return None


def _detect_entity(
    purpose: str,
    recipient: str,
    patterns: Dict[str, List[str]],
) -> str:
    """
    Search entity code in purpose + recipient text via regex patterns.
    Returns entity code ('DBZ', 'MN'…) or '' if not found.
    """
    text = f"{purpose} {recipient}".upper()
    for code, regexes in patterns.items():
        for rx in regexes:
            if re.search(rx.upper(), text):
                return code
    return ""


def _to_rub(amount: float, currency: str, rates: Dict[str, float]) -> Optional[float]:
    """Convert amount to RUB. Returns None if rate is missing."""
    if currency == "RUB":
        return amount
    rate = rates.get(currency)
    if rate is None:
        return None
    return round(amount * rate, 2)


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=UNIFIED_COLUMNS)


def read_financebot_expenses(
    sheets_id: str,
    credentials_path: str,
    entity_patterns: Optional[Dict[str, List[str]]] = None,
    fx_rates: Optional[Dict[str, float]] = None,
    statuses: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Read paid expenses from all FinanceBot sheets and normalize to unified format.

    Reads sheets: Основные, Фактические расходы, USDT, CNY.
    Filters by status. Detects entity from purpose/recipient text.

    Args:
        sheets_id:        Google Sheets spreadsheet ID.
        credentials_path: Path to service_account.json.
        entity_patterns:  {entity_code: [regex_list]} for entity detection in text.
        fx_rates:         {currency: rub_rate}, e.g. {'USDT': 90.0}.
        statuses:         Status values to include (default: ['Оплачена', 'Факт']).

    Returns:
        DataFrame with UNIFIED_COLUMNS. Empty DataFrame on connection error.

    Side effects:
        None.

    Invariants:
        Sheets are never written to.
    """
    if statuses is None:
        statuses = ["Оплачена", "Факт"]
    if entity_patterns is None:
        entity_patterns = {}
    if fx_rates is None:
        fx_rates = {"BYN": 30.0, "KZT": 0.2, "USDT": 90.0, "CNY": 13.0}

    # Connect
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheets_id)
    except Exception as exc:
        logger.error("Cannot connect to FinanceBot Sheets: %s", exc)
        return _empty_df()

    rows: list = []

    for sheet_name, col_map, currency_fixed in _SHEET_CONFIGS:
        try:
            ws = spreadsheet.worksheet(sheet_name)
            all_rows = ws.get_all_values()
        except Exception as exc:
            logger.warning("Sheet '%s' skipped: %s", sheet_name, exc)
            continue

        if len(all_rows) < 2:
            continue

        skipped = 0
        for raw in all_rows[1:]:  # skip header row
            status = _cell(raw, col_map, "status")
            if status not in statuses:
                continue

            date = _parse_date(_cell(raw, col_map, "date"))
            if date is None:
                skipped += 1
                continue

            try:
                amount = float(
                    _cell(raw, col_map, "amount", "0")
                    .replace(" ", "")
                    .replace(",", ".")
                )
            except ValueError:
                skipped += 1
                continue

            if amount <= 0:
                continue

            currency = currency_fixed or _cell(raw, col_map, "currency", "RUB")

            # recipient: use 'recipient' field; fall back to account_name
            recipient = (
                _cell(raw, col_map, "recipient")
                or _cell(raw, col_map, "account_name")
                or _cell(raw, col_map, "card_or_phone")
            )
            purpose      = _cell(raw, col_map, "purpose")
            category     = _cell(raw, col_map, "category") or "Прочее"
            account_name = _cell(raw, col_map, "account_name")
            tx_id        = _cell(raw, col_map, "request_id")

            amount_rub = _to_rub(amount, currency, fx_rates)
            entity     = _detect_entity(purpose, recipient, entity_patterns)

            rows.append({
                "date":         date,
                "amount":       amount,
                "currency":     currency,
                "amount_rub":   amount_rub,
                "source":       "financebot",
                "source_sheet": sheet_name,
                "tx_type":      "Расход",
                "category":     category,
                "recipient":    recipient,
                "purpose":      purpose,
                "entity":       entity,
                "is_shared":    entity == "",
                "account_name": account_name,
                "tx_id":        tx_id,
            })

        if skipped:
            logger.debug("Sheet '%s': %d rows skipped (bad date/amount)", sheet_name, skipped)

    if not rows:
        logger.info("No paid expenses found in FinanceBot Sheets")
        return _empty_df()

    df = pd.DataFrame(rows)[UNIFIED_COLUMNS]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    shared_count = df["is_shared"].sum()
    tagged_count = len(df) - shared_count
    logger.info(
        "FinanceBot: %d paid expenses loaded (%d entity-tagged, %d shared)",
        len(df), tagged_count, shared_count,
    )
    return df
