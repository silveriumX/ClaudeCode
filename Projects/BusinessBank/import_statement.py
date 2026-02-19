#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Импорт банковской выписки в журнал операций.

Использование:
    python import_statement.py <путь_к_файлу> [--entity DBZ] [--out output.xlsx]

Примеры:
    python import_statement.py "Примеры выписок из Модульбанка/Statement 40802810570010435344 01.01.2025_18.02.2026.xlsx" --entity DBZ
    python import_statement.py statement.xlsx --entity MN --out journal_MN.xlsx
"""

import argparse
import io
import logging
import sys
from pathlib import Path

# Принудительно UTF-8 для вывода (Windows cp1251 не поддерживает emoji)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.parser import parse_statement
from src.classifier import TransactionClassifier
from src.categories import (
    TYPE_INCOME, TYPE_EXPENSE,
    TYPE_TRANSFER_INTERNAL, TYPE_TRANSFER_WITHDRAWAL,
    ALL_EXPENSE_CATEGORIES,
    CAT_INCOME_WB, CAT_INCOME_OZON, CAT_INCOME_OTHER,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_journal(df: pd.DataFrame, entity: str, owner_name: str = "") -> pd.DataFrame:
    """
    Добавляет результаты классификации к DataFrame выписки.
    Возвращает единый журнал операций (вертикальный формат).

    Args:
        owner_name: ФИО владельца р/с — нужно для распознавания переводов
                    на личные счета без пометки "перевод между счетами".
    """
    classifier = TransactionClassifier()
    results = [classifier.classify(row, owner_name=owner_name) for _, row in df.iterrows()]

    journal = df.copy()
    journal["entity"]     = entity
    journal["type"]       = [r["type"]       for r in results]
    journal["category"]   = [r["category"]   for r in results]
    journal["subcategory"] = [r["subcategory"] for r in results]
    journal["confidence"] = [r["confidence"] for r in results]
    journal["currency"]   = "RUB"
    journal["source"]     = "bank_statement"

    # Итоговые колонки журнала
    return journal[[
        "date", "entity", "type", "category", "subcategory",
        "amount", "currency",
        "counterparty", "purpose",
        "bank", "account",
        "doc_num", "confidence", "source",
    ]].rename(columns={
        "date":        "Дата",
        "entity":      "Юрлицо",
        "type":        "Тип",
        "category":    "Категория",
        "subcategory": "Подкатегория",
        "amount":      "Сумма",
        "currency":    "Валюта",
        "counterparty": "Контрагент",
        "purpose":     "Назначение платежа",
        "bank":        "Банк контрагента",
        "account":     "Счёт корреспондента",
        "doc_num":     "Номер документа",
        "confidence":  "Достоверность",
        "source":      "Источник",
    })


def build_pnl(journal: pd.DataFrame, entity: str) -> pd.DataFrame:
    """
    Строит отчёт P&L (только Доходы и Расходы, без Переводов).

    Структура: Год | Месяц | Категория | Сумма
    """
    # Только операции, влияющие на P&L
    pnl_df = journal[journal["Тип"].isin([TYPE_INCOME, TYPE_EXPENSE])].copy()
    pnl_df["Год"]   = pnl_df["Дата"].dt.year
    pnl_df["Месяц"] = pnl_df["Дата"].dt.month

    # Расходы — отрицательные для P&L
    pnl_df["Сумма_PnL"] = pnl_df.apply(
        lambda r: r["Сумма"] if r["Тип"] == TYPE_INCOME else -r["Сумма"],
        axis=1,
    )

    pivot = (
        pnl_df.groupby(["Год", "Месяц", "Категория"])["Сумма_PnL"]
        .sum()
        .reset_index()
        .rename(columns={"Сумма_PnL": "Сумма"})
        .sort_values(["Год", "Месяц", "Сумма"], ascending=[True, True, False])
    )
    return pivot


def build_monthly_summary(journal: pd.DataFrame) -> pd.DataFrame:
    """
    Месячная сводка: Доходы / Расходы / Переводы (вывод) / Чистая прибыль.
    """
    df = journal.copy()
    df["Год"]   = df["Дата"].dt.year
    df["Месяц"] = df["Дата"].dt.month

    rows = []
    for (year, month), grp in df.groupby(["Год", "Месяц"]):
        income    = grp[grp["Тип"] == TYPE_INCOME]["Сумма"].sum()
        expense   = grp[grp["Тип"] == TYPE_EXPENSE]["Сумма"].sum()
        w_draw    = grp[grp["Тип"] == TYPE_TRANSFER_WITHDRAWAL]["Сумма"].sum()
        internal  = grp[grp["Тип"] == TYPE_TRANSFER_INTERNAL]["Сумма"].sum()
        profit    = income - expense

        rows.append({
            "Год":               year,
            "Месяц":             month,
            "Доходы":            income,
            "Расходы":           expense,
            "Чистая прибыль":    profit,
            "Вывод на карты":    w_draw,
            "Внутренние переводы": internal,
            "Маржа %":           round(profit / income * 100, 1) if income > 0 else 0,
        })

    return pd.DataFrame(rows)


def build_manual_review(journal: pd.DataFrame) -> pd.DataFrame:
    """Операции, требующие ручной проверки категории."""
    return journal[journal["Достоверность"] == "manual"].copy()


def export_to_excel(
    journal: pd.DataFrame,
    pnl: pd.DataFrame,
    summary: pd.DataFrame,
    manual: pd.DataFrame,
    output_path: Path,
    entity: str,
) -> None:
    """Записывает все таблицы в один Excel файл."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="📊 Сводка по месяцам", index=False)
        pnl.to_excel(writer, sheet_name="💰 PnL", index=False)
        journal.to_excel(writer, sheet_name="📋 Журнал", index=False)
        manual.to_excel(writer, sheet_name="⚠️ Требуют проверки", index=False)

        # Авто-ширина колонок
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max(
                    len(str(cell.value or "")) for cell in col
                )
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    logger.info(f"Отчёт сохранён: {output_path}")


