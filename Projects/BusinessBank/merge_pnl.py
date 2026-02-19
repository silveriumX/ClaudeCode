#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сводный P&L: банковская выписка + FinanceBot расходы.

Объединяет данные из разных источников в единый журнал и строит P&L
на трёх уровнях: Юрлицо → Кластер → Компания.

Использование:
    python -X utf8 merge_pnl.py \\
        --bank "Примеры выписок из Модульбанка/Statement.xlsx" \\
        --entity DBZ \\
        --owner "Пирожкова Наталья Викторовна" \\
        --clusters clusters.json \\
        [--fb-creds "../FinanceBot/service_account.json"] \\
        [--fb-sheets "1bFBHIB53h7TJBknJatJn_y__11jCIP45ZbGsatnb1G4"] \\
        [--out pnl_DBZ.xlsx]

    Если --fb-creds / --fb-sheets не указаны — считает только по банку.
"""

import argparse
import io
import json
import logging
import sys
from pathlib import Path
from typing import Optional

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from src.parser import parse_statement
from src.classifier import TransactionClassifier
from src.categories import TYPE_INCOME, TYPE_EXPENSE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_clusters(path: Path) -> dict:
    """Load clusters.json. Strip _comment keys."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    # strip _comment keys recursively
    def strip_comments(obj):
        if isinstance(obj, dict):
            return {k: strip_comments(v) for k, v in obj.items() if not k.startswith("_")}
        return obj
    return strip_comments(raw)


# ---------------------------------------------------------------------------
# Bank data → unified journal
# ---------------------------------------------------------------------------

def _classify_bank(df: pd.DataFrame, entity: str, owner: str) -> pd.DataFrame:
    """Run TransactionClassifier on raw bank DataFrame. Returns classified rows."""
    clf = TransactionClassifier()
    results = [clf.classify(row, owner_name=owner) for _, row in df.iterrows()]

    out = df.copy()
    out["entity"]      = entity
    out["tx_type"]     = [r["type"]       for r in results]
    out["category"]    = [r["category"]   for r in results]
    out["subcategory"] = [r["subcategory"] for r in results]
    out["source"]      = "bank"
    out["currency"]    = "RUB"
    return out


def _bank_to_unified(classified: pd.DataFrame) -> pd.DataFrame:
    """
    Convert classified bank DataFrame to unified journal.
    Only Доход / Расход rows. Transfers excluded.
    amount_rub: positive for income, negative for expense.
    """
    pnl = classified[classified["tx_type"].isin([TYPE_INCOME, TYPE_EXPENSE])].copy()

    unified = pd.DataFrame({
        "date":        pnl["date"],
        "amount_rub":  pnl.apply(
            lambda r: r["amount"] if r["tx_type"] == TYPE_INCOME else -r["amount"],
            axis=1,
        ),
        "tx_type":     pnl["tx_type"],
        "category":    pnl["category"],
        "subcategory": pnl["subcategory"],
        "entity":      pnl["entity"],
        "is_shared":   False,
        "source":      "bank",
        "description": pnl["purpose"].fillna(""),
        "counterparty": pnl["counterparty"].fillna(""),
    })
    return unified.reset_index(drop=True)


# ---------------------------------------------------------------------------
# FinanceBot data → unified journal
# ---------------------------------------------------------------------------

