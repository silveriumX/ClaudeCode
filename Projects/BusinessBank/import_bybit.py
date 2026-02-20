#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_bybit.py — Импорт истории транзакций Bybit.

Как получить экспорт из Bybit:
    1. Зайди на bybit.com → Assets → Transaction History
    2. Нажми Export → выбери период → Download CSV
    Или для P2P:
    3. P2P → My Orders → Export

Использование:
    # Один файл
    python -X utf8 import_bybit.py bybit_history.csv

    # Несколько файлов / папка
    python -X utf8 import_bybit.py bybit_2024.csv bybit_2025.csv
    python -X utf8 import_bybit.py --folder "Bybit/"

    # Диагностика формата
    python -X utf8 import_bybit.py bybit_history.csv --diagnose

    # Только USDT операции
    python -X utf8 import_bybit.py bybit_history.csv --coin USDT

Выходной Excel (4 листа):
    📊 Сводка         — по месяцам: купил / продал / вывел USDT
    📋 Журнал         — все операции
    💸 Расходы USDT   — выводы с Bybit (карго, доставки, бизнес-платежи)
    📥 P2P покупки    — пополнения Bybit с личных карт
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

from src.bybit_adapter import (
    BYBIT_COLUMNS,
    TX_DEPOSIT,
    TX_P2P_BUY,
    TX_P2P_SELL,
    TX_WITHDRAW,
    BybitParser,
    classify_bybit_tx,
    _detect_format,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Константы ────────────────────────────────────────────────────────────────

TX_TYPE_LABELS = {
    "P2P_BUY":      "Покупка USDT (P2P)",
    "P2P_SELL":     "Продажа USDT (P2P)",
    "DEPOSIT":      "Пополнение (внешний)",
    "WITHDRAW":     "Вывод (бизнес-платёж)",
    "TRANSFER_IN":  "Перевод между субаккаунтами (+)",
    "TRANSFER_OUT": "Перевод между субаккаунтами (−)",
    "FEE":          "Комиссия биржи",
    "OTHER":        "Прочее",
}


# ─── Диагностика ──────────────────────────────────────────────────────────────

def diagnose_file(file_path: Path) -> None:
    """Выводит информацию о формате файла — для отладки."""
    parser = BybitParser()
    raw = parser._read_file(file_path)
    if raw is None:
        print(f"❌ Не удалось прочитать файл: {file_path}")
        return

    fmt = _detect_format(raw)
    print(f"\n{'='*60}")
    print(f"  Файл:    {file_path.name}")
    print(f"  Формат:  {fmt}")
    print(f"  Строк:   {len(raw)}")
    print(f"\n  Колонки:")
    for i, col in enumerate(raw.columns):
        sample = str(raw[col].dropna().iloc[0]) if not raw[col].dropna().empty else "(пусто)"
        print(f"    [{i:2d}] {col:<35} | Пример: {sample[:40]}")
    print(f"\n  Первые 3 строки:")
    print(raw.head(3).to_string())
    print(f"{'='*60}\n")


# ─── Построение таблиц ────────────────────────────────────────────────────────

def build_journal(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет колонки классификации к нормализованному DataFrame."""
    results = [classify_bybit_tx(row) for _, row in df.iterrows()]

    j = df.copy()
    j["Категория"]    = [r["category"]    for r in results]
    j["Подкатегория"] = [r["subcategory"] for r in results]
    j["Влияние P&L"]  = [r["pnl_sign"]   for r in results]
    j["Комментарий"]  = [r["comment"]     for r in results]

    return j[[
        "date", "tx_type", "coin", "amount", "amount_rub", "price_rub",
        "fee", "Категория", "Подкатегория", "Влияние P&L", "Комментарий",
        "status", "tx_id", "purpose",
    ]].rename(columns={
        "date":         "Дата",
        "tx_type":      "Тип",
        "coin":         "Монета",
        "amount":       "Сумма (монета)",
        "amount_rub":   "Сумма (RUB)",
        "price_rub":    "Курс USDT/RUB",
        "fee":          "Комиссия",
        "status":       "Статус",
        "tx_id":        "ID транзакции",
        "purpose":      "Описание",
    })


def build_monthly_summary(merged: pd.DataFrame) -> pd.DataFrame:
    """Сводка по месяцам: покупка / продажа / вывод USDT.

    Принимает сырой DataFrame из BybitParser (колонки: date, tx_type, amount, amount_rub).
    """
    if merged.empty:
        return pd.DataFrame()

    df = merged.copy()
    df["_year"]  = pd.to_datetime(df["date"]).dt.year
    df["_month"] = pd.to_datetime(df["date"]).dt.month

    rows = []
    for (year, month), grp in df.groupby(["_year", "_month"]):
        def _sum_type(type_key: str) -> float:
            mask = grp["tx_type"] == type_key
            return abs(grp[mask]["amount"].sum())

        bought    = _sum_type(TX_P2P_BUY)
        sold      = _sum_type(TX_P2P_SELL)
        deposited = _sum_type(TX_DEPOSIT)
        withdrawn = _sum_type(TX_WITHDRAW)

        # Сумма RUB потраченная на покупку USDT
        rub_spent = abs(grp[grp["tx_type"] == TX_P2P_BUY]["amount_rub"].sum())
        avg_rate  = rub_spent / bought if bought > 0 else 0.0

        rows.append({
            "Год":              int(year),
            "Месяц":            int(month),
            "Куплено USDT":     round(bought, 2),
            "Потрачено RUB":    round(rub_spent, 2),
            "Ср. курс USDT/RUB": round(avg_rate, 2),
            "Продано USDT":     round(sold, 2),
            "Выведено USDT":    round(withdrawn, 2),
            "Пополнено (внешнее)": round(deposited, 2),
            "Кол-во операций":  len(grp),
        })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).sort_values(["Год", "Месяц"])
    # Итого
    totals = {
        "Год": "ИТОГО",
        "Месяц": "",
        "Куплено USDT":       result["Куплено USDT"].sum(),
        "Потрачено RUB":      result["Потрачено RUB"].sum(),
        "Ср. курс USDT/RUB":  result["Потрачено RUB"].sum() / result["Куплено USDT"].sum()
                              if result["Куплено USDT"].sum() > 0 else 0,
        "Продано USDT":       result["Продано USDT"].sum(),
        "Выведено USDT":      result["Выведено USDT"].sum(),
        "Пополнено (внешнее)": result["Пополнено (внешнее)"].sum(),
        "Кол-во операций":    result["Кол-во операций"].sum(),
    }
    return pd.concat([result, pd.DataFrame([totals])], ignore_index=True)


def build_withdrawals(journal: pd.DataFrame) -> pd.DataFrame:
    """Выводы с Bybit — бизнес-платежи (карго, доставки, агенты)."""
    mask = journal["Тип"] == TX_WITHDRAW
    if not mask.any():
        return pd.DataFrame()
    return (
        journal[mask]
        .sort_values("Дата")
        .reset_index(drop=True)
    )


def build_p2p_buys(journal: pd.DataFrame) -> pd.DataFrame:
    """P2P покупки USDT с личных карт."""
    mask = journal["Тип"] == TX_P2P_BUY
    if not mask.any():
        return pd.DataFrame()
    return (
        journal[mask]
        .sort_values("Дата")
        .reset_index(drop=True)
    )


def export_to_excel(
    journal: pd.DataFrame,
    summary: pd.DataFrame,
    withdrawals: pd.DataFrame,
    p2p_buys: pd.DataFrame,
    output_path: Path,
) -> None:
    """Записывает все таблицы в Excel с автошириной колонок."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, data in [
            ("📊 Сводка",        summary),
            ("📋 Журнал",        journal),
            ("💸 Расходы USDT",  withdrawals),
            ("📥 P2P покупки",   p2p_buys),
        ]:
            if data.empty:
                pd.DataFrame({"(нет данных)": []}).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )
            else:
                data.to_excel(writer, sheet_name=sheet_name, index=False)

        # Авто-ширина колонок
        for ws in writer.sheets.values():
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 55)

    logger.info("Отчёт сохранён: %s", output_path)


