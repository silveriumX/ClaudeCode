# -*- coding: utf-8 -*-
"""
Upload categorized transactions to Google Sheet "Мои финансы".

Sheet ID: 1J1eAUCsqRPjdvEwC-_3YIULphcZMAjiRPLJ9QQo1Z4A

Features:
- Сводка: группы отсортированы по убыванию суммы
- Строки деталей сгруппированы (collapsible) через Sheets API
- Заголовки групп выделены цветом и жирным
- Лист "Транзакции": все операции с колонкой для комментариев

Run after parse_statements.py and categorize.py.

Usage:
    python upload_to_sheets.py
"""

import csv
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = Path(os.getenv("PERSONAL_FINANCE_DATA_DIR", WORKSPACE_ROOT / "Личное" / "Мои деньги"))
CAT_CSV = DATA_DIR / "parsed" / "categorized.csv"
ALL_CSV = DATA_DIR / "parsed" / "all.csv"

SHEET_ID = "1J1eAUCsqRPjdvEwC-_3YIULphcZMAjiRPLJ9QQo1Z4A"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CRED_CANDIDATES = [
    WORKSPACE_ROOT / ".credentials" / "credentials.json",
    WORKSPACE_ROOT / "Projects" / "FinanceBot" / "service_account.json",
    WORKSPACE_ROOT / "Projects" / "ChatManager" / "service_account.json",
]

PERIOD_ORDER = ["окт-ноя 2025", "ноя-дек 2025", "дек-янв 2026", "янв-фев 2026"]

FILE_TO_PERIOD = {
    "ноябрь 2025.pdf":  "окт-ноя 2025",
    "декабрь 2025.pdf": "ноя-дек 2025",
    "январь 2026.pdf":  "дек-янв 2026",
    "февраль 2026.pdf": "янв-фев 2026",
}

# Groups: СБЕРЕЖЕНИЯ always goes last regardless of sort order
GROUPS: list[tuple[str, list[str]]] = [
    ("ЖИЛЬЁ", ["Аренда квартиры"]),
    ("ЕДА", ["Еда/Продукты", "Кафе/Рестораны", "Кафе/Кофейни", "Доставка еды"]),
    ("ЗДОРОВЬЕ", ["Медицина/Клиники", "Медицина/Аптеки", "Медицина/Операция", "Медицина/Прочее", "Психолог"]),
    ("КРАСОТА", ["Красота"]),
    ("СПОРТ", ["Спорт/Бокс"]),
    ("ТРАНСПОРТ", ["Транспорт/Такси", "Транспорт/Метро и ж/д"]),
    ("РАЗВЛЕЧЕНИЯ", ["Развлечения", "Путешествия/Виза"]),
    ("ОБУЧЕНИЕ", ["Образование"]),
    ("ПОДПИСКИ", [
        "Подписки/МегаФон", "Подписки/Яндекс Плюс",
        "Подписки/ЯндексБанк", "Подписки/Тинькофф",
        "Подписки/GetCourse", "Подписки/RusProfile", "Подписки/Starter Pay",
        "Подписки/Прочее",
    ]),
    ("ПЕРЕВОДЫ", ["Маркетплейс (Озон/ВБ)", "Мама", "Переводы (неизвестно)"]),
    ("НАЛОГИ", ["Налоги"]),
    ("РАЗНОЕ", ["Чаевые", "Разное", "Прочее"]),
    # СБЕРЕЖЕНИЯ always last
    ("СБЕРЕЖЕНИЯ", ["Сбережения/USDT"]),
]

# Colors
COLOR_GROUP_BG  = {"red": 0.157, "green": 0.306, "blue": 0.475}  # dark blue
COLOR_GROUP_FG  = {"red": 1.0,   "green": 1.0,   "blue": 1.0}   # white
COLOR_TOTAL_BG  = {"red": 0.1,   "green": 0.1,   "blue": 0.1}   # almost black
COLOR_INCOME_BG = {"red": 0.133, "green": 0.388, "blue": 0.212}  # dark green
COLOR_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
COLOR_BLACK = {"red": 0.0, "green": 0.0, "blue": 0.0}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_client() -> gspread.Client:
    for p in CRED_CANDIDATES:
        if p.exists():
            logger.info(f"Using credentials: {p}")
            creds = Credentials.from_service_account_file(str(p), scopes=SCOPES)
            return gspread.authorize(creds)
    raise FileNotFoundError(
        "No credentials found. Expected one of:\n"
        + "\n".join(f"  {p}" for p in CRED_CANDIDATES)
    )


# ---------------------------------------------------------------------------
# Sheet helpers
# ---------------------------------------------------------------------------

