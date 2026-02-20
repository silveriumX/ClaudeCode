"""
Ozon "Начисления и компенсации" Excel parser.

Reads the monthly Excel file downloaded from Ozon Seller portal:
    Аналитика → Финансовые отчёты → Начисления и компенсации по отправлениям

File-based approach: no API calls. Handles the Excel report directly.

Ozon report specifics:
    - One row per operation type per shipment
    - 'amount' field = NET delta (positive = income, negative = cost)
    - SUM(amount) over all rows = NET payout to seller for the period
    - Contains product names (unlike WB report which requires Content API join)

Output schema (compatible with merge_pnl.py unified journal):
    date, amount, currency, amount_rub, amount_usdt,
    source, tx_type, category, recipient, purpose,
    entity, is_shared, account_name, tx_id

Invariants:
    - amount_rub is signed: + income, - cost
    - amount_usdt is always 0.0
    - entity is set from caller argument, not auto-detected
    - is_shared is always False
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Column aliases for Ozon Excel "Начисления" report.
# Ozon has two report variants with slightly different column names;
# aliases are tried left-to-right, first match wins.
_COL_ALIASES: Dict[str, List[str]] = {
    "posting_number": [
        "ID начисления",
        "Номер отправления",
        "posting_number",
        "ID отправления",
    ],
    "operation_date": [
        "Дата начисления",
        "Дата операции",
        "operation_date",
    ],
    "operation_type_group": [
        "Группа услуг",
        "Тип операции",
    ],
    "operation_type_name": [
        "Тип начисления",
        "operation_type_name",
        "Название операции",
    ],
    "product_name": [
        "Название товара",
        "Товар",
        "name",
        "Наименование товара",
    ],
    "sku": [
        "Артикул",
        "Ozon ID",
        "sku",
        "SKU",
    ],
    "accruals_for_sale": [
        "За продажу или возврат до вычета комиссий",
        "accruals_for_sale",
        "За продажу до вычета комиссий",
    ],
    "sale_commission": [
        "Комиссия за продажу",
        "sale_commission",
        "Комиссия",
    ],
    "delivery_charge": [
        "Логистика",
        "delivery_charge",
        "Стоимость доставки",
        "Доставка",
    ],
    "return_delivery_charge": [
        "Обратная логистика",
        "return_delivery_charge",
        "Стоимость возврата",
    ],
    "amount": [
        "Итого",
        "amount",
        "Итоговая сумма",
        "Начислено",
    ],
}

# Ozon operation type → unified tx_type mapping
_TX_TYPE_MAP: Dict[str, str] = {
    "доставка покупателю": "Продажа Ozon",
    "товары": "Продажа Ozon",
    "продажа": "Продажа Ozon",
    "возврат": "Возврат Ozon",
    "возврат от покупателя": "Возврат Ozon",
    "комиссия за продажу": "Комиссия Ozon",
    "обработка отправления": "Обработка Ozon",
    "последняя миля": "Логистика Ozon",
    "логистика": "Логистика Ozon",
    "реклама": "Реклама Ozon",
    "хранение": "Хранение Ozon",
    "штраф": "Штраф Ozon",
    "компенсация": "Компенсация Ozon",
}

# Unified output columns (compatible with merge_pnl.py)
UNIFIED_COLUMNS = [
    "date",
    "amount",
    "currency",
    "amount_rub",
    "amount_usdt",
    "source",
    "tx_type",
    "category",
    "recipient",
    "purpose",
    "entity",
    "is_shared",
    "account_name",
    "tx_id",
]


def _resolve_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Map logical field names to actual DataFrame column names."""
    cols_lower = {c.strip().lower(): c for c in df.columns}
    resolved: Dict[str, Optional[str]] = {}

    for field, aliases in _COL_ALIASES.items():
        found = None
        for alias in aliases:
            if alias in df.columns:
                found = alias
                break
            if alias.lower() in cols_lower:
                found = cols_lower[alias.lower()]
                break
        resolved[field] = found
        if found is None:
            logger.debug("Ozon parser: column '%s' not found (aliases: %s)", field, aliases)

    return resolved


def _get_val(row: pd.Series, col: Optional[str], default=None):
    if col is None or col not in row.index:
        return default
    val = row[col]
    if pd.isna(val):
        return default
    return val


def _parse_float(val, default: float = 0.0) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    try:
        return float(str(val).replace(" ", "").replace(",", ".").replace("\xa0", ""))
    except (ValueError, TypeError):
        return default


def _parse_date(val) -> Optional[pd.Timestamp]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val
    try:
        return pd.to_datetime(str(val).strip(), dayfirst=True)
    except (ValueError, TypeError):
        return None


def _detect_tx_type(operation_name: str, operation_group: str, amount: float) -> str:
    """
    Determine unified tx_type from Ozon operation name/group.
    Falls back to generic income/expense based on amount sign.
    """
    text = f"{operation_name} {operation_group}".lower().strip()
    for keyword, tx_type in _TX_TYPE_MAP.items():
        if keyword in text:
            return tx_type
    # Generic fallback
    return "Доход Ozon" if amount >= 0 else "Расход Ozon"


