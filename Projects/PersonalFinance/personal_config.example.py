# -*- coding: utf-8 -*-
"""
Personal cash expenses — NOT committed to git (gitignored).

Copy this file to personal_config.py and fill in your actual amounts.
personal_config.py is listed in .gitignore.

Format:
    CASH_EXPENSES = [
        (period, category, description, amount),
        ...
    ]

Period values (must match categorize.py FILE_TO_PERIOD):
    "окт-ноя 2025"
    "ноя-дек 2025"
    "дек-янв 2026"
    "янв-фев 2026"

Category values must match a category used in categorize.py GROUPS,
or you can introduce a new one (add it to GROUPS in upload_to_sheets.py too).

Amount: negative = expense, positive = income (same sign convention as card txns).
"""

CASH_EXPENSES = [
    # ("окт-ноя 2025", "Аренда квартиры", "Аренда (наличные) — ноябрь", -70_000),
    # ("ноя-дек 2025", "Аренда квартиры", "Аренда (наличные) — декабрь", -70_000),
    # ("дек-янв 2026", "Аренда квартиры", "Аренда (наличные) — январь",  -70_000),
    # ("янв-фев 2026", "Аренда квартиры", "Аренда (наличные) — февраль", -70_000),
    # ("янв-фев 2026", "Спорт/Бокс",      "Бокс 15 тренировок (наличные)", -43_200),
    # ("янв-фев 2026", "Медицина/Операция", "Операция (наличные)",         -82_000),
]