def print_summary(summary: pd.DataFrame, entity: str) -> None:
    """Выводит краткий P&L в консоль."""
    print(f"\n{'='*60}")
    print(f"  P&L / Сводка | Юрлицо: {entity}")
    print(f"{'='*60}")
    print(f"{'Период':<12} {'Доходы':>14} {'Расходы':>14} {'Прибыль':>14} {'Маржа':>8}")
    print(f"{'-'*60}")

    for _, row in summary.iterrows():
        period  = f"{int(row['Год'])}-{int(row['Месяц']):02d}"
        income  = f"{row['Доходы']:>14,.0f}"
        expense = f"{row['Расходы']:>14,.0f}"
        profit  = f"{row['Чистая прибыль']:>14,.0f}"
        margin  = f"{row['Маржа %']:>7.1f}%"
        print(f"{period:<12} {income} {expense} {profit} {margin}")

    print(f"{'-'*60}")
    totals = summary[["Доходы", "Расходы", "Чистая прибыль"]].sum()
    margin_total = (
        round(totals["Чистая прибыль"] / totals["Доходы"] * 100, 1)
        if totals["Доходы"] > 0 else 0
    )
    print(
        f"{'ИТОГО':<12} "
        f"{totals['Доходы']:>14,.0f} "
        f"{totals['Расходы']:>14,.0f} "
        f"{totals['Чистая прибыль']:>14,.0f} "
        f"{margin_total:>7.1f}%"
    )
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Импорт банковской выписки в журнал операций"
    )
    parser.add_argument("file", help="Путь к файлу выписки (.xlsx)")
    parser.add_argument(
        "--entity", default="UNKNOWN",
        help="Юрлицо: DBZ, MN, VAS, LYA, MAKS, LIFE, ALEX, HUB"
    )
    parser.add_argument(
        "--out", default=None,
        help="Путь для сохранения Excel-отчёта (по умолчанию: journal_<entity>.xlsx)"
    )
    parser.add_argument(
        "--owner", default="",
        help='ФИО владельца р/с для распознавания переводов (пример: "Пирожкова Наталья Викторовна")'
    )
    parser.add_argument(
        "--last-months", type=int, default=None,
        help="Показать только последние N месяцев"
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        logger.error(f"Файл не найден: {file_path}")
        sys.exit(1)

    output_path = Path(args.out) if args.out else Path(f"journal_{args.entity}.xlsx")

    # 1. Парсинг
    df = parse_statement(file_path)

    # 2. Фильтр по периоду (если задан)
    if args.last_months:
        cutoff = df["date"].max() - pd.DateOffset(months=args.last_months)
        df = df[df["date"] >= cutoff].copy()
        logger.info(f"Фильтр: последние {args.last_months} месяца(ев), с {cutoff.date()}")

    # 3. Классификация
    journal = build_journal(df, entity=args.entity, owner_name=args.owner)

    # 4. Отчёты
    pnl     = build_pnl(journal, entity=args.entity)
    summary = build_monthly_summary(journal)
    manual  = build_manual_review(journal)

    # 5. Вывод
    print_summary(summary, args.entity)

    if manual is not None and len(manual) > 0:
        print(f"⚠️  Требуют ручной проверки: {len(manual)} операций")
        for _, row in manual.iterrows():
            print(f"   {row['Дата'].date()} | {row['Сумма']:>10,.0f} | {row['Контрагент'][:40]}")

    export_to_excel(journal, pnl, summary, manual, output_path, args.entity)
    print(f"\n✅ Готово! Отчёт: {output_path.resolve()}")


if __name__ == "__main__":
    main()