def recreate_worksheet(sh: gspread.Spreadsheet, title: str, rows: int = 2000, cols: int = 12) -> gspread.Worksheet:
    """Delete old and create fresh worksheet (clears row groups too)."""
    try:
        old = sh.worksheet(title)
        sh.del_worksheet(old)
        time.sleep(0.5)
    except gspread.WorksheetNotFound:
        pass
    ws = sh.add_worksheet(title=title, rows=rows, cols=cols)
    logger.info(f"Created worksheet '{title}'")
    return ws


def write_data(ws: gspread.Worksheet, data: list[list[Any]]) -> None:
    if data:
        ws.update(data, value_input_option="USER_ENTERED")
    logger.info(f"  Written {len(data)} rows to '{ws.title}'")


def add_row_groups(sh: gspread.Spreadsheet, ws_id: int, groups: list[tuple[int, int]]) -> None:
    """Add collapsible row groups via Sheets API. groups = [(start_0idx, end_0idx_exclusive), ...]"""
    if not groups:
        return
    requests = [
        {
            "addDimensionGroup": {
                "range": {
                    "sheetId": ws_id,
                    "dimension": "ROWS",
                    "startIndex": start,
                    "endIndex": end,
                }
            }
        }
        for start, end in groups
    ]
    sh.batch_update({"requests": requests})
    logger.info(f"  Added {len(groups)} row groups")


def batch_format(sh: gspread.Spreadsheet, ws_id: int, formats: list[dict]) -> None:
    """Apply multiple cell formats in one API call."""
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": ws_id,
                    **fmt["range"],
                },
                "cell": {"userEnteredFormat": fmt["format"]},
                "fields": "userEnteredFormat",
            }
        }
        for fmt in formats
    ]
    if requests:
        sh.batch_update({"requests": requests})


def range_spec(start_row: int, end_row: int, start_col: int = 0, end_col: int = 6) -> dict:
    """0-indexed range spec for Sheets API."""
    return {
        "startRowIndex": start_row,
        "endRowIndex": end_row,
        "startColumnIndex": start_col,
        "endColumnIndex": end_col,
    }


def col_widths(sh: gspread.Spreadsheet, ws_id: int) -> None:
    """Set column widths for the summary sheet."""
    widths = [220, 110, 110, 110, 110, 110]  # A=category, B-E=periods, F=total
    requests = [
        {
            "updateDimensionProperties": {
                "range": {"sheetId": ws_id, "dimension": "COLUMNS",
                          "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": w},
                "fields": "pixelSize",
            }
        }
        for i, w in enumerate(widths)
    ]
    sh.batch_update({"requests": requests})


# ---------------------------------------------------------------------------
# Transactions sheet
# ---------------------------------------------------------------------------

def build_txn_rows(rows: list[dict]) -> list[list[Any]]:
    header = ["Период", "Дата", "Описание", "Сумма", "Категория", "Источник", "Комментарий"]
    data = [header]
    for r in sorted(rows, key=lambda x: (x["period"], x["date"])):
        data.append([
            r["period"], r["date"], r["description"],
            float(r["amount"]), r["category"], r["source"], "",
        ])
    return data


def format_txn_sheet(sh: gspread.Spreadsheet, ws: gspread.Worksheet, n_data_rows: int) -> None:
    ws_id = ws.id
    formats = [
        # Header row
        {
            "range": range_spec(0, 1, 0, 7),
            "format": {
                "backgroundColor": COLOR_GROUP_BG,
                "textFormat": {"bold": True, "foregroundColor": COLOR_WHITE, "fontSize": 10},
                "horizontalAlignment": "CENTER",
            },
        },
        # Comment column header — orange tint to hint it's editable
        {
            "range": range_spec(0, 1, 6, 7),
            "format": {
                "backgroundColor": {"red": 0.9, "green": 0.6, "blue": 0.1},
                "textFormat": {"bold": True, "foregroundColor": COLOR_BLACK, "fontSize": 10},
            },
        },
    ]
    batch_format(sh, ws_id, formats)
    ws.freeze(rows=1)
    widths = [120, 90, 320, 90, 180, 80, 200]
    requests = [
        {
            "updateDimensionProperties": {
                "range": {"sheetId": ws_id, "dimension": "COLUMNS",
                          "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": w},
                "fields": "pixelSize",
            }
        }
        for i, w in enumerate(widths)
    ]
    sh.batch_update({"requests": requests})
    logger.info("  Formatted Транзакции")


# ---------------------------------------------------------------------------
# Summary sheet
# ---------------------------------------------------------------------------

