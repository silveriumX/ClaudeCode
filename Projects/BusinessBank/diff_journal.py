#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сверка горизонтального журнала операций с банковской выпиской.

Логика:
  - Берём только пересечение: с первой даты в журнале
  - Сопоставляем по (дата, сумма ± 1 руб) в колонке МодульБанк р/с
  - Выводим: что совпало / чего нет в журнале / что только в журнале

Использование:
    python -X utf8 diff_journal.py \
        --bank "Примеры выписок из Модульбанка/Statement ...xlsx" \
        --journal "../../Финансовая система/Журнал операций ДБЗ .xlsx" \
        --entity DBZ \
        --owner "Пирожкова Наталья Викторовна" \
        --out diff_DBZ.xlsx
"""

import argparse
import io
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from src.classifier import TransactionClassifier
from src.parser import parse_statement

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TOLERANCE = 1.0  # рублей — допуск при сравнении сумм


# ── 1. ЧТЕНИЕ ЖУРНАЛА ─────────────────────────────────────────────────────────

def read_journal_modulbank(journal_path: Path) -> pd.DataFrame:
    """
    Читает горизонтальный журнал (экспорт Google Sheets).
    Возвращает вертикальный DataFrame только для колонки МодульБанк р/с:
        date (date) | amount (float, + приход / − расход) | comment (str)

    Структура файла:
        Строка 0 — сводка текущих остатков (пропускаем)
        Строка 1 — заголовки колонок  ← header
        Строка 2 — строка открытия (Текущий баланс на ...)
        Строки 3+ — транзакции
    """
    df_raw = pd.read_excel(journal_path, header=1)  # строка 1 = заголовок

    # Ищем нужные колонки по имени (с fallback на позицию)
    date_col = _find_col(df_raw, ["дата", "date"], fallback=0)
    mb_col   = _find_col(df_raw, ["модульбанк р/с", "модульбанк р/с", "р/с"], fallback=1)

    # Комментарий = следующая колонка после МодульБанк
    comment_col = mb_col + 1 if mb_col + 1 < len(df_raw.columns) else None

    logger.info(
        f"Журнал: Дата=col[{date_col}], МодульБанк=col[{mb_col}], "
        f"Комментарий=col[{comment_col}]"
    )

    records = []
    for _, row in df_raw.iterrows():
        raw_date   = row.iloc[date_col]
        raw_amount = row.iloc[mb_col]
        raw_comment = row.iloc[comment_col] if comment_col is not None else ""

        # Пропускаем строки без даты или суммы
        if pd.isna(raw_date) or pd.isna(raw_amount):
            continue

        # Пропускаем служебные строки (баланс, шапки)
        comment_str = str(raw_comment).strip()
        if any(kw in comment_str.lower() for kw in ["баланс", "текущий", "остаток", "итого"]):
            continue

        try:
            dt = pd.to_datetime(raw_date, dayfirst=True).date()
        except Exception:
            continue

        try:
            amount = float(raw_amount)
        except (ValueError, TypeError):
            continue

        if amount == 0:
            continue

        records.append({"date": dt, "amount": amount, "comment": comment_str})

    result = pd.DataFrame(records)
    logger.info(f"Журнал: {len(result)} строк по МодульБанк р/с (период: {result['date'].min()} → {result['date'].max()})")
    return result


def _find_col(df: pd.DataFrame, keywords: list[str], fallback: int) -> int:
    """Ищет колонку по ключевым словам в имени, возвращает индекс."""
    for i, col in enumerate(df.columns):
        col_l = str(col).lower().strip()
        if any(kw in col_l for kw in keywords):
            return i
    return fallback


# ── 2. ЧТЕНИЕ БАНКОВСКОЙ ВЫПИСКИ ──────────────────────────────────────────────

def read_bank_modulbank(bank_path: Path, owner_name: str = "") -> pd.DataFrame:
    """
    Парсит XLSX-выписку Модульбанка.
    Возвращает вертикальный DataFrame:
        date | amount (+ приход / − расход) | counterparty | purpose | type | category | subcategory
    """
    raw = parse_statement(bank_path)
    classifier = TransactionClassifier()

    records = []
    for _, row in raw.iterrows():
        cls = classifier.classify(row, owner_name=owner_name)
        signed = row["amount_in"] if row["is_income"] else -row["amount_out"]

        records.append(
            {
                "date":        row["date"].date(),
                "amount":      signed,
                "counterparty": row["counterparty"],
                "purpose":     row["purpose"],
                "type":        cls["type"],
                "category":    cls["category"],
                "subcategory": cls["subcategory"],
            }
        )

    result = pd.DataFrame(records)
    logger.info(f"Банк: {len(result)} транзакций (период: {result['date'].min()} → {result['date'].max()})")
    return result


# ── 3. СОПОСТАВЛЕНИЕ ──────────────────────────────────────────────────────────

def match(
    journal: pd.DataFrame,
    bank: pd.DataFrame,
    start_date: date,
    tolerance: float = TOLERANCE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Сопоставляет транзакции банка и журнала за период [start_date, ∞).

    Правило матча: date совпадает И abs(bank.amount − journal.amount) ≤ tolerance.

    Returns:
        matched       — есть в обоих
        missing       — есть в банке, нет в журнале → нужно добавить
        journal_only  — есть в журнале, нет в банке → ручные записи / другой банк
    """
    bank_p    = bank[bank["date"] >= start_date].copy().reset_index(drop=True)
    journal_p = journal[journal["date"] >= start_date].copy().reset_index(drop=True)

    logger.info(
        f"Сверка с {start_date}: банк={len(bank_p)}, журнал={len(journal_p)}"
    )

    # Множество ещё не сопоставленных индексов журнала
    free_j = set(journal_p.index.tolist())

    matched_rows  = []
    missing_rows  = []

    for _, b in bank_p.iterrows():
        # Ищем кандидатов в журнале: та же дата + сумма ± tolerance
        candidates = journal_p[
            (journal_p.index.isin(free_j))
            & (journal_p["date"] == b["date"])
            & (abs(journal_p["amount"] - b["amount"]) <= tolerance)
        ]

        if not candidates.empty:
            j_idx = candidates.index[0]
            free_j.discard(j_idx)
            j = journal_p.loc[j_idx]

            matched_rows.append(
                {
                    "Дата":              b["date"],
                    "Сумма":             b["amount"],
                    "Тип":               b["type"],
                    "Категория":         b["category"],
                    "Контрагент (банк)": b["counterparty"],
                    "Назначение (банк)": str(b["purpose"])[:80],
                    "Комментарий (журнал)": j["comment"],
                }
            )
        else:
            missing_rows.append(
                {
                    "Дата":                    b["date"],
                    "Сумма":                   b["amount"],
                    "Тип":                     b["type"],
                    "Категория":               b["category"],
                    "Подкатегория":            b["subcategory"],
                    "Контрагент":              b["counterparty"],
                    "Назначение платежа":      str(b["purpose"])[:120],
                    "Предлагаемый комментарий": _suggest_comment(b),
                }
            )

    journal_only_rows = [
        {
            "Дата":    journal_p.loc[i, "date"],
            "Сумма":   journal_p.loc[i, "amount"],
            "Комментарий": journal_p.loc[i, "comment"],
            "Примечание": "Нет в банковской выписке — ручная запись или другой банк",
        }
        for i in free_j
    ]

    return (
        pd.DataFrame(matched_rows),
        pd.DataFrame(missing_rows),
        pd.DataFrame(sorted(journal_only_rows, key=lambda r: r["Дата"])),
    )