def _fb_to_unified(fb_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert fb_adapter output to unified journal.
    All FB records are expenses → amount_rub is negative.
    """
    if fb_df.empty:
        return pd.DataFrame(columns=[
            "date", "amount_rub", "tx_type", "category", "subcategory",
            "entity", "is_shared", "source", "description", "counterparty",
        ])

    df = fb_df.copy()
    unified = pd.DataFrame({
        "date":        df["date"],
        "amount_rub":  -df["amount_rub"].fillna(0),  # expenses are negative
        "tx_type":     "Расход",
        "category":    df["category"],
        "subcategory": "",
        "entity":      df["entity"],
        "is_shared":   df["is_shared"],
        "source":      "financebot_" + df["source_sheet"].str.lower()
                       .str.replace(" ", "_", regex=False)
                       .str.replace("фактические_расходы", "cash", regex=False),
        "description": (df["purpose"].fillna("") + " → " + df["recipient"].fillna(""))
                       .str.strip(" →"),
        "counterparty": df["recipient"].fillna(""),
    })
    return unified.reset_index(drop=True)


# ---------------------------------------------------------------------------
# P&L builders
# ---------------------------------------------------------------------------

def _month_label(year: int, month: int) -> str:
    return f"{int(year)}-{int(month):02d}"


def build_entity_pnl(unified: pd.DataFrame, entity: str) -> pd.DataFrame:
    """
    Monthly P&L for a single entity.
    Includes: bank (income + expense) + FB expenses tagged to this entity.
    Shared FB expenses shown as a separate row per month.
    """
    df = unified.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    entity_df = df[
        (df["entity"] == entity) | df["is_shared"]
    ].copy()

    rows = []
    for (year, month), grp in entity_df.groupby(["year", "month"]):
        bank_income  = grp[(grp["source"] == "bank") & (grp["amount_rub"] > 0)]["amount_rub"].sum()
        bank_expense = grp[(grp["source"] == "bank") & (grp["amount_rub"] < 0)]["amount_rub"].sum()
        fb_entity    = grp[
            (grp["source"].str.startswith("financebot")) & (~grp["is_shared"])
        ]["amount_rub"].sum()
        fb_shared    = grp[
            (grp["source"].str.startswith("financebot")) & grp["is_shared"]
        ]["amount_rub"].sum()

        total_expense = bank_expense + fb_entity + fb_shared
        profit        = bank_income + total_expense  # total_expense is negative
        margin        = round(profit / bank_income * 100, 1) if bank_income > 0 else 0.0

        rows.append({
            "Период":               _month_label(year, month),
            "Доходы (банк)":        round(bank_income, 2),
            "Расходы банк":         round(-bank_expense, 2),
            "Расходы FinanceBot":   round(-(fb_entity + fb_shared), 2),
            "  в т.ч. entity":      round(-fb_entity, 2),
            "  в т.ч. общие":       round(-fb_shared, 2),
            "Расходы итого":        round(-total_expense, 2),
            "Прибыль":              round(profit, 2),
            "Маржа %":              margin,
        })

    return pd.DataFrame(rows)


def build_category_breakdown(unified: pd.DataFrame, entity: str) -> pd.DataFrame:
    """Expense breakdown by category for the given entity (all time)."""
    df = unified[
        (unified["amount_rub"] < 0) &
        ((unified["entity"] == entity) | unified["is_shared"])
    ].copy()

    df["month"] = df["date"].dt.to_period("M").astype(str)

    breakdown = (
        df.groupby(["month", "category", "source"])["amount_rub"]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"amount_rub": "Сумма", "month": "Период",
                         "category": "Категория", "source": "Источник"})
        .sort_values(["Период", "Сумма"], ascending=[True, False])
    )
    return breakdown


def build_company_pnl(unified: pd.DataFrame) -> pd.DataFrame:
    """Monthly P&L for the entire company (all entities + all shared)."""
    df = unified.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    rows = []
    for (year, month), grp in df.groupby(["year", "month"]):
        income   = grp[grp["amount_rub"] > 0]["amount_rub"].sum()
        expense  = grp[grp["amount_rub"] < 0]["amount_rub"].sum()
        shared   = grp[grp["is_shared"]]["amount_rub"].sum()
        bank_exp = grp[(grp["source"] == "bank") & (grp["amount_rub"] < 0)]["amount_rub"].sum()
        fb_exp   = grp[grp["source"].str.startswith("financebot")]["amount_rub"].sum()
        profit   = income + expense
        margin   = round(profit / income * 100, 1) if income > 0 else 0.0

        rows.append({
            "Период":             _month_label(year, month),
            "Доходы":             round(income, 2),
            "Расходы (банк)":     round(-bank_exp, 2),
            "Расходы (FinanceBot)": round(-fb_exp, 2),
            "  в т.ч. общие":     round(-shared, 2),
            "Расходы итого":      round(-expense, 2),
            "Прибыль":            round(profit, 2),
            "Маржа %":            margin,
        })

    return pd.DataFrame(rows)


def build_full_journal(unified: pd.DataFrame) -> pd.DataFrame:
    """Full sorted journal for inspection."""
    return (
        unified
        .assign(
            Дата=unified["date"].dt.date,
            Сумма_RUB=unified["amount_rub"].round(2),
            Тип=unified["tx_type"],
            Категория=unified["category"],
            Юрлицо=unified["entity"],
            Общий=unified["is_shared"].map({True: "да", False: "нет"}),
            Источник=unified["source"],
            Назначение=unified["description"],
        )
        [["Дата", "Сумма_RUB", "Тип", "Категория", "Юрлицо", "Общий", "Источник", "Назначение"]]
        .sort_values("Дата")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def _print_pnl(df: pd.DataFrame, title: str) -> None:
    print(f"\n{'='*72}")
    print(f"  {title}")
    print(f"{'='*72}")
    if df.empty:
        print("  (нет данных)")
        return
    print(df.to_string(index=False))
    print(f"{'='*72}")


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

def export_excel(
    entity_pnl: pd.DataFrame,
    company_pnl: pd.DataFrame,
    category_bd: pd.DataFrame,
    journal: pd.DataFrame,
    output_path: Path,
    entity: str,
) -> None:
    """Write all P&L tables to a single Excel file."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        company_pnl.to_excel(writer,  sheet_name="🏢 Компания",          index=False)
        entity_pnl.to_excel(writer,   sheet_name=f"📋 {entity}",          index=False)
        category_bd.to_excel(writer,  sheet_name="🔍 Категории",          index=False)
        journal.to_excel(writer,      sheet_name="📄 Журнал",             index=False)

        for ws in writer.sheets.values():
            for col in ws.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 55)

    logger.info("Отчёт сохранён: %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Сводный P&L: банк + FinanceBot"
    )
    ap.add_argument("--bank",      required=True, help="Путь к XLSX выписке банка")
    ap.add_argument("--entity",    required=True, help="Код юрлица: DBZ, MN, VAS…")
    ap.add_argument("--owner",     default="",    help='ФИО владельца р/с (для классификации переводов)')
    ap.add_argument("--clusters",  default="clusters.json", help="Путь к clusters.json")
    ap.add_argument("--fb-creds",  default=None,  help="Путь к service_account.json (FinanceBot)")
    ap.add_argument("--fb-sheets", default=None,  help="Google Sheets ID FinanceBot")
    ap.add_argument("--out",       default=None,  help="Имя выходного Excel (по умолчанию: pnl_<entity>.xlsx)")
    ap.add_argument("--last-months", type=int, default=None,
                    help="Ограничить анализ последними N месяцами")
    args = ap.parse_args()

    bank_path   = Path(args.bank)
    output_path = Path(args.out) if args.out else Path(f"pnl_{args.entity}.xlsx")

    if not bank_path.exists():
        logger.error("Файл не найден: %s", bank_path)
        sys.exit(1)

    # Load config
    clusters_path = Path(args.clusters)
    cfg = load_clusters(clusters_path) if clusters_path.exists() else {}
    entity_patterns = cfg.get("entity_patterns", {})
    fx_rates        = cfg.get("fx_rates", {"BYN": 30.0, "KZT": 0.2, "USDT": 90.0, "CNY": 13.0})

    # ---- 1. Bank data -------------------------------------------------------
    logger.info("Парсинг банковской выписки: %s", bank_path)
    raw_bank = parse_statement(bank_path)

    if args.last_months:
        cutoff = raw_bank["date"].max() - pd.DateOffset(months=args.last_months)
        raw_bank = raw_bank[raw_bank["date"] >= cutoff].copy()
        logger.info("Фильтр: последние %d мес. (с %s)", args.last_months, cutoff.date())

    classified_bank = _classify_bank(raw_bank, entity=args.entity, owner=args.owner)
    unified_bank    = _bank_to_unified(classified_bank)
    logger.info("Банк: %d операций P&L", len(unified_bank))

    # ---- 2. FinanceBot data (optional) --------------------------------------
    unified_fb = pd.DataFrame()
    if args.fb_creds and args.fb_sheets:
        from src.fb_adapter import read_financebot_expenses
        logger.info("Загрузка FinanceBot Sheets…")
        fb_raw    = read_financebot_expenses(
            sheets_id         = args.fb_sheets,
            credentials_path  = args.fb_creds,
            entity_patterns   = entity_patterns,
            fx_rates          = fx_rates,
        )
        unified_fb = _fb_to_unified(fb_raw)
        logger.info("FinanceBot: %d расходов", len(unified_fb))
    else:
        logger.info("FinanceBot не подключён (--fb-creds/--fb-sheets не указаны)")

    # ---- 3. Merge -----------------------------------------------------------
    frames = [unified_bank]
    if not unified_fb.empty:
        frames.append(unified_fb)

    unified = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    logger.info("Единый журнал: %d строк", len(unified))

    # ---- 4. P&L tables ------------------------------------------------------
    entity_pnl  = build_entity_pnl(unified, entity=args.entity)
    company_pnl = build_company_pnl(unified)
    category_bd = build_category_breakdown(unified, entity=args.entity)
    journal     = build_full_journal(unified)

    # ---- 5. Console output --------------------------------------------------
    _print_pnl(entity_pnl,  f"P&L | {args.entity}")
    _print_pnl(company_pnl, "P&L | Компания (всё)")

    # ---- 6. Excel export ----------------------------------------------------
    export_excel(entity_pnl, company_pnl, category_bd, journal, output_path, args.entity)
    print(f"\n✅ Готово! Отчёт: {output_path.resolve()}")


if __name__ == "__main__":
    main()