def compute_cat_period(rows: list[dict]) -> dict:
    cp: dict = defaultdict(lambda: defaultdict(float))
    for r in rows:
        cp[r["category"]][r["period"]] += float(r["amount"])
    return cp


def build_summary_rows(
    cat_period: dict,
) -> tuple[list[list[Any]], list[int], list[tuple[int, int]], int, int]:
    """
    Returns:
        data             -- list of rows to write
        group_header_rows -- 0-indexed row indices of group headers (for formatting)
        detail_groups    -- (start, end) for addDimensionGroup API calls
        total_row_idx    -- row index of the grand total row
        income_header_idx -- row index of the income section header
    """
    SAVINGS_GROUP = "СБЕРЕЖЕНИЯ"
    expense_groups = [(g, cats) for g, cats in GROUPS if g != SAVINGS_GROUP]
    savings_groups = [(g, cats) for g, cats in GROUPS if g == SAVINGS_GROUP]

    def group_total(cats: list[str]) -> float:
        return sum(
            sum(cat_period.get(c, {}).values())
            for c in cats
        )

    # Sort expense groups ascending (most negative = largest expense first)
    sorted_expense = sorted(expense_groups, key=lambda x: group_total(x[1]))
    all_groups_ordered = sorted_expense + savings_groups

    header = ["Категория"] + PERIOD_ORDER + ["ИТОГО"]
    data: list[list[Any]] = [header]
    group_header_rows: list[int] = []
    detail_groups: list[tuple[int, int]] = []

    grand_by_period: dict = defaultdict(float)
    grand_total = 0.0

    for group_name, cats in all_groups_ordered:
        is_savings = group_name == SAVINGS_GROUP

        active_cats = [c for c in cats if c in cat_period]
        if not active_cats:
            continue

        g_by_period: dict = defaultdict(float)
        g_total = 0.0
        for c in active_cats:
            for p in PERIOD_ORDER:
                v = cat_period[c].get(p, 0)
                g_by_period[p] += v
                g_total += v

        # Group header row
        g_row_idx = len(data)
        group_header_rows.append(g_row_idx)
        g_vals = [round(g_by_period.get(p, 0), 2) for p in PERIOD_ORDER]
        data.append([group_name] + g_vals + [round(g_total, 2)])

        # Detail rows
        det_start = len(data)
        for cat in active_cats:
            vals = [round(cat_period[cat].get(p, 0), 2) for p in PERIOD_ORDER]
            row_total = round(sum(vals), 2)
            data.append([f"    {cat}"] + vals + [row_total])

        # For СБЕРЕЖЕНИЯ: add USDT equivalent row
        if is_savings and "Сбережения/USDT" in cat_period:
            USDT_RATE = 80.0
            usdt_vals = [
                round(abs(cat_period["Сбережения/USDT"].get(p, 0)) / USDT_RATE, 0)
                for p in PERIOD_ORDER
            ]
            usdt_total = round(sum(usdt_vals), 0)
            data.append(
                [f"    \u21b3 Эквивалент USDT (~{int(USDT_RATE)} руб/USDT)"]
                + [f"~{int(v)} USDT" if v else "\u2014" for v in usdt_vals]
                + [f"~{int(usdt_total)} USDT"]
            )

        det_end = len(data)
        if det_end > det_start:
            detail_groups.append((det_start, det_end))

        if not is_savings:
            for p in PERIOD_ORDER:
                grand_by_period[p] += g_by_period.get(p, 0)
            grand_total += g_total

    # Grand total row
    data.append([])  # blank separator
    total_row_idx = len(data)
    g_vals = [round(grand_by_period.get(p, 0), 2) for p in PERIOD_ORDER]
    data.append(["ИТОГО РАСХОДЫ (без сбережений)"] + g_vals + [round(grand_total, 2)])

    # Income section
    data.append([])
    income_header_idx = len(data)
    data.append(["ПОСТУПЛЕНИЯ"] + PERIOD_ORDER + ["ИТОГО"])

    deposit_by_period: dict = defaultdict(float)
    with open(ALL_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["direction"] == "наличные_внесение":
                p = FILE_TO_PERIOD.get(row["file"], "")
                if p:
                    deposit_by_period[p] += float(row["amount"])

    dep_vals = [round(deposit_by_period.get(p, 0), 2) for p in PERIOD_ORDER]
    data.append(["    Внесения наличных (бизнес-доход)"] + dep_vals + [round(sum(dep_vals), 2)])

    return data, group_header_rows, detail_groups, total_row_idx, income_header_idx


def format_summary_sheet(
    sh: gspread.Spreadsheet,
    ws: gspread.Worksheet,
    group_header_rows: list[int],
    total_row_idx: int,
    income_header_idx: int,
    n_rows: int,
) -> None:
    ws_id = ws.id
    formats = []

    # Column header (row 0)
    formats.append({
        "range": range_spec(0, 1, 0, 6),
        "format": {
            "backgroundColor": COLOR_GROUP_BG,
            "textFormat": {"bold": True, "foregroundColor": COLOR_WHITE, "fontSize": 10},
            "horizontalAlignment": "CENTER",
        },
    })

    # Group header rows
    for r in group_header_rows:
        formats.append({
            "range": range_spec(r, r + 1, 0, 6),
            "format": {
                "backgroundColor": COLOR_GROUP_BG,
                "textFormat": {"bold": True, "foregroundColor": COLOR_WHITE, "fontSize": 11},
                "horizontalAlignment": "LEFT",
            },
        })
        formats.append({
            "range": range_spec(r, r + 1, 1, 6),
            "format": {
                "backgroundColor": COLOR_GROUP_BG,
                "textFormat": {"bold": True, "foregroundColor": COLOR_WHITE, "fontSize": 11},
                "horizontalAlignment": "RIGHT",
                "numberFormat": {"type": "NUMBER", "pattern": "#,##0"},
            },
        })

    # Grand total row
    for col_range in [(0, 6), (1, 6)]:
        formats.append({
            "range": range_spec(total_row_idx, total_row_idx + 1, *col_range),
            "format": {
                "backgroundColor": COLOR_TOTAL_BG,
                "textFormat": {"bold": True, "foregroundColor": COLOR_WHITE, "fontSize": 11},
                "horizontalAlignment": "RIGHT" if col_range[0] == 1 else "LEFT",
                **({"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}} if col_range[0] == 1 else {}),
            },
        })

    # Income header
    formats.append({
        "range": range_spec(income_header_idx, income_header_idx + 1, 0, 6),
        "format": {
            "backgroundColor": COLOR_INCOME_BG,
            "textFormat": {"bold": True, "foregroundColor": COLOR_WHITE, "fontSize": 11},
        },
    })

    # Number format for all data cells
    formats.append({
        "range": range_spec(1, n_rows, 1, 6),
        "format": {
            "numberFormat": {"type": "NUMBER", "pattern": "#,##0"},
            "horizontalAlignment": "RIGHT",
        },
    })

    batch_format(sh, ws_id, formats)
    ws.freeze(rows=1)
    col_widths(sh, ws_id)
    logger.info("  Formatted Сводка по категориям")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=== Загрузка транзакций в Google Sheets ===")

    if not CAT_CSV.exists():
        logger.error(f"categorized.csv not found at {CAT_CSV}")
        logger.error("Run categorize.py first")
        sys.exit(1)

    if not ALL_CSV.exists():
        logger.error(f"all.csv not found at {ALL_CSV}")
        logger.error("Run parse_statements.py first")
        sys.exit(1)

    with open(CAT_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    logger.info(f"Loaded {len(rows)} transactions from categorized.csv")

    gc = get_client()
    sh = gc.open_by_key(SHEET_ID)
    logger.info(f"Opened: '{sh.title}'")

    # ---- Transactions sheet ----
    logger.info("\nWriting Транзакции...")
    ws_txn = recreate_worksheet(sh, "Транзакции", rows=2000, cols=8)
    txn_data = build_txn_rows(rows)
    write_data(ws_txn, txn_data)
    format_txn_sheet(sh, ws_txn, len(txn_data))

    # ---- Summary sheet ----
    logger.info("\nWriting Сводка по категориям...")
    ws_sum = recreate_worksheet(sh, "Сводка по категориям", rows=100, cols=8)
    cat_period = compute_cat_period(rows)
    sum_data, group_header_rows, detail_groups, total_row_idx, income_header_idx = build_summary_rows(cat_period)
    write_data(ws_sum, sum_data)
    add_row_groups(sh, ws_sum.id, detail_groups)
    format_summary_sheet(sh, ws_sum, group_header_rows, total_row_idx, income_header_idx, len(sum_data))

    # Remove blank Лист1 if it exists
    for ws in sh.worksheets():
        if ws.title == "Лист1" and len(sh.worksheets()) > 1:
            vals = ws.get_all_values()
            if not any(c for row in vals for c in row):
                sh.del_worksheet(ws)
                logger.info("Deleted blank 'Лист1'")

    logger.info("\n=== ГОТОВО ===")
    logger.info(f"Транзакций: {len(rows)}")
    logger.info(f"URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
