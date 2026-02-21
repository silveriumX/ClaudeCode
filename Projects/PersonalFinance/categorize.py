# -*- coding: utf-8 -*-
"""
Categorize parsed Tinkoff transactions and produce summary.

Run after parse_statements.py.

Personal cash expenses are loaded from personal_config.py (gitignored).
Copy personal_config.example.py -> personal_config.py and fill in your data.

Usage:
    python categorize.py

Output (in DATA_DIR/parsed/):
    categorized.csv   -- all transactions with assigned categories
    final_summary.txt -- expense summary by category and period
"""

import csv
import os
import re
from collections import defaultdict
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = Path(os.getenv("PERSONAL_FINANCE_DATA_DIR", WORKSPACE_ROOT / "Личное" / "Мои деньги"))
SRC     = DATA_DIR / "parsed" / "all.csv"
OUT_CAT = DATA_DIR / "parsed" / "categorized.csv"
OUT_SUM = DATA_DIR / "parsed" / "final_summary.txt"

FILE_TO_PERIOD = {
    "ноябрь 2025.pdf":  "окт-ноя 2025",
    "декабрь 2025.pdf": "ноя-дек 2025",
    "январь 2026.pdf":  "дек-янв 2026",
    "февраль 2026.pdf": "янв-фев 2026",
}
PERIOD_ORDER = ["окт-ноя 2025", "ноя-дек 2025", "дек-янв 2026", "янв-фев 2026"]

# Own phone numbers (transfers to self)
OWN_PHONES = {
    "+79774819800": "Маркетплейс (Озон/ВБ)",
}

# Named contacts
CONTACT_PHONES = {
    "+37377976522": "Психолог",
    "+37377970999": "Мама",
}

# Own USDT savings card fragments (partial card numbers)
OWN_USDT_CARDS = ["5536 91", "2200 70", "427654"]


def get_phone(desc: str) -> str:
    m = re.search(r"\+\d+", desc)
    return m.group() if m else ""


