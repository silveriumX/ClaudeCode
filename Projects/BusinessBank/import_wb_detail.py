#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_wb_detail.py — Импорт WB «Отчёт реализации» (детализированный).

Поддерживаемые форматы:
    Еженедельный детализированный (основной / по выкупам)  — 81 колонка
    Ежедневный детализированный   (основной / по выкупам)  — 79 колонок

Как получить отчёт из WB:
    WB Партнёр → Аналитика → Финансовые отчёты →
    «Отчёт реализации (еженедельный/ежедневный)» → Скачать

Использование:
    # Один файл
    python -X utf8 import_wb_detail.py "09.02.-15.02. осн. еженедельный дет..xlsx"

    # Несколько файлов
    python -X utf8 import_wb_detail.py file1.xlsx file2.xlsx

    # Целая папка
    python -X utf8 import_wb_detail.py --folder "Финансовые отчеты/"

    # Диагностика (проверить схему без обработки)
    python -X utf8 import_wb_detail.py file.xlsx --diagnose

    # Указать выходной файл
    python -X utf8 import_wb_detail.py --folder "Финансовые отчеты/" --out my_report.xlsx

Выходной Excel (3 листа):
    📊 Сводка P&L    — по файлам: суммы продаж, возвратов, комиссий, логистики
    📋 Детали        — все строки всех файлов (основной тип)
    🛒 По выкупам    — строки из файлов «по выкупам»
