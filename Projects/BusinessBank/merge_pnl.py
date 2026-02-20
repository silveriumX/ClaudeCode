#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сводный P&L: банковские выписки (несколько) + FinanceBot расходы.

Объединяет данные из разных источников в единый журнал и строит P&L
на трёх уровнях: Юрлицо → Кластер → Компания.

USDT-расходы показываются отдельным блоком (в USDT), без смешивания с RUB.

Использование:
    # Один банковский счёт
    python -X utf8 merge_pnl.py \\
        --bank "Выписки/modulbank.xlsx" \\
        --entity DBZ --owner "Пирожкова Наталья Викторовна" \\
        --clusters clusters.json \\
        --fb-creds "../FinanceBot/service_account.json" \\
        --fb-sheets "1bFBHIB53h7TJBknJatJn_y__11jCIP45ZbGsatnb1G4" \\
        --out pnl_DBZ.xlsx

    # Несколько счетов одного юрлица
    python -X utf8 merge_pnl.py \\
        --bank "modulbank_rc.xlsx" "tinkoff.xlsx" "sberbank.xlsx" \\
        --entity DBZ --owner "Пирожкова Наталья Викторовна"

    Если --fb-creds / --fb-sheets не указаны — считает только по банку.
"""

import argparse
import io
import json
import logging
import sys
from pathlib import Path

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
# Config
# ---------------------------------------------------------------------------

def load_clusters(path: Path) -> dict:
    """Load clusters.json, strip _comment keys."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    def strip_comments(obj):
        if isinstance(obj, dict):
            return {k: strip_comments(v) for k, v in obj.items() if not k.startswith("_")}
        return obj

    return strip_comments(raw)


# ---------------------------------------------------------------------------
# Unified journal schema
#
# Each row represents one transaction:
#   amount_rub  — signed RUB amount (positive=income, negative=expense)
#                 For RUB/BYN/KZT transactions only. 0 for USDT.
#   amount_usdt — signed USDT amount (negative=expense).
#                 For USDT transactions only. 0 for RUB.
#   currency    — original currency of the transaction
#
# This keeps USDT separate from the RUB P&L. The two columns are
# mutually exclusive per row.
# ---------------------------------------------------------------------------

_UNIFIED_COLS = [
    "date", "amount_rub", "amount_usdt", "currency",
    "tx_type", "category", "subcategory",
    "entity", "is_shared", "source", "description", "counterparty",
]


def _empty_unified() -> pd.DataFrame:
    return pd.DataFrame(columns=_UNIFIED_COLS)


# ---------------------------------------------------------------------------
# Bank data → unified
# ---------------------------------------------------------------------------