def categorize(row: dict) -> str:
    desc      = row["description"].upper()
    direction = row["direction"]
    phone     = get_phone(row["description"])

    # Internal sub-account (cashback buckets) — skip
    if row["notes"] == "внутренний_субсчет":
        return "_SKIP"

    # Cash deposits (business income) — skip from expenses
    if direction == "наличные_внесение":
        return "_SKIP"

    # ATM withdrawals — cash expenses tracked separately in personal_config
    if direction == "наличные_снятие":
        return "_SKIP"

    # Transfers to own cards — USDT savings
    if "ПЕРЕВОД НА КАРТУ" in desc or "ПЕРЕВОД ПО НОМЕРУ КАРТЫ" in desc:
        if any(c in desc for c in OWN_USDT_CARDS):
            return "Сбережения/USDT"
        return "Прочее"

    # Internal Tinkoff account transfers (round-trip, skip)
    if "ВНУТРЕННИЙ ПЕРЕВОД НА ДОГОВОР" in desc and row["notes"] != "внутренний_субсчет":
        return "_SKIP"

    # Own phone numbers
    if phone in OWN_PHONES:
        return OWN_PHONES[phone]

    # Named contacts
    if phone in CONTACT_PHONES:
        return CONTACT_PHONES[phone]

    # Unknown transfers
    if direction == "перевод":
        return "Переводы (неизвестно)"

    # Other income — skip
    if direction == "доход":
        return "_INCOME"

    # ----------------------------------------------------------------
    # Card expenses
    # ----------------------------------------------------------------

    # Налоги
    if any(x in desc for x in ["ОПЛАТАГОСУСЛУГ.ФНС", "NALOG.RU", "GOSUSLUGI"]):
        return "Налоги"

    # Медицина — Medical On Group clinics (OP branches)
    if re.search(r"\bOP (PETROGRADSKOYE|TSENTRALNOYE|YUZHNOYE|SEVERNOYE|VYBORGSKOE)\b", desc):
        return "Медицина/Клиники"

    # Медицина — аптеки
    if any(x in desc for x in ["APTEKA", "36,6", "ORTEKA", "APTECHNOE", "АПТЕКА"]):
        return "Медицина/Аптеки"

    # Медицина — другие клиники / ИП
    if any(x in desc for x in ["PRIEMNYJ POKOJ", "WCLINIC", "BUD ZDOROV", "IP DMITRIYEV",
                                 "GEREGA", "IP LOBYNCEV"]):
        return "Медицина/Прочее"

    # Красота
    if any(x in desc for x in ["GOLDAPPLE", "SALON KRASOTY", "STUDIYA 134", "FAMILY C",
                                 "NOGTEV", "BEAUTY"]):
        return "Красота"

    # Подписки — детализированные
    if any(x in desc for x in ["MBANK.MEGAFON", "MBANK", "MEGAFON RITEJL",
                                 "MEGAFON RETAIL", "АО «МЕГАФОН"]):
        return "Подписки/МегаФон"
    if any(x in desc for x in ["YANDEX*PLUS", "YANDEX*5815"]):
        return "Подписки/Яндекс Плюс"
    if "СЕРВИСЫ ЯНДЕКСА" in desc:
        return "Развлечения"   # concert/event tickets via Yandex
    if "YANDEXBANK" in desc or "YANDEX*BANK" in desc or "ОПЕРАЦИЯ В ДРУГИХ КРЕДИТНЫХ" in desc:
        return "Подписки/ЯндексБанк"
    if any(x in desc for x in ["PLATA ZA SERVIS", "PLATA ZA SERVI",
                                 "ПЛАТА ЗА СЕРВИС", "ПЛАТА ЗА ОПОВЕЩЕНИЯ"]):
        return "Подписки/Тинькофф"
    if "GETCOURSE" in desc:
        return "Подписки/GetCourse"
    if "RUSPROFILE" in desc:
        return "Подписки/RusProfile"
    if "STARTER PAY" in desc:
        return "Подписки/Starter Pay"
    if any(x in desc for x in ["NEWPAYONLINE", "XPLAT", "VV_9"]):
        return "Подписки/Прочее"

    # Транспорт
    if any(x in desc for x in ["YANDEX*TAXI", "YANDEX*GO", "YANDEX*4121*GO",
                                 "YANDEX*4121*YANDEX GO", "YANDEX*4121*YANDEX DEL"]):
        return "Транспорт/Такси"
    if any(x in desc for x in ["METRO TPP", "METRO", "RUSSIAN RAILWAYS", "MOS.TRANSPORT"]):
        return "Транспорт/Метро и ж/д"

    # Доставка еды
    if any(x in desc for x in ["YANDEX*4215*DOSTAVKA", "YANDEX*DOSTAVKA", "DOSTAVKA"]):
        return "Доставка еды"

    # Путешествия / Виза
    if any(x in desc for x in ["OSTROVOK", "DMITRIIVISAKOREA", "KOREA"]):
        return "Путешествия/Виза"

    # Образование
    if any(x in desc for x in ["UCHI.RU", "ACADEMY", "SKILLBOX", "GEEKBRAINS"]):
        return "Образование"

    # Развлечения
    if any(x in desc for x in ["SINEMA", "AFISHA", "CITY.TRAVEL", "CLOUDKASSIR",
                                 "CYBER X", "PANORAMA 360", "YANDEX*AFISHA"]):
        return "Развлечения"

    # Кофейни
    if any(x in desc for x in ["ETLON COFFEE", "XO COFFEE", "DO.BRO COFFEE",
                                 "DRINKIT", "GOJA", "BAGGINS COFFEE", "COFFEE"]):
        return "Кафе/Кофейни"

    # Еда — рестораны и кафе
    if any(x in desc for x in [
        "YUKARI", "NETMONET", "LYUDI LYUBYAT", "EVRAZIYA", "GOROD 812",
        "DODO", "PIZZA", "STOLOVAYA", "KAFE", "RAMEN", "RESTORAN",
        "SESILIA", "TOKIO", "BRYNZA", "PIBIM", "YOKI", "AZBUKAVKUSA",
        "IP DORIN", "IP KALININA",
    ]):
        return "Кафе/Рестораны"

    # Еда — продукты
    if any(x in desc for x in [
        "PEKARNYA", "PEKARNA", "CEKH 85", "KHLEBNIK", "BYSTRO I VKUSNO",
        "PYATEROCHKA", "DIXY", "SPAR", "MAGNIT", "OQ M", "GROWFOOD",
        "VIPFISH", "VLAVASHE", "ВЛАВАШЕ", "GRADUSY", "BONTI",
        "YM*NUTS", "SP_ISTOK",
    ]):
        return "Еда/Продукты"

    # Разное
    if any(x in desc for x in ["CHITAJ-GOROD", "БУКВОЕД", "SUVENIRNYJ",
                                 "POST RUS", "BYURO PEREVODOV", "DNS"]):
        return "Разное"

    if any(x in desc for x in ["VTBCHAI", "ВТБ.ЧАЕВЫЕ"]):
        return "Чаевые"

    return "Прочее"


