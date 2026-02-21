#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reports_sheet.py — Построение листа «Финансовые отчёты WB» с группировкой.

Структура листа:
    ▼ 2024                              ← год (строка-итог, сворачивает месяцы)
      ▼ Январь 2024                     ← месяц (строка-итог, сворачивает недели)
          250793392  29.01–04.02  ...   ← еженедельный отчёт
          251899171  05.02–11.02  ...
      ▼ Февраль 2024
          ...
    ▼ 2025
      ...
    ИТОГО                               ← grand total

Через Google Sheets Row Grouping API:
    Клик ▶/▼ на боковой панели — разворачивает/сворачивает строки.
    По умолчанию все группы развёрнуты. Месяцы сворачиваются независимо.
"""

import logging
import time
from typing import Any

import gspread
import pandas as pd

logger = logging.getLogger(__name__)

# ─── Цвета ───────────────────────────────────────────────────────────────────

_C = {
    "header":      {"red": 0.122, "green": 0.216, "blue": 0.392},   # #1f3764 тёмно-синий
    "year":        {"red": 0.18,  "green": 0.33,  "blue": 0.55},    # #2e5590 синий
    "month":       {"red": 0.29,  "green": 0.53,  "blue": 0.91},    # #4a88e8 голубой
    "data_odd":    {"red": 0.937, "green": 0.949, "blue": 0.996},   # #eff2fe светло-синий
    "data_even":   {"red": 1.0,   "green": 1.0,   "blue": 1.0},     # белый
    "total":       {"red": 0.122, "green": 0.216, "blue": 0.392},   # #1f3764 тёмно-синий
    "white":       {"red": 1.0,   "green": 1.0,   "blue": 1.0},
    "dark_text":   {"red": 0.2,   "green": 0.2,   "blue": 0.2},
}

_MONTH_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}

# ─── Колонки листа ────────────────────────────────────────────────────────────

DISPLAY_COLS = [
    ("label",          "Период / № отчёта",             160),
    ("Тип отчета",     "Тип",                            90),
    ("Продажа",        "Продажа",                        120),
    ("К перечислению за товар", "К перечислению",        130),
    ("Стоимость логистики",     "Логистика",             110),
    ("Стоимость хранения",      "Хранение",              100),
    ("Стоимость операций на приемке", "Приёмка",         90),
    ("Прочие удержания/выплаты", "Удержания",            110),
    ("Общая сумма штрафов",     "Штрафы",                90),
    ("Корректировка Вознаграждения Вайлдберриз (ВВ)", "Корр. ВВ", 90),
    ("Итого к оплате", "Итого к оплате",                 130),
]

# Числовые колонки (для суммирования и форматирования)
NUM_SOURCE_COLS = [src for src, _, _ in DISPLAY_COLS if src not in ("label", "Тип отчета")]


# ─── Построитель листа ────────────────────────────────────────────────────────

def rebuild_reports_sheet(
    spreadsheet: gspread.Spreadsheet,
    df: pd.DataFrame,
    sheet_name: str = "Финансовые отчёты",
    report_type: str = "Основной",
) -> None:
    """
    Пересоздать лист с финансовыми отчётами и row-группировкой год/месяц.

    Args:
        spreadsheet:  gspread.Spreadsheet объект
        df:           DataFrame из WbGeneralParser.parse()
        sheet_name:   Имя листа
        report_type:  «Основной» или «По выкупам»
    """
    # ── 1. Пересоздать лист ──────────────────────────────────────────────────
    try:
        old = spreadsheet.worksheet(sheet_name)
        spreadsheet.del_worksheet(old)
        time.sleep(0.5)
    except gspread.WorksheetNotFound:
        pass

    ws = spreadsheet.add_worksheet(title=sheet_name, rows=2000, cols=len(DISPLAY_COLS))
    time.sleep(0.5)
    sheet_id = ws.id

    # ── 2. Подготовить данные ────────────────────────────────────────────────
    src = df[df["Тип отчета"] == report_type].copy() if "Тип отчета" in df.columns else df.copy()
    src["_Дата начала"] = pd.to_datetime(src["Дата начала"], errors="coerce")
    src["_Дата конца"]  = pd.to_datetime(src["Дата конца"],  errors="coerce")
    src = src.sort_values("_Дата начала").reset_index(drop=True)

    for col in NUM_SOURCE_COLS:
        if col in src.columns:
            src[col] = pd.to_numeric(src[col], errors="coerce").fillna(0.0)

    # ── 3. Построить строки и группы ─────────────────────────────────────────
    # Каждый элемент: (row_type, row_values_list)
    # row_type: "HEADER" | "YEAR" | "MONTH" | "DATA_ODD" | "DATA_EVEN" | "TOTAL"
    rows: list[tuple[str, list[Any]]] = []
    dim_groups: list[tuple[int, int]] = []  # (startIndex, endIndex) 0-based, exclusive

    # Заголовок
    headers = [display for _, display, _ in DISPLAY_COLS]
    rows.append(("HEADER", headers))

    grand = {c: 0.0 for c in NUM_SOURCE_COLS}

    src["_year"]  = src["_Дата начала"].dt.year
    src["_month"] = src["_Дата начала"].dt.month

    for year, year_grp in src.groupby("_year", sort=True):
        year_sums = _sum_group(year_grp)
        for c in NUM_SOURCE_COLS:
            grand[c] = grand.get(c, 0.0) + year_sums.get(c, 0.0)

        # Строка года (НЕ входит в год-группу — остаётся видимой при свёртке)
        rows.append(("YEAR", _build_row(f"▶  {int(year)}", "", year_sums)))
        year_group_start = len(rows)  # первая строка внутри год-группы

        data_counter = 0
        for month, month_grp in year_grp.groupby("_month", sort=True):
            month_sums = _sum_group(month_grp)
            month_label = f"   {_MONTH_RU[int(month)]} {int(year)}"

            # Строка месяца (входит в год-группу, НЕ входит в месяц-группу)
            rows.append(("MONTH", _build_row(month_label, "", month_sums)))
            month_group_start = len(rows)  # первая строка внутри месяц-группы

            for _, rep in month_grp.sort_values("_Дата начала").iterrows():
                date_str = ""
                if pd.notna(rep.get("_Дата начала")) and pd.notna(rep.get("_Дата конца")):
                    date_str = (
                        f"{rep['_Дата начала'].strftime('%d.%m')}–"
                        f"{rep['_Дата конца'].strftime('%d.%m.%y')}"
                    )
                label = f"      {int(rep.get('№ отчета', 0))}  {date_str}"
                rtype = "DATA_ODD" if data_counter % 2 == 0 else "DATA_EVEN"
                data_counter += 1
                rows.append((rtype, _build_row(label, str(rep.get("Тип отчета", "")), _row_nums(rep))))

            month_group_end = len(rows)  # exclusive
            if month_group_end > month_group_start:
                dim_groups.append((month_group_start, month_group_end))

        year_group_end = len(rows)  # exclusive
        if year_group_end > year_group_start:
            dim_groups.append((year_group_start, year_group_end))

    # Строка ИТОГО
    rows.append(("TOTAL", _build_row("ИТОГО", "", grand)))

    # ── 4. Записать данные ───────────────────────────────────────────────────
    all_values = [r[1] for r in rows]
    # Записываем чанками чтобы не превысить лимит запроса
    _write_chunks(ws, all_values)

    # ── 5. Форматирование ────────────────────────────────────────────────────
    fmt_requests = _build_format_requests(sheet_id, rows)

    # ── 6. Группировка строк ─────────────────────────────────────────────────
    group_requests = [
        {
            "addDimensionGroup": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start,
                    "endIndex": end,
                }
            }
        }
        for start, end in dim_groups
    ]

    # ── 7. Ширина колонок ────────────────────────────────────────────────────
    col_width_requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        }
        for i, (_, _, width) in enumerate(DISPLAY_COLS)
    ]

    # ── 8. Заморозить первую строку ──────────────────────────────────────────
    freeze_request = [{
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    }]

    all_requests = fmt_requests + group_requests + col_width_requests + freeze_request
    if all_requests:
        spreadsheet.batch_update({"requests": all_requests})

    logger.info(
        "Лист «%s» пересоздан: %d строк, %d групп",
        sheet_name, len(rows), len(dim_groups),
    )


# ─── Вспомогательные ─────────────────────────────────────────────────────────

def _sum_group(grp: pd.DataFrame) -> dict[str, float]:
    result = {}
    for col in NUM_SOURCE_COLS:
        if col in grp.columns:
            result[col] = float(grp[col].sum())
        else:
            result[col] = 0.0
    return result


def _row_nums(rep) -> dict[str, float]:
    result = {}
    for col in NUM_SOURCE_COLS:
        v = rep.get(col, 0)
        result[col] = float(v) if pd.notna(v) else 0.0
    return result


def _build_row(label: str, rtype: str, nums: dict[str, float]) -> list[Any]:
    row = []
    for src, _, _ in DISPLAY_COLS:
        if src == "label":
            row.append(label)
        elif src == "Тип отчета":
            row.append(rtype)
        else:
            row.append(round(nums.get(src, 0.0), 2))
    return row


def _write_chunks(ws: gspread.Worksheet, values: list[list], chunk: int = 500) -> None:
    if not values:
        return
    ws.update("A1", values[:chunk], value_input_option="USER_ENTERED")
    for i in range(chunk, len(values), chunk):
        ws.append_rows(values[i: i + chunk], value_input_option="USER_ENTERED")
        time.sleep(0.5)


# ─── Форматирование ───────────────────────────────────────────────────────────

def _build_format_requests(sheet_id: int, rows: list[tuple[str, list]]) -> list[dict]:
    """Собрать batch-запросы на форматирование всех строк."""
    requests = []
    n_cols = len(DISPLAY_COLS)

    for row_idx, (rtype, _) in enumerate(rows):
        if rtype == "HEADER":
            requests.append(_fmt_row(sheet_id, row_idx, n_cols, _C["header"], _C["white"], bold=True, size=10))
        elif rtype == "YEAR":
            requests.append(_fmt_row(sheet_id, row_idx, n_cols, _C["year"], _C["white"], bold=True, size=10))
            # Числа в году — правое выравнивание
            requests.append(_fmt_numbers(sheet_id, row_idx, n_cols))
        elif rtype == "MONTH":
            requests.append(_fmt_row(sheet_id, row_idx, n_cols, _C["month"], _C["white"], bold=True, size=10))
            requests.append(_fmt_numbers(sheet_id, row_idx, n_cols))
        elif rtype == "DATA_ODD":
            requests.append(_fmt_row(sheet_id, row_idx, n_cols, _C["data_odd"], _C["dark_text"], bold=False, size=9))
            requests.append(_fmt_numbers(sheet_id, row_idx, n_cols))
        elif rtype == "DATA_EVEN":
            requests.append(_fmt_row(sheet_id, row_idx, n_cols, _C["data_even"], _C["dark_text"], bold=False, size=9))
            requests.append(_fmt_numbers(sheet_id, row_idx, n_cols))
        elif rtype == "TOTAL":
            requests.append(_fmt_row(sheet_id, row_idx, n_cols, _C["total"], _C["white"], bold=True, size=10))
            requests.append(_fmt_numbers(sheet_id, row_idx, n_cols))

    return requests


def _grid_range(sheet_id: int, row: int, col_start: int = 0, col_end: int = 11) -> dict:
    return {
        "sheetId": sheet_id,
        "startRowIndex": row,
        "endRowIndex": row + 1,
        "startColumnIndex": col_start,
        "endColumnIndex": col_end,
    }


def _fmt_row(
    sheet_id: int, row: int, n_cols: int,
    bg: dict, fg: dict, bold: bool, size: int,
) -> dict:
    return {
        "repeatCell": {
            "range": _grid_range(sheet_id, row, 0, n_cols),
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": bg,
                    "textFormat": {"foregroundColor": fg, "bold": bold, "fontSize": size},
                    "verticalAlignment": "MIDDLE",
                    "padding": {"top": 3, "bottom": 3, "left": 6, "right": 4},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)",
        }
    }


def _fmt_numbers(sheet_id: int, row: int, n_cols: int) -> dict:
    """Числовые колонки: правое выравнивание + формат с пробелами."""
    return {
        "repeatCell": {
            "range": _grid_range(sheet_id, row, 2, n_cols),  # со столбца 2 (пропускаем label и тип)
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "RIGHT",
                    "numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"},
                }
            },
            "fields": "userEnteredFormat(horizontalAlignment,numberFormat)",
        }
    }