def _classify_bank(df: pd.DataFrame, entity: str, owner: str) -> pd.DataFrame:
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
    Convert classified bank DataFrame to unified rows.
    Only Доход / Расход. Transfers excluded.
    Bank transactions are always RUB → amount_usdt = 0.
    """
    pnl = classified[classified["tx_type"].isin([TYPE_INCOME, TYPE_EXPENSE])].copy()

    return pd.DataFrame({
        "date":        pnl["date"],
        "amount_rub":  pnl.apply(
            lambda r: r["amount"] if r["tx_type"] == TYPE_INCOME else -r["amount"], axis=1
        ),
        "amount_usdt": 0.0,
        "currency":    "RUB",
        "tx_type":     pnl["tx_type"],
        "category":    pnl["category"],
        "subcategory": pnl["subcategory"],
        "entity":      pnl["entity"],
        "is_shared":   False,
        "source":      "bank",
        "description": pnl["purpose"].fillna(""),
        "counterparty": pnl["counterparty"].fillna(""),
    }).reset_index(drop=True)


# ---------------------------------------------------------------------------
# FinanceBot data → unified
# ---------------------------------------------------------------------------

def _fb_to_unified(fb_df: pd.DataFrame, fx_rates: dict) -> pd.DataFrame:
    """
    Convert fb_adapter output to unified rows.

    USDT expenses → amount_rub = 0, amount_usdt = -amount (shown separately).
    RUB/BYN/KZT expenses → amount_rub = -amount_rub (negative), amount_usdt = 0.
    CNY → treated as RUB-group (converted via fx_rates).
    """
    if fb_df.empty:
        return _empty_unified()

    df = fb_df.copy()
    is_usdt = df["currency"] == "USDT"

    # For non-USDT: use pre-computed amount_rub from fb_adapter (already converted)
    # For USDT: set amount_rub = 0, amount_usdt = raw USDT amount
    amount_rub_signed = df.apply(
        lambda r: 0.0 if r["currency"] == "USDT"
                  else -(r["amount_rub"] if pd.notna(r["amount_rub"]) else r["amount"]),
        axis=1,
    )
    amount_usdt_signed = df.apply(
        lambda r: -r["amount"] if r["currency"] == "USDT" else 0.0,
        axis=1,
    )

    def _source_label(sheet: str) -> str:
        sheet_lower = sheet.lower().replace(" ", "_")
        if "факт" in sheet_lower:
            return "financebot_cash"
        if "usdt" in sheet_lower:
            return "financebot_usdt"
        if "cny" in sheet_lower:
            return "financebot_cny"
        return "financebot_rub"

    return pd.DataFrame({
        "date":        df["date"],
        "amount_rub":  amount_rub_signed,
        "amount_usdt": amount_usdt_signed,
        "currency":    df["currency"],
        "tx_type":     "Расход",
        "category":    df["category"],
        "subcategory": "",
        "entity":      df["entity"],
        "is_shared":   df["is_shared"],
        "source":      df["source_sheet"].map(_source_label),
        "description": (df["purpose"].fillna("") + " → " + df["recipient"].fillna("")).str.strip(" →"),
        "counterparty": df["recipient"].fillna(""),
    }).reset_index(drop=True)


# ---------------------------------------------------------------------------
# P&L builders
# ---------------------------------------------------------------------------

def _month_label(year: int, month: int) -> str:
    return f"{int(year)}-{int(month):02d}"


def build_entity_pnl(
    unified: pd.DataFrame,
    entity: str,
    usdt_rate: float = 90.0,
) -> pd.DataFrame:
    """
    Monthly P&L for one entity.

    RUB section: bank income + (bank + FB-RUB) expenses.
    USDT section: FB-USDT expenses in USDT + approx RUB equivalent.
    Entity-tagged + shared FB expenses are both included.
    """
    df = unified.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    # Include entity-specific rows + shared (for company overhead)
    scope = df[(df["entity"] == entity) | df["is_shared"]]

    rows = []
    for (year, month), grp in scope.groupby(["year", "month"]):
        bank   = grp[grp["source"] == "bank"]
        fb_rub = grp[grp["source"].isin(["financebot_rub", "financebot_cash", "financebot_cny"])]
        fb_usd = grp[grp["source"] == "financebot_usdt"]

        income       = bank[bank["amount_rub"] > 0]["amount_rub"].sum()
        bank_exp     = bank[bank["amount_rub"] < 0]["amount_rub"].sum()
        fb_rub_exp   = fb_rub["amount_rub"].sum()
        usdt_exp_u   = fb_usd["amount_usdt"].sum()   # in USDT (negative)
        usdt_exp_rub = usdt_exp_u * usdt_rate         # approx RUB equivalent

        total_rub_exp = bank_exp + fb_rub_exp
        profit_rub    = income + total_rub_exp        # excl. USDT

        rows.append({
            "Период":                _month_label(year, month),
            # RUB block
            "Доходы (RUB)":          round(income, 2),
            "Расходы банк (RUB)":    round(-bank_exp, 2),
            "Расходы FB-RUB":        round(-fb_rub_exp, 2),
            "Расходы RUB итого":     round(-total_rub_exp, 2),
            "Прибыль (без USDT)":    round(profit_rub, 2),
            # USDT block (separate)
            "USDT расходы (USDT)":   round(-usdt_exp_u, 4),
            f"USDT ≈ RUB ({usdt_rate})": round(-usdt_exp_rub, 2),
            # Margin (RUB only)
            "Маржа % (RUB)":         round(profit_rub / income * 100, 1) if income > 0 else 0.0,
        })

    return pd.DataFrame(rows)


def build_company_pnl(
    unified: pd.DataFrame,
    usdt_rate: float = 90.0,
) -> pd.DataFrame:
    """Monthly P&L for the entire company (all entities + all shared)."""
    df = unified.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    rows = []
    for (year, month), grp in df.groupby(["year", "month"]):
        income       = grp[grp["amount_rub"] > 0]["amount_rub"].sum()
        bank_exp     = grp[(grp["source"] == "bank") & (grp["amount_rub"] < 0)]["amount_rub"].sum()
        fb_rub_exp   = grp[grp["source"].isin(["financebot_rub", "financebot_cash"])]["amount_rub"].sum()
        usdt_exp_u   = grp[grp["source"] == "financebot_usdt"]["amount_usdt"].sum()
        usdt_exp_rub = usdt_exp_u * usdt_rate
        shared_rub   = grp[grp["is_shared"] & (grp["source"] != "financebot_usdt")]["amount_rub"].sum()
        shared_usd   = grp[grp["is_shared"] & (grp["source"] == "financebot_usdt")]["amount_usdt"].sum()

        total_rub_exp = bank_exp + fb_rub_exp
        profit_rub    = income + total_rub_exp

        rows.append({
            "Период":                     _month_label(year, month),
            "Доходы (RUB)":               round(income, 2),
            "Расходы банк (RUB)":         round(-bank_exp, 2),
            "Расходы FB-RUB":             round(-fb_rub_exp, 2),
            "  в т.ч. общие RUB":         round(-shared_rub, 2),
            "Расходы RUB итого":          round(-total_rub_exp, 2),
            "Прибыль (без USDT)":         round(profit_rub, 2),
            "Маржа % (RUB)":              round(profit_rub / income * 100, 1) if income > 0 else 0.0,
            # USDT block
            "USDT расходы (USDT)":        round(-usdt_exp_u, 4),
            "  в т.ч. общие USDT":        round(-shared_usd, 4),
            f"USDT ≈ RUB ({usdt_rate})":  round(-usdt_exp_rub, 2),
        })

    return pd.DataFrame(rows)


def build_category_breakdown(
    unified: pd.DataFrame,
    entity: str,
) -> pd.DataFrame:
    """Expense breakdown by category (all time, entity + shared)."""
    df = unified[
        ((unified["entity"] == entity) | unified["is_shared"])
        & ((unified["amount_rub"] < 0) | (unified["amount_usdt"] < 0))
    ].copy()

    df["period"] = df["date"].dt.to_period("M").astype(str)
    df["amount_display"] = df.apply(
        lambda r: abs(r["amount_usdt"]) if r["source"] == "financebot_usdt"
                  else abs(r["amount_rub"]),
        axis=1,
    )
    df["валюта"] = df["currency"]

    return (
        df.groupby(["period", "category", "source", "валюта"])["amount_display"]
        .sum()
        .reset_index()
        .rename(columns={
            "period": "Период", "category": "Категория",
            "source": "Источник", "amount_display": "Сумма",
        })
        .sort_values(["Период", "Сумма"], ascending=[True, False])
        .reset_index(drop=True)
    )


def build_full_journal(unified: pd.DataFrame) -> pd.DataFrame:
    """Sorted full journal for inspection."""
    df = unified.copy()
    df["amount_display"] = df.apply(
        lambda r: r["amount_usdt"] if r["source"] == "financebot_usdt" else r["amount_rub"],
        axis=1,
    ).round(4)

    return (
        df.assign(
            Дата=df["date"].dt.date,
            Сумма=df["amount_display"],
            Валюта=df["currency"],
            Тип=df["tx_type"],
            Категория=df["category"],
            Юрлицо=df["entity"],
            Общий=df["is_shared"].map({True: "да", False: "нет"}),
            Источник=df["source"],
            Назначение=df["description"],
        )
        [["Дата", "Сумма", "Валюта", "Тип", "Категория", "Юрлицо", "Общий", "Источник", "Назначение"]]
        .sort_values("Дата")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def _print_pnl(df: pd.DataFrame, title: str) -> None:
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")
    if df.empty:
        print("  (нет данных)")
        return
    print(df.to_string(index=False))
    print(f"{'='*80}")


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
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        company_pnl.to_excel(writer, sheet_name="🏢 Компания",   index=False)
        entity_pnl.to_excel(writer,  sheet_name=f"📋 {entity}",  index=False)
        category_bd.to_excel(writer, sheet_name="🔍 Категории",  index=False)
        journal.to_excel(writer,     sheet_name="📄 Журнал",     index=False)

        for ws in writer.sheets.values():
            for col in ws.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 55)

    logger.info("Отчёт сохранён: %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Сводный P&L: банк(и) + FinanceBot")
    ap.add_argument(
        "--bank", nargs="+", required=True,
        help="Путь(и) к XLSX выпискам банка. Можно указать несколько через пробел.",
    )
    ap.add_argument("--entity",    required=True, help="Код юрлица: DBZ, MN, VAS…")
    ap.add_argument("--owner",     default="",    help="ФИО владельца р/с")
    ap.add_argument("--clusters",  default="clusters.json")
    ap.add_argument("--fb-creds",  default=None,  help="service_account.json (FinanceBot)")
    ap.add_argument("--fb-sheets", default=None,  help="Google Sheets ID FinanceBot")
    ap.add_argument("--out",       default=None)
    ap.add_argument("--last-months", type=int, default=None,
                    help="Ограничить последними N месяцами")
    args = ap.parse_args()

    output_path = Path(args.out) if args.out else Path(f"pnl_{args.entity}.xlsx")

    # Config
    clusters_path = Path(args.clusters)
    cfg = load_clusters(clusters_path) if clusters_path.exists() else {}
    entity_patterns = cfg.get("entity_patterns", {})
    fx_rates        = cfg.get("fx_rates", {"BYN": 30.0, "KZT": 0.2, "USDT": 90.0, "CNY": 13.0})
    usdt_rate       = fx_rates.get("USDT", 90.0)

    # ---- 1. Bank data (one or more files) -----------------------------------
    bank_parts = []
    for bank_file in args.bank:
        p = Path(bank_file)
        if not p.exists():
            logger.error("Файл не найден: %s", p)
            sys.exit(1)
        logger.info("Парсинг выписки: %s", p.name)
        raw = parse_statement(p)
        if args.last_months:
            cutoff = raw["date"].max() - pd.DateOffset(months=args.last_months)
            raw = raw[raw["date"] >= cutoff].copy()
        classified = _classify_bank(raw, entity=args.entity, owner=args.owner)
        bank_parts.append(_bank_to_unified(classified))

    unified_bank = pd.concat(bank_parts, ignore_index=True) if bank_parts else _empty_unified()
    # Deduplicate by (date, amount, counterparty) if same file loaded twice
    unified_bank = unified_bank.drop_duplicates(
        subset=["date", "amount_rub", "counterparty"]
    ).reset_index(drop=True)
    logger.info("Банк: %d операций P&L (из %d файл(ов))", len(unified_bank), len(args.bank))

    # ---- 2. FinanceBot data (optional) --------------------------------------
    unified_fb = _empty_unified()
    if args.fb_creds and args.fb_sheets:
        from src.fb_adapter import read_financebot_expenses
        logger.info("Загрузка FinanceBot Sheets…")
        fb_raw = read_financebot_expenses(
            sheets_id        = args.fb_sheets,
            credentials_path = args.fb_creds,
            entity_patterns  = entity_patterns,
            fx_rates         = fx_rates,
        )
        unified_fb = _fb_to_unified(fb_raw, fx_rates)
        usdt_count = (unified_fb["source"] == "financebot_usdt").sum()
        rub_count  = len(unified_fb) - usdt_count
        logger.info("FinanceBot: %d расходов (%d USDT + %d RUB/др.)", len(unified_fb), usdt_count, rub_count)
    else:
        logger.info("FinanceBot не подключён")

    # ---- 3. Merge -----------------------------------------------------------
    frames = [f for f in [unified_bank, unified_fb] if not f.empty]
    unified = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    logger.info("Единый журнал: %d строк", len(unified))

    # ---- 4. P&L -------------------------------------------------------------
    entity_pnl  = build_entity_pnl(unified, entity=args.entity, usdt_rate=usdt_rate)
    company_pnl = build_company_pnl(unified, usdt_rate=usdt_rate)
    category_bd = build_category_breakdown(unified, entity=args.entity)
    journal     = build_full_journal(unified)

    _print_pnl(entity_pnl,  f"P&L | {args.entity}")
    _print_pnl(company_pnl, "P&L | Компания (всё)")

    # ---- 5. Export ----------------------------------------------------------
    export_excel(entity_pnl, company_pnl, category_bd, journal, output_path, args.entity)
    print(f"\n✅ Готово! Отчёт: {output_path.resolve()}")


if __name__ == "__main__":
    main()