def print_console_summary(summary: pd.DataFrame, journal: pd.DataFrame) -> None:
    """Выводит сводку в консоль."""
    if summary.empty:
        print("  (нет данных)")
        return

    totals = summary[summary["Год"] == "ИТОГО"].iloc[0] if "ИТОГО" in summary["Год"].values else None

    print(f"\n{'='*68}")
    print(f"  Bybit — история транзакций")
    print(f"{'='*68}")
    print(f"  {'Год':<6}{'Месяц':<8}{'Куплено USDT':>14}{'RUB':>14}{'Курс':>8}{'Выведено':>12}")
    print(f"{'-'*68}")

    for _, row in summary.iterrows():
        if row["Год"] == "ИТОГО":
            print(f"{'='*68}")
        year  = str(int(row["Год"])) if row["Год"] != "ИТОГО" else "ИТОГО"
        month = f"{int(row['Месяц']):02d}" if row["Месяц"] != "" else ""
        print(
            f"  {year:<6}{month:<8}"
            f"{row['Куплено USDT']:>14,.2f}"
            f"{row['Потрачено RUB']:>14,.0f}"
            f"{row['Ср. курс USDT/RUB']:>8,.1f}"
            f"{row['Выведено USDT']:>12,.2f}"
        )

    print(f"{'='*68}")
    print(f"\nВсего операций: {len(journal)}")

    # Статистика по типам
    by_type = journal.groupby("Тип")["Сумма (монета)"].agg(["count", "sum"])
    print("\nПо типам:")
    for tx_type, row in by_type.iterrows():
        label = TX_TYPE_LABELS.get(tx_type, tx_type)
        sign  = "+" if row["sum"] > 0 else ""
        print(f"  {label:<38} {int(row['count']):>4} шт.  {sign}{row['sum']:>10,.2f} USDT")
    print()


