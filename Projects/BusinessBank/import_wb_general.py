#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_wb_general.py — Импорт общего списка финансовых отчётов WB.

Источник: «Фин.отчет общий.ДБЗ..xls» — все еженедельные отчёты за период,
с разбивкой по категориям (продажа, логистика, хранение, удержания, штрафы).

Как получить файл:
    WB Партнёр → Аналитика → Финансовые отчёты → кнопка «Список отчётов»

Использование:
    python -X utf8 import_wb_general.py "Финансовые отчеты/Фин.отчет общий.ДБЗ..xls"

    # Фильтр по году
    python -X utf8 import_wb_general.py file.xls --year 2025

    # Фильтр по периоду (YYYY-MM-DD)
    python -X utf8 import_wb_general.py file.xls --from 2025-01-01 --to 2025-12-31

    # Только основные отчёты (без выкупов)
    python -X utf8 import_wb_general.py file.xls --type Основной

    # Указать выходной файл
    python -X utf8 import_wb_general.py file.xls --out wb_pnl_2025.xlsx

Выходной Excel (3 листа):
    📊 P&L по месяцам   — сводка: продажи/логистика/хранение/удержания/итого
    📋 По неделям        — одна строка на отчёт (Основной)
    🛒 По выкупам        — недели из отчётов «По выкупам»
"""

import argparse
import io
import logging
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.wb_general_report import WbGeneralParser, SchemaError, FIN_COLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Excel-экспорт ────────────────────────────────────────────────────────────

def export_to_excel(
    monthly_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    buyout_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Сохранить все листы в Excel с форматированием."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        sheets = [
            ("📊 P&L по месяцам",  monthly_df),
            ("📋 По неделям",       weekly_df),
            ("🛒 По выкупам",       buyout_df),
        ]
        for sheet_name, data in sheets:
            if data.empty:
                pd.DataFrame({"(нет данных)": []}).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )
            else:
                data.to_excel(writer, sheet_name=sheet_name, index=False)

        for ws in writer.sheets.values():
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 55)

    logger.info("Отчёт сохранён: %s", output_path)


# ─── Консольная сводка ────────────────────────────────────────────────────────

def print_console_summary(monthly: pd.DataFrame, weekly: pd.DataFrame) -> None:
    """Вывести P&L сводку в консоль."""
    if monthly.empty:
        print("  (нет данных)")
        return

    sales_col   = FIN_COLS.get("gross_sales", "Продажа")
    payout_col  = FIN_COLS.get("payout", "К перечислению за товар")
    net_col     = FIN_COLS.get("net_payout", "Итого к оплате")
    logist_col  = FIN_COLS.get("logistics", "Стоимость логистики")

    print(f"\n{'='*78}")
    print(f"  WB — Общий список финансовых отчётов")
    print(f"{'='*78}")
    hdr = f"  {'Период':<20} {'Отч.':>5} {'Продажа':>14} {'К перечисл.':>14} {'Логистика':>12} {'Итого':>13}"
    print(hdr)
    print(f"  {'-'*76}")

    for _, row in monthly.iterrows():
        period = str(row.get("Период", ""))
        n      = str(row.get("Отчётов (шт.)", ""))
        sales  = row.get(sales_col, 0)
        payout = row.get(payout_col, 0)
        logist = row.get(logist_col, 0)
        net    = row.get(net_col, 0)

        is_total = str(row.get("Год", "")) == "ИТОГО"
        if is_total:
            print(f"  {'='*76}")

        try:
            print(
                f"  {period:<20} {n:>5}"
                f" {float(sales):>14,.0f}"
                f" {float(payout):>14,.0f}"
                f" {float(logist):>12,.0f}"
                f" {float(net):>13,.0f}"
            )
        except (TypeError, ValueError):
            pass

    print(f"{'='*78}")
    print(f"\nВсего еженедельных отчётов (Основной): {len(weekly)}")
    print()


# ─── Фильтрация по периоду ────────────────────────────────────────────────────

def filter_period(df: pd.DataFrame, year: int | None, from_date: str | None, to_date: str | None) -> pd.DataFrame:
    """Применить фильтры по дате к DataFrame."""
    if df.empty:
        return df

    if year is not None:
        df = df[df["Дата начала"].dt.year == year].copy()

    if from_date:
        df = df[df["Дата начала"] >= pd.Timestamp(from_date)].copy()

    if to_date:
        df = df[df["Дата конца"] <= pd.Timestamp(to_date)].copy()

    return df


# ─── Точка входа ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Импорт общего списка финансовых отчётов WB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file", help="XLS/XLSX файл общего списка отчётов WB")
    parser.add_argument(
        "--out", default="wb_general_report.xlsx",
        help="Выходной Excel-файл (default: wb_general_report.xlsx)",
    )
    parser.add_argument(
        "--type", choices=["Основной", "По выкупам"],
        default=None,
        help="Фильтр по типу отчёта (default: оба)",
    )
    parser.add_argument("--year", type=int, default=None, help="Фильтр по году")
    parser.add_argument("--from", dest="from_date", default=None, help="Дата от (YYYY-MM-DD)")
    parser.add_argument("--to",   dest="to_date",   default=None, help="Дата до (YYYY-MM-DD)")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        logger.error("Файл не найден: %s", file_path)
        sys.exit(1)

    wb_parser = WbGeneralParser()

    try:
        df_all = wb_parser.parse(file_path, report_type=None)
    except SchemaError as exc:
        logger.error("Не подходящий файл: %s", exc)
        sys.exit(1)

    if df_all.empty:
        logger.error("Нет данных в файле.")
        sys.exit(1)

    # Фильтрация по периоду
    df_all = filter_period(df_all, args.year, args.from_date, args.to_date)

    if df_all.empty:
        logger.error("После фильтрации не осталось данных.")
        sys.exit(1)

    # Разделение по типу
    df_main   = df_all[df_all["Тип отчета"] == "Основной"].copy()
    df_buyout = df_all[df_all["Тип отчета"] == "По выкупам"].copy()

    # Агрегация
    monthly_df = wb_parser.monthly_pnl(df_all, report_type="Основной")
    weekly_df  = wb_parser.weekly_table(df_all, report_type="Основной")
    buyout_df  = wb_parser.weekly_table(df_all, report_type="По выкупам")

    print_console_summary(monthly_df, df_main)

    output_path = Path(args.out)
    export_to_excel(monthly_df, weekly_df, buyout_df, output_path)
    print(f"✅ Готово! Отчёт: {output_path.resolve()}")


if __name__ == "__main__":
    main()