def _suggest_comment(b: pd.Series) -> str:
    """Формирует предлагаемый комментарий для журнала на основе данных банка."""
    cp = str(b.get("counterparty", ""))[:45]
    cat = b.get("category", "")
    purpose = str(b.get("purpose", ""))

    templates = {
        "Доход — Wildberries":       f"WB — {cp}",
        "Доход — Ozon":              f"Ozon — {cp}",
        "Налоги и сборы":            f"{b.get('subcategory', 'Налог')} — {purpose[:50]}",
        "Банковские расходы":        f"Комиссия — {purpose[:50]}",
        "Фулфилмент":                f"Фулфилмент — {cp}",
        "IT и сервисы":              f"IT — {cp}",
        "Зарплата":                  f"Зарплата — {cp}",
        "Сертификация":              f"Сертификация — {cp}",
        "Перевод (внутренний)":      f"Перевод р/с → МК — {purpose[:40]}",
        "Перевод (вывод на карту)":  f"Вывод → {b.get('subcategory', cp)}",
        "Закупка товара":            f"Товар — {cp}",
    }
    return templates.get(cat, f"{cp} — {purpose[:40]}")


# ── 4. ЭКСПОРТ ────────────────────────────────────────────────────────────────

def export(
    matched: pd.DataFrame,
    missing: pd.DataFrame,
    journal_only: pd.DataFrame,
    out_path: Path,
    entity: str,
    start_date: date,
) -> None:
    total_bank = len(matched) + len(missing)
    coverage_pct = (len(matched) / total_bank * 100) if total_bank else 0

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        # Лист 0 — Итоговая сводка
        summary = pd.DataFrame(
            {
                "Показатель": [
                    "Юрлицо",
                    "Период сверки (начало)",
                    "Операций в банке (за период)",
                    "✅ Найдено в журнале",
                    "❌ Отсутствует в журнале",
                    "⚠️  Только в журнале (ручной ввод)",
                    "Покрытие журнала",
                    "",
                    "Сумма отсутствующих (без переводов)",
                ],
                "Значение": [
                    entity,
                    str(start_date),
                    total_bank,
                    len(matched),
                    len(missing),
                    len(journal_only),
                    f"{coverage_pct:.1f}%",
                    "",
                    _missing_pnl_sum(missing),
                ],
            }
        )
        summary.to_excel(writer, sheet_name="📊 Сводка", index=False)

        # Лист 1 — Главное: чего нет в журнале
        if not missing.empty:
            missing.sort_values("Дата").to_excel(
                writer, sheet_name="❌ Нет в журнале", index=False
            )

        # Лист 2 — Совпадения
        if not matched.empty:
            matched.sort_values("Дата").to_excel(
                writer, sheet_name="✅ Совпадают", index=False
            )

        # Лист 3 — Только в журнале
        if not journal_only.empty:
            pd.DataFrame(journal_only).sort_values("Дата").to_excel(
                writer, sheet_name="⚠️ Только в журнале", index=False
            )

        # Авто-ширина колонок
        for ws in writer.sheets.values():
            for col in ws.columns:
                w = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(w + 2, 55)

    logger.info(f"Отчёт сохранён: {out_path}")