def _detect_category(tx_type: str) -> str:
    """Map tx_type to P&L category."""
    mapping = {
        "Продажа Ozon": "Доходы WB/Ozon",
        "Возврат Ozon": "Доходы WB/Ozon",
        "Комиссия Ozon": "Комиссии / Эквайринг",
        "Обработка Ozon": "Логистика / Фулфилмент",
        "Логистика Ozon": "Логистика / Фулфилмент",
        "Реклама Ozon": "Реклама",
        "Хранение Ozon": "Хранение",
        "Штраф Ozon": "Штрафы / Удержания",
        "Компенсация Ozon": "Доходы WB/Ozon",
        "Доход Ozon": "Доходы WB/Ozon",
        "Расход Ozon": "Прочие расходы",
    }
    return mapping.get(tx_type, "Прочее Ozon")


def parse_ozon_excel(
    path: Path,
    entity: str,
    sheet_index: int = 0,
) -> pd.DataFrame:
    """
    Parse Ozon "Начисления и компенсации" Excel into unified journal rows.

    Each row in the Ozon report becomes one row in the output,
    categorized by operation type.

    The key field is 'amount' (Итого) which already contains the NET delta
    for that operation: positive = seller receives money, negative = seller pays.

    Args:
        path:        Path to the Ozon Excel file.
        entity:      Legal entity code (e.g., 'VAS', 'LYA'). All rows tagged with it.
        sheet_index: Excel sheet index to read (default 0 = first sheet).

    Returns:
        DataFrame with UNIFIED_COLUMNS. Empty DataFrame on parse error.

    Side effects:
        None (read-only).
    """
    try:
        raw = pd.read_excel(path, sheet_name=sheet_index, dtype=str)
    except Exception as exc:
        logger.error("Ozon parser: cannot read '%s': %s", path, exc)
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    if raw.empty:
        logger.warning("Ozon parser: '%s' is empty", path)
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    cols = _resolve_columns(raw)

    if cols["amount"] is None:
        logger.error(
            "Ozon parser: key column 'amount' (Итого) not found in '%s'. "
            "Available columns: %s",
            path,
            list(raw.columns[:20]),
        )
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    rows: list = []
    skipped = 0

    for _, row in raw.iterrows():
        date = _parse_date(_get_val(row, cols["operation_date"]))
        if date is None:
            skipped += 1
            continue

        amount = _parse_float(_get_val(row, cols["amount"]))
        if amount == 0.0:
            continue  # zero-amount rows add no value to P&L

        op_type_name = str(_get_val(row, cols["operation_type_name"], "")).strip()
        op_type_group = str(_get_val(row, cols["operation_type_group"], "")).strip()
        product_name = str(_get_val(row, cols["product_name"], "")).strip()
        posting_number = str(_get_val(row, cols["posting_number"], "")).strip()
        sku = str(_get_val(row, cols["sku"], "")).strip()

        tx_type = _detect_tx_type(op_type_name, op_type_group, amount)
        category = _detect_category(tx_type)

        op_label = op_type_name or op_type_group or "Ozon"
        purpose_parts = [op_label]
        if product_name and product_name not in ("nan", "None", ""):
            purpose_parts.append(product_name)
        purpose = " | ".join(purpose_parts)

        rows.append({
            "date": date,
            "amount": abs(amount),
            "currency": "RUB",
            "amount_rub": amount,           # signed NET: + income, - cost
            "amount_usdt": 0.0,
            "source": "ozon_report",
            "tx_type": tx_type,
            "category": category,
            "recipient": "",
            "purpose": purpose,
            "entity": entity,
            "is_shared": False,
            "account_name": "Ozon",
            "tx_id": posting_number,
        })

    if skipped:
        logger.warning("Ozon parser: %d rows skipped (no parseable date)", skipped)

    if not rows:
        logger.warning("Ozon parser: no rows extracted from '%s'", path)
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    df = pd.DataFrame(rows)[UNIFIED_COLUMNS]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    net = df["amount_rub"].sum()
    sales = df[df["amount_rub"] > 0]["amount_rub"].sum()
    costs = df[df["amount_rub"] < 0]["amount_rub"].sum()

    logger.info(
        "Ozon report '%s': %d rows | entity=%s | доходы=%.0f затраты=%.0f NET=%.0f RUB",
        path.name, len(df), entity, sales, costs, net,
    )
    return df


def net_payout_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate Ozon journal rows into monthly P&L summary by type.

    Args:
        df: Output of parse_ozon_excel().

    Returns:
        DataFrame: month, tx_type, amount_rub, rows_count.
    """
    if df.empty:
        return pd.DataFrame(columns=["month", "tx_type", "amount_rub", "rows_count"])

    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.to_period("M").dt.start_time
    summary = (
        tmp.groupby(["month", "tx_type"])
        .agg(amount_rub=("amount_rub", "sum"), rows_count=("amount_rub", "count"))
        .reset_index()
        .sort_values(["month", "tx_type"])
    )
    return summary