"""

import argparse
import glob
import io
import logging
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.wb_detail_report import (
    SchemaError,
    WbDetailParser,
    detect_report_type,
    summarize_by_period,
    validate_schema,
    _normalize_columns,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Диагностика ──────────────────────────────────────────────────────────────

def diagnose_file(file_path: Path) -> None:
    """Проверить схему файла и вывести информацию."""
    print(f"\n{'='*65}")
    print(f"  Файл: {file_path.name}")

    try:
        raw = pd.read_excel(file_path, sheet_name=0, header=0, nrows=3)
    except Exception as exc:
        print(f"  ✗ Не удалось прочитать: {exc}")
        return

    df = _normalize_columns(raw)
    freq, data_type = detect_report_type(file_path)
    print(f"  Частота:  {freq}")
    print(f"  Тип:      {data_type}")
    print(f"  Колонок:  {len(df.columns)}")

    try:
        validate_schema(df)
        print("  Схема:    ✓ OK")
    except SchemaError as exc:
        print(f"  Схема:    ✗ {exc}")

    print(f"\n  Первые 10 колонок:")
    for i, col in enumerate(list(df.columns)[:10]):
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else "(пусто)"
        print(f"    [{i:2d}] {col:<45} | {str(sample)[:30]}")
    print(f"{'='*65}")


# ─── Excel-экспорт ────────────────────────────────────────────────────────────

def export_to_excel(
    summary_df: pd.DataFrame,
    detail_df: pd.DataFrame,
    buyout_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Сохранить все листы в Excel с форматированием."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        sheets = [
            ("📊 Сводка P&L",  summary_df),
            ("📋 Детали",       detail_df),
            ("🛒 По выкупам",   buyout_df),
        ]
        for sheet_name, data in sheets:
            if data.empty:
                pd.DataFrame({"(нет данных)": []}).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )
            else:
                data.to_excel(writer, sheet_name=sheet_name, index=False)

        # Авто-ширина колонок
        for ws in writer.sheets.values():
            for col in ws.columns:
                max_len = max(
                    len(str(cell.value or "")) for cell in col
                )
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

    logger.info("Отчёт сохранён: %s", output_path)


# ─── Консольная сводка ────────────────────────────────────────────────────────

def print_console_summary(summaries: list[dict]) -> None:
    """Вывести сводку в консоль."""
    if not summaries:
        print("  (нет данных)")
        return

    print(f"\n{'='*75}")
    print(f"  WB Отчёт реализации — сводка")
    print(f"{'='*75}")
    print(f"  {'Файл':<40} {'Частота':<10} {'К перечисл.':>14} {'Продаж шт.':>10}")
    print(f"  {'-'*75}")

    total_payout = 0.0
    total_sales  = 0

    for s in summaries:
        name = str(s.get("file", ""))[:38]
        freq = s.get("freq", "")
        payout = s.get("net_payout", 0.0)
        n_sales = s.get("n_sales", 0)
        total_payout += payout
        total_sales  += n_sales
        print(f"  {name:<40} {freq:<10} {payout:>14,.2f} {n_sales:>10,}")

    print(f"  {'='*75}")
    print(f"  {'ИТОГО':<40} {'':<10} {total_payout:>14,.2f} {total_sales:>10,}")
    print(f"{'='*75}")

    # Детальная сводка по первому файлу
    if summaries:
        s = summaries[0]
        print(f"\nДетали ({s.get('file', '')}):")
        print(f"  Продажи (к перечислению):    {s.get('gross_sales', 0):>14,.2f}")
        print(f"  Возвраты (к перечислению):   {s.get('gross_returns', 0):>14,.2f}")
        print(f"  К перечислению ИТОГО:        {s.get('net_payout', 0):>14,.2f}")
        print(f"  Комиссия WB (gross):         {s.get('commission_gross', 0):>14,.2f}")
        print(f"  Логистика:                   {s.get('logistics', 0):>14,.2f}")
        print(f"  Хранение:                    {s.get('storage', 0):>14,.2f}")
        print(f"  Удержания:                   {s.get('holds', 0):>14,.2f}")
        print(f"  Эквайринг:                   {s.get('acquiring', 0):>14,.2f}")
    print()


# ─── Сбор файлов ──────────────────────────────────────────────────────────────

def collect_files(args: argparse.Namespace) -> list[Path]:
    """Собрать дедуплицированный список файлов."""
    paths: list[Path] = []

    if args.folder:
        folder = Path(args.folder)
        if not folder.is_dir():
            logger.error("Папка не найдена: %s", folder)
            sys.exit(1)
        for ext in ("*.xlsx",):
            paths.extend(sorted(folder.glob(ext)))

    for pattern in (args.files or []):
        matched = glob.glob(pattern)
        if matched:
            paths.extend(Path(p) for p in sorted(matched))
        else:
            p = Path(pattern)
            if p.exists():
                paths.append(p)
            else:
                logger.warning("Файл не найден: %s", pattern)

    # Дедупликация
    seen: set[Path] = set()
    result: list[Path] = []
    for p in paths:
        key = p.resolve()
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


# ─── Точка входа ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Импорт WB «Отчёт реализации» (детализированный)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("files", nargs="*", help="XLSX файлы отчёта")
    parser.add_argument("--folder", default=None, help="Папка — обработать все XLSX")
    parser.add_argument(
        "--out", default="wb_detail_report.xlsx",
        help="Выходной Excel-файл (default: wb_detail_report.xlsx)",
    )
    parser.add_argument(
        "--diagnose", action="store_true",
        help="Диагностика: проверить схему без обработки",
    )
    args = parser.parse_args()

    input_files = collect_files(args)
    if not input_files:
        logger.error("Не найдено ни одного файла. Укажите файлы или --folder.")
        sys.exit(1)

    if args.diagnose:
        for f in input_files:
            diagnose_file(f)
        return

    logger.info("Файлов для обработки: %d", len(input_files))

    detail_parser = WbDetailParser()
    summaries: list[dict] = []
    detail_rows: list[pd.DataFrame] = []
    buyout_rows: list[pd.DataFrame] = []

    for file_path in input_files:
        try:
            df = detail_parser.parse(file_path)
            if df.empty:
                logger.warning("Нет данных: %s", file_path.name)
                continue

            summary = detail_parser.summarize(df)
            summaries.append(summary)

            # Разделить основной / по выкупам
            if summary.get("data_type") == "по_выкупам":
                buyout_rows.append(df)
            else:
                detail_rows.append(df)

            logger.info(
                "  ✓ %s — %d строк, К перечислению: %.2f",
                file_path.name, len(df), summary.get("net_payout", 0),
            )
        except SchemaError as exc:
            logger.warning("  ✗ %s — не Отчёт реализации: %s", file_path.name, exc)
        except Exception as exc:
            logger.error("  ✗ %s: %s", file_path.name, exc, exc_info=True)

    if not summaries:
        logger.error("Ни один файл не обработан успешно.")
        sys.exit(1)

    summary_df = summarize_by_period(summaries)
    detail_df  = pd.concat(detail_rows,  ignore_index=True) if detail_rows  else pd.DataFrame()
    buyout_df  = pd.concat(buyout_rows,  ignore_index=True) if buyout_rows  else pd.DataFrame()

    print_console_summary(summaries)

    output_path = Path(args.out)
    export_to_excel(summary_df, detail_df, buyout_df, output_path)
    print(f"✅ Готово! Отчёт: {output_path.resolve()}")


if __name__ == "__main__":
    main()