def _missing_pnl_sum(missing: pd.DataFrame) -> str:
    """Сумма отсутствующих операций, влияющих на P&L (без внутренних переводов)."""
    if missing.empty:
        return "0"
    pnl = missing[~missing["Тип"].str.startswith("Перевод", na=False)]
    total = pnl["Сумма"].sum()
    return f"{total:,.0f} руб."


# ── 5. MAIN ───────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Сверка журнала с банковской выпиской")
    p.add_argument("--bank",    required=True, help="Путь к XLSX-выписке банка")
    p.add_argument("--journal", required=True, help="Путь к XLSX-журналу операций")
    p.add_argument("--entity",  default="UNKNOWN")
    p.add_argument("--owner",   default="", help='ФИО владельца р/с (для определения переводов)')
    p.add_argument("--out",     default=None)
    args = p.parse_args()

    bank_path    = Path(args.bank)
    journal_path = Path(args.journal)
    out_path     = Path(args.out) if args.out else Path(f"diff_{args.entity}.xlsx")

    for f in [bank_path, journal_path]:
        if not f.exists():
            logger.error(f"Файл не найден: {f}")
            sys.exit(1)

    # Читаем
    journal_df = read_journal_modulbank(journal_path)
    bank_df    = read_bank_modulbank(bank_path, owner_name=args.owner)

    if journal_df.empty:
        logger.error("Журнал не содержит данных по МодульБанк р/с")
        sys.exit(1)

    # Период сверки = с первой даты в журнале
    start_date = journal_df["date"].min()

    # Сопоставляем
    matched, missing, journal_only = match(journal_df, bank_df, start_date)

    # Консольный вывод
    total_bank = len(matched) + len(missing)
    cov = len(matched) / total_bank * 100 if total_bank else 0

    print(f"\n{'='*58}")
    print(f"  Сверка | {args.entity} | с {start_date}")
    print(f"{'='*58}")
    print(f"  Операций в банке за период:     {total_bank:>4}")
    print(f"  Найдено в журнале       ✅:     {len(matched):>4}  ({cov:.0f}%)")
    print(f"  Отсутствуют в журнале   ❌:     {len(missing):>4}")
    print(f"  Только в журнале        ⚠️:     {len(journal_only):>4}")
    print(f"{'='*58}")

    if not missing.empty:
        # Группируем по типу
        by_type = missing.groupby("Тип")["Сумма"].agg(["count", "sum"])
        print("\nОтсутствующие по типу:")
        for t, row in by_type.iterrows():
            print(f"  {t:<35} {int(row['count']):>3} шт.  {row['sum']:>14,.0f} руб.")

        print("\nТоп-10 отсутствующих (по |сумме|):")
        top10 = missing.reindex(
            missing["Сумма"].abs().sort_values(ascending=False).index
        ).head(10)
        for _, r in top10.iterrows():
            sign = "+" if r["Сумма"] > 0 else ""
            print(
                f"  {r['Дата']}  {sign}{r['Сумма']:>12,.0f}  "
                f"{r['Категория']:<28} {str(r['Контрагент'])[:35]}"
            )

    # Сохраняем
    export(matched, missing, journal_only, out_path, args.entity, start_date)
    print(f"\n✅ Отчёт: {out_path.resolve()}\n")


if __name__ == "__main__":
    main()