# ─── Сбор файлов ──────────────────────────────────────────────────────────────

def collect_files(args: argparse.Namespace) -> list[Path]:
    """Возвращает дедуплицированный список файлов для обработки."""
    paths: list[Path] = []

    if args.folder:
        folder = Path(args.folder)
        if not folder.is_dir():
            logger.error("Папка не найдена: %s", folder)
            sys.exit(1)
        for ext in ("*.csv", "*.xlsx"):
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

    # Дедупликация с сохранением порядка
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
        description="Импорт истории транзакций Bybit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "files", nargs="*",
        help="CSV/XLSX файлы Bybit (можно несколько)",
    )
    parser.add_argument(
        "--folder", default=None,
        help="Папка — обработать все CSV/XLSX внутри",
    )
    parser.add_argument(
        "--out", default="bybit_journal.xlsx",
        help="Имя выходного Excel-файла (default: bybit_journal.xlsx)",
    )
    parser.add_argument(
        "--coin", default=None,
        help="Фильтр по монете, например: USDT (default: все)",
    )
    parser.add_argument(
        "--diagnose", action="store_true",
        help="Диагностический режим: показать формат файла без парсинга",
    )
    args = parser.parse_args()

    input_files = collect_files(args)
    if not input_files:
        logger.error("Не найдено ни одного файла. Укажите файлы или --folder.")
        sys.exit(1)

    # Режим диагностики
    if args.diagnose:
        for f in input_files:
            diagnose_file(f)
        return

    logger.info("Файлов для обработки: %d", len(input_files))
    bybit_parser = BybitParser()
    all_dfs: list[pd.DataFrame] = []

    for file_path in input_files:
        try:
            df = bybit_parser.parse(file_path)
            if df.empty:
                logger.warning("Нет данных: %s", file_path.name)
                continue
            all_dfs.append(df)
            logger.info("  ✓ %s — %d операций", file_path.name, len(df))
        except Exception as exc:
            logger.error("  ✗ %s: %s", file_path.name, exc, exc_info=True)

    if not all_dfs:
        logger.error("Ни один файл не обработан успешно.")
        sys.exit(1)

    merged = (
        pd.concat(all_dfs, ignore_index=True)
        .sort_values("date")
        .reset_index(drop=True)
    )

    # Фильтр по монете
    if args.coin:
        before = len(merged)
        merged = merged[merged["coin"].str.upper() == args.coin.upper()].copy()
        logger.info("Фильтр %s: %d → %d строк", args.coin, before, len(merged))

    journal    = build_journal(merged)
    summary    = build_monthly_summary(merged)
    withdrawals = build_withdrawals(journal)
    p2p_buys   = build_p2p_buys(journal)

    print_console_summary(summary, journal)
    print(f"Выводов с Bybit (расходы):  {len(withdrawals)}")
    print(f"P2P покупок USDT:           {len(p2p_buys)}")

    output_path = Path(args.out)
    export_to_excel(journal, summary, withdrawals, p2p_buys, output_path)
    print(f"\n✅ Готово! Отчёт: {output_path.resolve()}")


if __name__ == "__main__":
    main()
