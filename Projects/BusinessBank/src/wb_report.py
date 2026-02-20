"""
WB "Финансовый отчёт" (агрегированный) Excel parser.

Reads the aggregate financial report downloaded from WB Partners:
    Финансы → Финансовые отчёты → Финансовый отчет → скачать Excel

THIS IS NOT the detailed "Отчёт реализации" (line-by-line).
This is the AGGREGATE report: one row per weekly report period.

File structure:
    Row 0 — column totals (skip)
    Row 1 — short headers (skip)
    Row 2 — full column headers  ← real header
    Row 3+ — weekly report rows

Key fields:
    №отчета              — weekly report ID (matches bank transfer reference)
    Дата начала/конца    — report period
    Продажа              — gross sales (includes SPP/loyalty adjustments)
    К перечислению за товар — net goods payout (after WB commission)
    Стоимость логистики  — logistics cost (deducted from seller)
    Стоимость хранения   — storage cost (INCLUDED in this report)
    Стоимость операций на приемке — intake/acceptance cost
    Прочие удержания/выплаты — other deductions or additions
    Общая сумма штрафов  — total fines
    Итого к оплате       — NET amount WB transfers to seller's bank account

Reconciliation logic:
    SUM("Итого к оплате") for a date range ≈ bank transfer from WB INN
    WB may batch multiple weekly reports into one bank transfer.

Output schema (compatible with merge_pnl.py unified journal):
    date, amount, currency, amount_rub, amount_usdt,
    source, tx_type, category, recipient, purpose,
    entity, is_shared, account_name, tx_id

Each weekly WB report row → multiple output rows (one per cost type):
    Продажа WB          — gross revenue (+)
    Комиссия WB         — WB commission = Продажа - К перечислению (-)
    Логистика WB        — logistics cost (-)
    Хранение WB         — storage cost (-)
    Приёмка WB          — acceptance cost (-)
    Штрафы WB           — fines (-)
    Прочие удержания WB — other deductions (+/-)

Invariants:
    - amount_rub: signed (+ income, - deduction)
    - amount_usdt: always 0.0
    - entity: set from caller argument
    - is_shared: always False
    - SUM(amount_rub for all rows of one report) ≈ "Итого к оплате"
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Column name → possible aliases in WB Excel (tried left-to-right)
# WB occasionally renames columns between report versions
_COL_MAP = {
    "report_id": [
        "№ отчета",
        "№отчета",
        "Номер отчета",
    ],
    "legal_entity": [
        "Юридическое лицо",
        "Поставщик",
    ],
    "date_from": [
        "Дата начала",
        "Начало периода",
    ],
    "date_to": [
        "Дата конца",
        "Конец периода",
    ],
    # "Период" — combined date range used in short-header (manual) format:
    # e.g. "2025-02-03-2025-02-09"
    "period": [
        "Период",
    ],
    "report_type": [
        "Тип отчета",
        "Вид отчета",
    ],
    "sales": [
        "Продажа",
        "Сумма продаж",
    ],
    "spp_discount": [
        "В том числе Компенсация скидки по программе лояльности",
        "Компенсация скидки по программе лояльности",
    ],
    "goods_payout": [
        "К перечислению за товар",
        "К перечислению",
    ],
    "logistics": [
        "Стоимость логистики",
        "Логистика",
    ],
    "storage": [
        "Стоимость хранения",
        "Хранение",
    ],
    "acceptance": [
        "Стоимость операций на приемке",
        "Приёмка",
        "Платная приёмка",
        "Стоимость платной приемки",
    ],
    "other_deductions": [
        "Прочие удержания/выплаты",
        "Прочие удержания",
    ],
    "fines": [
        "Общая сумма штрафов",
        "Штрафы",
        "Другие виды штрафов",
    ],
    "net_total": [
        "Итого к оплате",
        "Итого",
    ],
    "currency": [
        "Валюта",
    ],
}

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


def _find_col(df: pd.DataFrame, field: str) -> Optional[str]:
    """Return the actual column name for a logical field, or None."""
    aliases = _COL_MAP.get(field, [])
    cols_lower = {c.strip().lower(): c for c in df.columns}
    for alias in aliases:
        if alias in df.columns:
            return alias
        if alias.lower() in cols_lower:
            return cols_lower[alias.lower()]
    return None


def _resolve_cols(df: pd.DataFrame) -> dict:
    resolved = {}
    for field in _COL_MAP:
        col = _find_col(df, field)
        resolved[field] = col
        if col is None:
            logger.debug("WB parser: field '%s' not found", field)
    return resolved


def _float(val, default: float = 0.0) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    try:
        return float(str(val).replace(" ", "").replace(",", ".").replace("\xa0", ""))
    except (ValueError, TypeError):
        return default


def _date(val) -> Optional[pd.Timestamp]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val
    try:
        return pd.to_datetime(str(val).strip(), dayfirst=False)
    except (ValueError, TypeError):
        return None


def _detect_header_row(path: Path, sheet_name) -> int:
    """
    Detect which row contains the real column headers.

    WB aggregate report (raw export):
        Row 0 = totals, Row 1 = short headers, Row 2 = full headers (→ use row 2)
    Manual compiled format:
        Row 0 = headers directly (→ use row 0)

    Priority: prefer the row containing "Юридическое лицо" (only in full headers).
    Fallback: first row containing both "перечислению" and "логистики".

    Returns the 0-based row index to use as header.
    """
    try:
        probe = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=5, dtype=str)
    except Exception:
        return 0

    best_row = None

    for i, row in probe.iterrows():
        vals = [str(v).strip() for v in row.values if str(v).strip() not in ("nan", "")]
        row_text = " ".join(vals).lower()

        # Best match: full WB export header — contains "юридическое лицо"
        if "юридическое лицо" in row_text:
            return int(i)

        # Good match: short header or manual header with key financial columns
        if best_row is None and "перечислению" in row_text and "логистики" in row_text:
            best_row = int(i)

    return best_row if best_row is not None else 0


def parse_wb_excel(
    path: Path,
    entity: str,
    sheet_name: str = 0,
) -> pd.DataFrame:
    """
    Parse WB aggregate "Финансовый отчёт" Excel into unified journal rows.

    Supports both:
    - Raw WB export (header at row 2, totals at row 0)
    - Manual compiled format (header at row 0)

    Each weekly report row → multiple output rows per cost category:
        Продажа WB, Комиссия WB, Логистика WB, Хранение WB,
        Приёмка WB, Штрафы WB, Прочие удержания WB

    Use `net_payout_by_report()` to get per-report NET totals for bank reconciliation.

    Args:
        path:       Path to the WB Excel file.
        entity:     Legal entity code (e.g., 'DBZ'). Applied to all rows.
        sheet_name: Sheet name or 0-based index (default: first sheet).

    Returns:
        DataFrame with UNIFIED_COLUMNS. Empty on parse error.

    Side effects:
        None (read-only).
    """
    header_row = _detect_header_row(path, sheet_name)

    try:
        raw = pd.read_excel(
            path,
            sheet_name=sheet_name,
            header=header_row,
            dtype=str,
        )
    except Exception as exc:
        logger.error("WB parser: cannot read '%s' sheet '%s': %s", path, sheet_name, exc)
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    # Drop fully empty rows and the leading empty column (col A in WB export is always NaN)
    raw = raw.dropna(how="all")
    raw = raw.loc[:, raw.columns.notna()]
    # Remove columns that are entirely NaN (WB export often has trailing empty cols)
    raw = raw.dropna(axis=1, how="all")

    cols = _resolve_cols(raw)

    if cols["net_total"] is None and cols["sales"] is None:
        logger.error(
            "WB parser: no recognized financial columns in '%s' sheet '%s'. "
            "Detected columns: %s",
            path.name, sheet_name, list(raw.columns[:15]),
        )
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    rows: list = []
    skipped = 0

    for _, row in raw.iterrows():
        # Resolve date: prefer date_to, then date_from, then parse from "Период" field
        date = None
        date_end_str = ""
        date_start_str = ""

        if cols.get("date_to"):
            date = _date(row.get(cols["date_to"]))
            date_end_str = str(row.get(cols["date_to"], "")).split("T")[0]
        if date is None and cols.get("date_from"):
            date = _date(row.get(cols["date_from"]))
        if cols.get("date_from"):
            date_start_str = str(row.get(cols["date_from"], "")).split("T")[0]

        # "Период" = "2025-02-03-2025-02-09" (combined start-end)
        if date is None and cols.get("period"):
            period_val = str(row.get(cols["period"], "")).strip()
            # Format: YYYY-MM-DD-YYYY-MM-DD (two ISO dates joined by "-")
            # Split: the second date starts at position 11
            if len(period_val) >= 21 and period_val[10] == "-":
                date_start_str = period_val[:10]
                date_end_str = period_val[11:]
                date = _date(date_end_str)
                if not date_start_str:
                    date_start_str = period_val[:10]

        if date is None:
            skipped += 1
            continue

        report_id = str(row.get(cols["report_id"], "") if cols.get("report_id") else "").strip()
        # Remove float suffix if report_id was read as float (e.g., "250793392.0")
        if report_id.endswith(".0"):
            report_id = report_id[:-2]

        # Skip the totals row (report_id == "Итого" or empty with totals)
        if report_id.lower() in ("итого", "nan", "", "№ отчета", "№отчета"):
            skipped += 1
            continue

        period_str = ""
        if date_start_str and date_end_str:
            period_str = f"{date_start_str} – {date_end_str}"
        elif date_start_str:
            period_str = date_start_str

        sales = _float(row.get(cols["sales"]) if cols["sales"] else None)
        goods_payout = _float(row.get(cols["goods_payout"]) if cols["goods_payout"] else None)
        logistics = _float(row.get(cols["logistics"]) if cols["logistics"] else None)
        storage = _float(row.get(cols["storage"]) if cols["storage"] else None)
        acceptance = _float(row.get(cols["acceptance"]) if cols["acceptance"] else None)
        fines = _float(row.get(cols["fines"]) if cols["fines"] else None)
        other = _float(row.get(cols["other_deductions"]) if cols["other_deductions"] else None)
        net_total = _float(row.get(cols["net_total"]) if cols["net_total"] else None)

        # WB commission is implicit: Продажа - К перечислению за товар
        # (WB takes their cut before "К перечислению за товар")
        commission = sales - goods_payout if (sales and goods_payout) else 0.0

        purpose_suffix = f"отч.{report_id} [{period_str}]" if period_str else f"отч.{report_id}"

        def _row(tx_type: str, category: str, amount_rub: float) -> dict:
            return {
                "date": date,
                "amount": abs(amount_rub),
                "currency": "RUB",
                "amount_rub": amount_rub,
                "amount_usdt": 0.0,
                "source": "wb_report",
                "tx_type": tx_type,
                "category": category,
                "recipient": "",
                "purpose": f"{tx_type} | {purpose_suffix}",
                "entity": entity,
                "is_shared": False,
                "account_name": "WB",
                "tx_id": report_id,
            }

        # Gross sales (always include if non-zero)
        if sales != 0.0:
            rows.append(_row("Продажа WB", "Доходы WB/Ozon", sales))

        # WB commission (negative — deduction)
        if abs(commission) > 0.5:  # ignore rounding noise
            rows.append(_row("Комиссия WB", "Комиссии / Эквайринг", -abs(commission)))

        # Logistics
        if logistics != 0.0:
            rows.append(_row("Логистика WB", "Логистика / Фулфилмент", -abs(logistics)))

        # Storage
        if storage != 0.0:
            rows.append(_row("Хранение WB", "Хранение", -abs(storage)))

        # Acceptance
        if acceptance != 0.0:
            rows.append(_row("Приёмка WB", "Логистика / Фулфилмент", -abs(acceptance)))

        # Fines
        if fines != 0.0:
            rows.append(_row("Штрафы WB", "Штрафы / Удержания", -abs(fines)))

        # Other deductions/payments (signed: may be positive compensation)
        if other != 0.0:
            rows.append(_row("Прочие WB", "Прочие расходы", other))

    if skipped:
        logger.debug("WB parser: %d rows skipped (no date or totals row)", skipped)

    if not rows:
        logger.warning("WB parser: no rows extracted from '%s' sheet '%s'", path.name, sheet_name)
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    df = pd.DataFrame(rows)[UNIFIED_COLUMNS]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date", "tx_id", "tx_type"]).reset_index(drop=True)

    report_count = df["tx_id"].nunique()
    sales_total = df[df["tx_type"] == "Продажа WB"]["amount_rub"].sum()
    net = df["amount_rub"].sum()

    logger.info(
        "WB report '%s' sheet '%s': %d weekly reports | entity=%s | "
        "продажи=%.0f NET=%.0f RUB",
        path.name, sheet_name, report_count, entity, sales_total, net,
    )
    return df


def parse_all_sheets(path: Path, entity: str) -> pd.DataFrame:
    """
    Parse all ФинОт-* sheets from a multi-sheet workbook and combine.

    Useful when one Excel file contains reports for multiple sellers
    (e.g., 'Фин. отчет (Общий).xlsx' with ФинОт ДБЗ-2, ФинОт МН-2, etc.).

    Filters sheets by `entity` to avoid loading unrelated seller data.
    If no entity-matched sheets found, loads all ФинОт* sheets.

    Args:
        path:   Path to the multi-sheet Excel file.
        entity: Legal entity code (e.g., 'DBZ'). Used for sheet filtering and tagging.

    Returns:
        Combined DataFrame with UNIFIED_COLUMNS.
    """
    try:
        xl = pd.ExcelFile(path)
        sheet_names = xl.sheet_names
    except Exception as exc:
        logger.error("WB parser: cannot open '%s': %s", path, exc)
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    # Entity → sheet name keyword mapping (expand as needed)
    _ENTITY_KEYWORDS = {
        "DBZ": ["ДБЗ", "DBZ", "Пирожкова"],
        "MN": ["МН", "MN", "Мышей", "Алипов"],
        "VAS": ["Вася", "VAS", "Шляхов"],
        "LYA": ["Илья", "LYA", "Дмитриев"],
        "MAKS": ["Максим", "MAKS", "Абрамов"],
        "LIFE": ["Шоппилайф", "LIFE", "Shoplife"],
        "HUB": ["SH", "HUB", "ShopHub"],
        "ALEX": ["Александр", "ALEX", "Макеев"],
    }

    keywords = _ENTITY_KEYWORDS.get(entity, [entity])
    # Match sheets that contain entity keywords AND start with "ФинОт"
    matched = [
        s for s in sheet_names
        if s.startswith("ФинОт") and any(kw.lower() in s.lower() for kw in keywords)
    ]

    if not matched:
        # Fall back: all ФинОт sheets
        matched = [s for s in sheet_names if s.startswith("ФинОт")]
        if matched:
            logger.warning(
                "WB parser: no sheets matched entity '%s' in '%s'. "
                "Loading all ФинОт sheets: %s",
                entity, path.name, matched,
            )

    if not matched:
        logger.error("WB parser: no ФинОт sheets found in '%s'", path.name)
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    frames = []
    for sheet in matched:
        logger.info("WB parser: loading sheet '%s' for entity %s", sheet, entity)
        df = parse_wb_excel(path, entity, sheet_name=sheet)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["date", "tx_id"]).reset_index(drop=True)

    # Deduplicate: same (tx_id, tx_type) from multiple sheets
    # e.g. "ФинОт ДБЗ" and "ФинОт ДБЗ-2" may cover overlapping periods
    before = len(combined)
    combined = combined.drop_duplicates(subset=["tx_id", "tx_type"], keep="first")
    dupes = before - len(combined)
    if dupes:
        logger.info("WB parser: removed %d duplicate rows across sheets", dupes)

    combined = combined.sort_values(["date", "tx_id"]).reset_index(drop=True)
    return combined


def net_payout_by_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute NET payout per weekly report ID for bank reconciliation.

    The NET total should equal the bank transfer from WB for that report.
    WB may batch multiple weekly reports into a single bank transfer.

    Args:
        df: Output of parse_wb_excel() or parse_all_sheets().

    Returns:
        DataFrame: tx_id, date, net_payout_rub, gross_sales, rows.
    """
    if df.empty:
        return pd.DataFrame(columns=["tx_id", "date", "net_payout_rub", "gross_sales", "rows"])

    summary = (
        df.groupby("tx_id")
        .agg(
            date=("date", "max"),
            net_payout_rub=("amount_rub", "sum"),
            gross_sales=("amount_rub", lambda x: x[df.loc[x.index, "tx_type"] == "Продажа WB"].sum()),
            rows=("amount_rub", "count"),
        )
        .reset_index()
        .sort_values("date")
    )
    return summary


def summarize_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly P&L summary: revenue, costs by type, NET.

    Args:
        df: Output of parse_wb_excel() or parse_all_sheets().

    Returns:
        DataFrame: month, tx_type, amount_rub, reports_count.
    """
    if df.empty:
        return pd.DataFrame(columns=["month", "tx_type", "amount_rub", "reports_count"])

    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.to_period("M").dt.start_time
    summary = (
        tmp.groupby(["month", "tx_type"])
        .agg(
            amount_rub=("amount_rub", "sum"),
            reports_count=("tx_id", "nunique"),
        )
        .reset_index()
        .sort_values(["month", "tx_type"])
    )
    return summary