def load_cash_expenses() -> list[tuple]:
    """Load cash expenses from personal_config.py (gitignored). Returns [] if not found."""
    try:
        import importlib.util
        cfg_path = Path(__file__).parent / "personal_config.py"
        spec = importlib.util.spec_from_file_location("personal_config", cfg_path)
        cfg  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cfg)
        return getattr(cfg, "CASH_EXPENSES", [])
    except FileNotFoundError:
        print("[INFO] personal_config.py not found — no cash expenses loaded.")
        print("[INFO] Copy personal_config.example.py -> personal_config.py to add them.")
        return []


def main() -> None:
    with open(SRC, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    categorized = []
    for row in rows:
        cat = categorize(row)
        if cat.startswith("_"):
            continue
        period = FILE_TO_PERIOD.get(row["file"], row["file"])
        categorized.append({
            "period":      period,
            "date":        row["date"],
            "description": row["description"],
            "amount":      float(row["amount"]),
            "category":    cat,
            "source":      "карта",
        })

    for period, cat, desc, amount in load_cash_expenses():
        categorized.append({
            "period":      period,
            "date":        "—",
            "description": desc,
            "amount":      amount,
            "category":    cat,
            "source":      "наличные",
        })

    fields = ["period", "date", "description", "amount", "category", "source"]
    with open(OUT_CAT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(categorized)
    print(f"Saved {len(categorized)} rows -> categorized.csv")

    # Quick text summary
    cat_period: dict = defaultdict(lambda: defaultdict(float))
    for r in categorized:
        cat_period[r["category"]][r["period"]] += r["amount"]

    col_w = 14
    lines = ["=" * 90, "РАСХОДЫ ПО КАТЕГОРИЯМ", "=" * 90]
    header = f"{'Категория':<32}" + "".join(f"{p:>{col_w}}" for p in PERIOD_ORDER) + f"  {'ИТОГО':>{col_w}}"
    lines.append(header)
    lines.append("-" * 90)
    grand: dict = defaultdict(float)
    grand_total = 0.0
    for cat in sorted(cat_period):
        row_total = sum(cat_period[cat].values())
        grand_total += row_total
        row_str = f"  {cat:<30}" + "".join(f"{cat_period[cat].get(p,0):>{col_w},.0f}" for p in PERIOD_ORDER) + f"  {row_total:>{col_w},.0f}"
        lines.append(row_str)
        for p in PERIOD_ORDER:
            grand[p] += cat_period[cat].get(p, 0)
    lines.append("=" * 90)
    lines.append(f"{'ИТОГО':<32}" + "".join(f"{grand.get(p,0):>{col_w},.0f}" for p in PERIOD_ORDER) + f"  {grand_total:>{col_w},.0f}")

    report = "\n".join(lines)
    OUT_SUM.write_text(report, encoding="utf-8")
    print("\n" + report)


if __name__ == "__main__":
    main()
