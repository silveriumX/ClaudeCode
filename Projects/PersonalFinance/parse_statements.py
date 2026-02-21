# -*- coding: utf-8 -*-
"""
Parse Tinkoff bank statement PDFs -> compact CSV.

Reads PDFs from DATA_DIR (default: <workspace>/Личное/Мои деньги/).
Override by setting env var PERSONAL_FINANCE_DATA_DIR.

Usage:
    python parse_statements.py

Output (in DATA_DIR/parsed/):
    <name>.csv   -- transactions per PDF
    all.csv      -- all files combined
    summary.txt  -- balance check per file
"""

import csv
import os
import re
from pathlib import Path

import pdfplumber

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = Path(os.getenv("PERSONAL_FINANCE_DATA_DIR", WORKSPACE_ROOT / "Личное" / "Мои деньги"))
OUT_DIR = DATA_DIR / "parsed"
OUT_DIR.mkdir(exist_ok=True)

# PDF filenames to process (in DATA_DIR)
PDFS = [
    "ноябрь 2025.pdf",
    "декабрь 2025.pdf",
    "январь 2026.pdf",
    "февраль 2026.pdf",
]

CSV_HEADERS = ["file", "date", "description", "amount", "direction", "notes"]

RE_TXN_START = re.compile(
    r"^(\d{2}\.\d{2}\.\d{2})(?:\s+\d{2}:\d{2})?\s+\d{2}\.\d{2}\.\d{2}\s+(.+?)\s+(\+?\s*[\d\s]+[\.,]\d{2})\s*₽\s+(\+?\s*[\d\s]+[\.,]\d{2})\s*₽\s*$"
)
RE_TXN_ALT = re.compile(
    r"^(\d{2}\.\d{2}\.\d{2})\s+\d{2}\.\d{2}\.\d{2}\s+(.+?)\s+(\+?\s*[\d\s]+[\.,]\d{2})\s*₽\s+(\+?\s*[\d\s]+[\.,]\d{2})\s*₽\s*$"
)
RE_BALANCE  = re.compile(r"Баланс на (\d{2}\.\d{2}\.\d{2})\s+([\d\s]+[\.,]\d{2})\s*₽")
RE_INCOME   = re.compile(r"Поступления\s+([\d\s]+[\.,]\d{2})\s*₽")
RE_EXPENSE  = re.compile(r"Расходы\s+-\s*([\d\s]+[\.,]\d{2})\s*₽")
RE_CASHBACK = re.compile(r"Кэшбэк\s+([\d\s]+[\.,]\d{2})\s*₽")


def clean_amount(s: str) -> float:
    s = s.strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
    return float(s[1:]) if s.startswith("+") else float(s)


def parse_statement(pdf_path: Path) -> tuple[list[dict], dict]:
    with pdfplumber.open(pdf_path) as pdf:
        lines = []
        for page in pdf.pages:
            lines.extend((page.extract_text(x_tolerance=3, y_tolerance=3) or "").splitlines())

    full_text = "\n".join(lines)
    balances   = RE_BALANCE.findall(full_text)
    income_m   = RE_INCOME.search(full_text)
    expense_m  = RE_EXPENSE.search(full_text)
    cashback_m = RE_CASHBACK.search(full_text)

    summary = {
        "file":               pdf_path.name,
        "balance_open_date":  balances[0][0] if len(balances) >= 1 else "",
        "balance_open":       clean_amount(balances[0][1]) if len(balances) >= 1 else 0,
        "balance_close_date": balances[1][0] if len(balances) >= 2 else "",
        "balance_close":      clean_amount(balances[1][1]) if len(balances) >= 2 else 0,
        "income":    clean_amount(income_m.group(1))   if income_m   else 0,
        "expenses":  clean_amount(expense_m.group(1))  if expense_m  else 0,
        "cashback":  clean_amount(cashback_m.group(1)) if cashback_m else 0,
    }

    transactions = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = RE_TXN_START.match(line) or RE_TXN_ALT.match(line)
        if m:
            date_raw, desc, _amount_str, amount_rub_str = m.groups()
            day, mon, yr = date_raw.split(".")
            date = f"{day}.{mon}.20{yr}"
            amount_rub = clean_amount(amount_rub_str)
            is_income  = "+" in amount_rub_str

            # Continuation line (location suffix, contract number, etc.)
            continuation = ""
            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if (nxt
                        and not RE_TXN_START.match(nxt)
                        and not RE_TXN_ALT.match(nxt)
                        and not re.match(r"^\d{2}\.\d{2}\.\d{2}", nxt)
                        and not nxt.startswith("•")
                        and len(nxt) < 50):
                    continuation = nxt
                    i += 1

            full_desc = re.sub(r"\s+", " ", f"{desc} {continuation}".strip())
            direction = "доход" if is_income else "расход"
            notes = ""

            if any(x in full_desc for x in [
                "Внутренний перевод на договор 8276667349",
                "Внутренний перевод на договор 5545154709",
                "Внутрибанковский перевод с договора 8276667349",
                "Внутренний перевод на договор 5198138623",
            ]):
                notes = "внутренний_субсчет"
            elif "Внутренний перевод на карту" in full_desc:
                notes = "внутренняя_карта"
            elif "Внешний перевод по номеру телефона" in full_desc:
                direction = "перевод"
            elif "Внесение наличных" in full_desc:
                direction = "наличные_внесение"
            elif "Снятие" in full_desc or "ATM" in full_desc.upper():
                direction = "наличные_снятие"

            transactions.append({
                "file":        pdf_path.name,
                "date":        date,
                "description": full_desc,
                "amount":      amount_rub if is_income else -amount_rub,
                "direction":   direction,
                "notes":       notes,
            })
        i += 1

    return transactions, summary


def main() -> None:
    all_txns: list[dict] = []
    summaries: list[dict] = []

    for pdf_name in PDFS:
        pdf_path = DATA_DIR / pdf_name
        if not pdf_path.exists():
            print(f"[SKIP] not found: {pdf_path}")
            continue

        print(f"\n=== {pdf_name} ===")
        txns, summary = parse_statement(pdf_path)
        print(f"  parsed: {len(txns)} transactions")
        print(f"  period: {summary['balance_open_date']} -> {summary['balance_close_date']}")
        print(f"  open: {summary['balance_open']:,.2f}  close: {summary['balance_close']:,.2f}")

        out = OUT_DIR / f"{Path(pdf_name).stem}.csv"
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADERS).writeheader()
            csv.DictWriter(f, fieldnames=CSV_HEADERS).writerows(txns)
        print(f"  -> {out.name}")

        all_txns.extend(txns)
        summaries.append(summary)

    all_out = OUT_DIR / "all.csv"
    with open(all_out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        w.writeheader()
        w.writerows(all_txns)

    summary_lines = ["BALANCE SUMMARY\n" + "=" * 50]
    for s in summaries:
        summary_lines.append(
            f"\n{s['file']}\n"
            f"  Period:   {s['balance_open_date']} -> {s['balance_close_date']}\n"
            f"  Open:     {s['balance_open']:,.2f}\n"
            f"  Income:   {s['income']:,.2f}  Expenses: -{s['expenses']:,.2f}  Cashback: {s['cashback']:,.2f}\n"
            f"  Close:    {s['balance_close']:,.2f}"
        )
    (OUT_DIR / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"\nTotal: {len(all_txns)} transactions -> {all_out}")


if __name__ == "__main__":
    main()
