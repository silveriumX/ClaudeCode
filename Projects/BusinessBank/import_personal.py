#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Импорт PDF выписок личных счетов физлиц.

Поддерживаемые банки: АльфаБанк, ВТБ, Сбербанк, Т-Банк.

Использование:
    # Один файл
    python -X utf8 import_personal.py "Выписки с счетов физлица/Альфа.pdf"

    # Несколько файлов
    python -X utf8 import_personal.py "Выписки с счетов физлица/Альфа.pdf" "Выписки с счетов физлица/ВТБ.pdf"

    # Папка целиком
    python -X utf8 import_personal.py --folder "Выписки с счетов физлица/" --out personal_all.xlsx

    # Указать банк явно (если автоопределение не работает)
    python -X utf8 import_personal.py "Альфа.pdf" --bank alfa

Выходной Excel (4 листа):
    📊 Сводка          — по банкам и месяцам (приход/расход)
    📋 Журнал          — все операции из всех PDF
    🔍 Ручная проверка — операции с confidence='manual'
    📈 Крупные суммы   — операции > 50 000 руб.
"""

import argparse
import glob
import io
import logging
import re
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.personal_parsers import detect_pdf_bank, parse_personal_pdf, PDF_PARSERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Константы ────────────────────────────────────────────────────────────────

BANK_NAMES = {
    "alfa":  "АльфаБанк",
    "vtb":   "ВТБ",
    "sber":  "Сбербанк",
    "tbank": "Т-Банк",
}

# ─── Классификатор операций личного счёта ─────────────────────────────────────

_MODULBANK_RE = re.compile(r"Модульбанк|Московский Филиал АО КБ", re.IGNORECASE)
_INTERNAL_RE  = re.compile(
    r"собственных средств|внутрибанковск|внутренний перевод|перевод между счет",
    re.IGNORECASE,
)
_OWNER_RE     = re.compile(r"Пирожков", re.IGNORECASE)
_P2P_RE       = re.compile(r"p2p|bybit|binance|htx|okx|bitpapa|usdt|btc|крипт|биткойн|токен", re.IGNORECASE)
_ATM_RE       = re.compile(r"выдача наличных|снятие|банкомат|\bATM\b", re.IGNORECASE)
_BANK_FEE_RE  = re.compile(r"комиссия|пакет услуг|обслуживание счёт|подписка ВТБ|ВТБ Плюс", re.IGNORECASE)


def _classify_personal(row: pd.Series) -> dict:
    """
    Упрощённая классификация операции личного счёта.

    Ключевые типы:
      Перевод из бизнеса — поступление с р/с МодульБанка
      Внутренний перевод — между своими счетами (собственных средств)
      P2P (крипта)       — ВАЖНО: не расход (см. HANDOFF.md §Правила)
      Снятие наличных    — банкомат
      Банковская комиссия
      Доход / Расход     — прочее (manual)
    """
    purpose   = str(row.get("purpose", ""))
    cp        = str(row.get("counterparty", ""))
    full      = purpose + " " + cp
    is_income = bool(row.get("is_income", False))

    # Поступление с бизнес р/с МодульБанка
    if is_income and _MODULBANK_RE.search(full):
        return {"type": "Перевод из бизнеса", "category": "Поступление с р/с", "confidence": "auto"}

    # Внутренние переводы (собственные средства / между своими счетами)
    if _INTERNAL_RE.search(full):
        return {"type": "Внутренний перевод", "category": "Между своими счетами", "confidence": "auto"}

    # Перевод самой себе (контрагент = владелец)
    if _OWNER_RE.search(cp):
        return {"type": "Внутренний перевод", "category": "Между своими счетами", "confidence": "auto"}

    # P2P / крипта — НЕ расход! (фактический расход уже в FinanceBot)
    if _P2P_RE.search(full):
        return {"type": "P2P (крипта)", "category": "Покупка USDT", "confidence": "auto"}

    # Снятие наличных
    if _ATM_RE.search(full):
        return {"type": "Снятие наличных", "category": "Наличные", "confidence": "auto"}

    # Банковские комиссии
    if _BANK_FEE_RE.search(full):
        return {"type": "Расход", "category": "Банковские комиссии", "confidence": "auto"}

    # Прочий доход
    if is_income:
        return {"type": "Доход", "category": "Прочее", "confidence": "manual"}

    # Прочий расход
    return {"type": "Расход", "category": "Прочее", "confidence": "manual"}


# ─── Построение таблиц ────────────────────────────────────────────────────────

def build_journal(df: pd.DataFrame, bank_name: str) -> pd.DataFrame:
    """Добавляет колонки банка и классификации к нормализованному DataFrame."""
    results = [_classify_personal(row) for _, row in df.iterrows()]
    j = df.copy()
    j["_банк"]          = bank_name
    j["_тип"]           = [r["type"]       for r in results]
    j["_категория"]     = [r["category"]   for r in results]
    j["_достоверность"] = [r["confidence"] for r in results]

    return j[[
        "date", "_банк", "_тип", "_категория",
        "amount_in", "amount_out", "amount",
        "counterparty", "purpose", "doc_num", "_достоверность",
    ]].rename(columns={
        "date":           "Дата",
        "_банк":          "Банк",
        "_тип":           "Тип",
        "_категория":     "Категория",
        "amount_in":      "Приход",
        "amount_out":     "Расход",
        "amount":         "Сумма",
        "counterparty":   "Контрагент",
        "purpose":        "Назначение",
        "doc_num":        "Номер документа",
        "_достоверность": "Достоверность",
    })


def build_monthly_summary(journal: pd.DataFrame) -> pd.DataFrame:
    """Сводка: по банкам и месяцам — приход / расход / внутренние."""
    df = journal.copy()
    df["Год"]   = df["Дата"].dt.year
    df["Месяц"] = df["Дата"].dt.month

    rows = []
    for (bank, year, month), grp in df.groupby(["Банк", "Год", "Месяц"]):
        income   = grp[grp["Тип"].str.contains("Перевод из бизнеса|Доход", na=False, regex=True)]["Сумма"].sum()
        expense  = grp[grp["Тип"].str.contains("Расход|Снятие наличных", na=False, regex=True)]["Сумма"].sum()
        internal = grp[grp["Тип"].str.contains("Внутренний|P2P", na=False, regex=True)]["Сумма"].sum()
        rows.append({
            "Банк":              bank,
            "Год":               int(year),
            "Месяц":             int(month),
            "Приход":            round(income, 2),
            "Расход":            round(expense, 2),
            "Внутренние / P2P":  round(internal, 2),
            "Кол-во операций":   len(grp),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["Банк", "Год", "Месяц"])


def build_large_transactions(journal: pd.DataFrame, threshold: float = 50_000) -> pd.DataFrame:
    """Операции ≥ threshold руб. — нуждаются в ручной проверке."""
    return (
        journal[journal["Сумма"] >= threshold]
        .sort_values("Сумма", ascending=False)
        .reset_index(drop=True)
    )


def export_to_excel(
    journal: pd.DataFrame,
    summary: pd.DataFrame,
    large: pd.DataFrame,
    output_path: Path,
) -> None:
    """Записывает все таблицы в Excel с автошириной колонок."""
    manual = journal[journal["Достоверность"] == "manual"].copy()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, data in [
            ("📊 Сводка",           summary),
            ("📋 Журнал",           journal),
            ("🔍 Ручная проверка",  manual),
            ("📈 Крупные суммы",    large),
        ]:
            data.to_excel(writer, sheet_name=sheet_name, index=False)

        # Авто-ширина колонок
        for ws in writer.sheets.values():
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

    logger.info(f"Отчёт сохранён: {output_path}")


def print_console_summary(summary: pd.DataFrame) -> None:
    """Выводит сводку в консоль."""
    if summary.empty:
        print("  (нет данных)")
        return
    print(f"\n{'='*74}")
    print(f"  Сводка по личным счетам")
    print(f"{'='*74}")
    print(f"{'Банк':<12} {'Период':<10} {'Приход':>14} {'Расход':>14} {'Внутр./P2P':>12}")
    print(f"{'-'*74}")
    for _, row in summary.iterrows():
        period = f"{row['Год']}-{row['Месяц']:02d}"
        print(
            f"{row['Банк']:<12} {period:<10} "
            f"{row['Приход']:>14,.0f} "
            f"{row['Расход']:>14,.0f} "
            f"{row['Внутренние / P2P']:>12,.0f}"
        )
    totals = summary[["Приход", "Расход", "Внутренние / P2P"]].sum()
    print(f"{'='*74}")
    print(
        f"{'ИТОГО':<23} "
        f"{totals['Приход']:>14,.0f} "
        f"{totals['Расход']:>14,.0f} "
        f"{totals['Внутренние / P2P']:>12,.0f}"
    )
    print(f"{'='*74}\n")


# ─── Сбор файлов ──────────────────────────────────────────────────────────────

def collect_pdf_files(args: argparse.Namespace) -> list[Path]:
    """Возвращает дедуплицированный список PDF для обработки."""
    paths: list[Path] = []

    if args.folder:
        folder = Path(args.folder)
        if not folder.is_dir():
            logger.error(f"Папка не найдена: {folder}")
            sys.exit(1)
        paths.extend(sorted(folder.glob("*.pdf")))

    for pattern in (args.files or []):
        matched = glob.glob(pattern)
        if matched:
            paths.extend(Path(p) for p in sorted(matched))
        else:
            p = Path(pattern)
            if p.exists():
                paths.append(p)
            else:
                logger.warning(f"Файл не найден: {pattern}")

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
        description="Импорт PDF выписок личных счетов (Альфа, ВТБ, Сбер, Т-Банк)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "files", nargs="*",
        help="PDF-файлы (можно несколько, поддерживаются wildcards)",
    )
    parser.add_argument(
        "--folder", default=None,
        help="Папка — обработать все PDF внутри",
    )
    parser.add_argument(
        "--bank", default="auto",
        choices=["auto"] + list(PDF_PARSERS),
        help="Принудительно задать банк (default: auto)",
    )
    parser.add_argument(
        "--out", default="personal_journal.xlsx",
        help="Имя выходного Excel-файла (default: personal_journal.xlsx)",
    )
    parser.add_argument(
        "--large-threshold", type=float, default=50_000,
        help="Порог крупных операций в руб. (default: 50000)",
    )
    args = parser.parse_args()

    pdf_files = collect_pdf_files(args)
    if not pdf_files:
        logger.error("Не найдено ни одного PDF. Укажите файлы или --folder.")
        sys.exit(1)

    logger.info(f"Файлов для обработки: {len(pdf_files)}")
    all_journals: list[pd.DataFrame] = []

    for pdf_path in pdf_files:
        try:
            bank_key  = args.bank if args.bank != "auto" else detect_pdf_bank(pdf_path)
            bank_name = BANK_NAMES.get(bank_key, bank_key.upper())
            logger.info(f"  → {pdf_path.name} [{bank_name}]")

            df = parse_personal_pdf(pdf_path, bank=bank_key)
            if df.empty:
                logger.warning(f"    ⚠ Нет данных: {pdf_path.name}")
                continue

            journal = build_journal(df, bank_name)
            all_journals.append(journal)
            logger.info(f"    ✓ {len(df)} операций")

        except Exception as exc:
            logger.error(f"  ✗ {pdf_path.name}: {exc}", exc_info=True)

    if not all_journals:
        logger.error("Ни один файл не обработан успешно.")
        sys.exit(1)

    merged = (
        pd.concat(all_journals, ignore_index=True)
        .sort_values("Дата")
        .reset_index(drop=True)
    )

    summary = build_monthly_summary(merged)
    large   = build_large_transactions(merged, args.large_threshold)
    manual  = merged[merged["Достоверность"] == "manual"]

    print_console_summary(summary)
    print(f"Всего операций:       {len(merged)}")
    print(f"Требуют проверки:     {len(manual)}")
    print(f"Крупные (≥{args.large_threshold:,.0f} руб.): {len(large)}")

    output_path = Path(args.out)
    export_to_excel(merged, summary, large, output_path)
    print(f"\n✅ Готово! Отчёт: {output_path.resolve()}")


if __name__ == "__main__":
    main()
