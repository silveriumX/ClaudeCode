"""
Налоговый калькулятор для ИП на УСН (Доходы).

Считает налоговую нагрузку по схеме:
    УСН 6% × gross_income
    − вычет страховые взносы ИП (уменьшают УСН до 50%)
    + 1% ИП с дохода свыше 300 000 руб. (в ПФР, сверхлимит)
    + НДФЛ с выплат сотрудникам (если есть)

Результат: расчётный налог за период + сравнение с фактическими
платежами из банковской выписки.

Налоговая схема DBZ (ИП Пирожкова Н.В.):
    УСН:   6% от доходов на р/с (поступления от WB)
    Взносы ИП фиксированные: ежегодно (актуализировать)
    Доп. 1%: с дохода > 300 000 руб. за год, уплачивается до 1 июля
    НДФЛ:  13% с зарплат официальных сотрудников (если есть)

Важно:
    - "Доход" для УСН = поступления на р/с от WB (не продажи WB!)
    - Страховые взносы уменьшают УСН, но не более чем на 50%
    - Взносы ИП за себя: фиксированная часть + 1% сверхлимит
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Налоговые константы (обновлять ежегодно)
# ──────────────────────────────────────────────

@dataclass
class TaxScheme:
    """Параметры налоговой схемы ИП УСН-Доходы."""

    # УСН
    usn_rate: float = 0.06           # ставка УСН (6% по умолчанию)

    # Страховые взносы ИП фиксированные (руб./год)
    # 2024: 49 500 руб. | 2025: 53 658 руб. | уточнять ежегодно
    fixed_contributions_2024: float = 49_500.0
    fixed_contributions_2025: float = 53_658.0
    fixed_contributions_2026: float = 57_390.0   # предварительно

    # 1% с дохода свыше 300 000 руб./год (ПФР)
    extra_contrib_threshold: float = 300_000.0
    extra_contrib_rate: float = 0.01             # 1%
    extra_contrib_max: float = 277_571.0         # максимум 2024 (8 × МРОТ × 12)

    # НДФЛ с сотрудников
    ndfl_rate: float = 0.13

    # УСН уменьшается на взносы, но не более 50%
    usn_deduction_max_pct: float = 0.50

    def fixed_contributions(self, year: int) -> float:
        """Фиксированные взносы ИП за год."""
        mapping = {
            2024: self.fixed_contributions_2024,
            2025: self.fixed_contributions_2025,
            2026: self.fixed_contributions_2026,
        }
        val = mapping.get(year)
        if val is None:
            logger.warning("tax_calc: взносы для %d не заданы, используем 2026", year)
            val = self.fixed_contributions_2026
        return val


@dataclass
class TaxResult:
    """Результат расчёта налоговой нагрузки за период."""

    period_label: str
    income_rub: float                  # доход для УСН (поступления на р/с от WB)

    # Расчётные
    usn_gross: float = 0.0            # УСН до вычета
    fixed_contrib_period: float = 0.0 # взносы ИП за период (пропорционально)
    extra_contrib: float = 0.0        # 1% с превышения 300к
    usn_deduction: float = 0.0        # вычет из УСН (≤ 50%)
    usn_net: float = 0.0              # УСН к уплате (после вычета)
    total_tax: float = 0.0            # итого налог + взносы

    # Фактические платежи из р/с (если есть)
    paid_usn_rub: float = 0.0
    paid_contrib_rub: float = 0.0
    paid_ndfl_rub: float = 0.0

    @property
    def diff_usn(self) -> float:
        """Расхождение расчётного УСН и фактически уплаченного."""
        return self.usn_net - self.paid_usn_rub

    @property
    def total_paid(self) -> float:
        return self.paid_usn_rub + self.paid_contrib_rub + self.paid_ndfl_rub

    def to_dict(self) -> Dict[str, float]:
        return {
            "Период": self.period_label,
            "Доход УСН (р/с)": self.income_rub,
            "УСН 6% (расчётно)": self.usn_gross,
            "Взносы ИП (период)": self.fixed_contrib_period,
            "1% с превышения 300к": self.extra_contrib,
            "Вычет из УСН": self.usn_deduction,
            "УСН к уплате (расчётно)": self.usn_net,
            "ИТОГО налог+взносы (расчётно)": self.total_tax,
            "Уплачено УСН (р/с)": self.paid_usn_rub,
            "Уплачено взносов (р/с)": self.paid_contrib_rub,
            "Уплачено НДФЛ (р/с)": self.paid_ndfl_rub,
            "Расхождение УСН": self.diff_usn,
        }


def calc_tax(
    income_rub: float,
    period_label: str,
    year: int,
    months_in_period: int = 12,
    ndfl_base_rub: float = 0.0,
    scheme: Optional[TaxScheme] = None,
) -> TaxResult:
    """
    Рассчитать налоговую нагрузку ИП УСН-Доходы за период.

    Логика:
        1. УСН = income_rub × usn_rate
        2. Взносы ИП за период = fixed_contributions(year) × (months / 12)
        3. 1% = max(0, income_rub − 300 000) × 1%  [только если годовой расчёт]
        4. Вычет из УСН = min(взносы_период + 1%, УСН × 50%)
        5. УСН к уплате = УСН − вычет
        6. Итого = УСН_к_уплате + взносы_период + 1% + НДФЛ

    Args:
        income_rub:        Доход за период (поступления от WB на р/с).
        period_label:      Название периода для отчёта.
        year:              Год (для выбора ставки взносов).
        months_in_period:  Кол-во месяцев в периоде (для расчёта взносов пропорционально).
        ndfl_base_rub:     База для НДФЛ (зарплаты официальных сотрудников).
        scheme:            Налоговая схема (дефолтная, если не передана).

    Returns:
        TaxResult с расчётными показателями.
    """
    if scheme is None:
        scheme = TaxScheme()

    result = TaxResult(period_label=period_label, income_rub=income_rub)

    # 1. УСН gross
    result.usn_gross = round(income_rub * scheme.usn_rate, 2)

    # 2. Взносы ИП за период (пропорционально месяцам)
    annual_contrib = scheme.fixed_contributions(year)
    result.fixed_contrib_period = round(annual_contrib * months_in_period / 12, 2)

    # 3. 1% с превышения 300к (актуально для полного года или при известном годовом доходе)
    excess = max(0.0, income_rub - scheme.extra_contrib_threshold)
    result.extra_contrib = round(min(excess * scheme.extra_contrib_rate, scheme.extra_contrib_max), 2)

    # 4. Вычет из УСН = взносы + 1%, но не более 50% УСН
    total_contrib = result.fixed_contrib_period + result.extra_contrib
    max_deduction = round(result.usn_gross * scheme.usn_deduction_max_pct, 2)
    result.usn_deduction = round(min(total_contrib, max_deduction), 2)

    # 5. УСН к уплате
    result.usn_net = round(max(0.0, result.usn_gross - result.usn_deduction), 2)

    # 6. НДФЛ
    ndfl = round(ndfl_base_rub * scheme.ndfl_rate, 2)

    # 7. Итого
    result.total_tax = round(result.usn_net + total_contrib + ndfl, 2)

    logger.info(
        "Налоги [%s]: доход=%.0f | УСН=%.0f | вычет=%.0f | УСН_нетто=%.0f | взносы=%.0f | итого=%.0f",
        period_label, income_rub, result.usn_gross, result.usn_deduction,
        result.usn_net, total_contrib, result.total_tax,
    )
    return result


def extract_tax_payments(bank_df: pd.DataFrame) -> Dict[str, float]:
    """
    Извлечь фактически уплаченные налоги из банковской выписки.

    Использует категории из classifier.py:
        'Налог УСН'     → paid_usn_rub
        'Страх. взносы' → paid_contrib_rub
        'НДФЛ'          → paid_ndfl_rub

    Args:
        bank_df: DataFrame из parser.py с колонкой 'category' и 'amount'.

    Returns:
        Dict с суммами по типам налогов.
    """
    if bank_df is None or bank_df.empty:
        return {"paid_usn_rub": 0.0, "paid_contrib_rub": 0.0, "paid_ndfl_rub": 0.0}

    payments = {"paid_usn_rub": 0.0, "paid_contrib_rub": 0.0, "paid_ndfl_rub": 0.0}

    # Ищем по категории или по назначению платежа
    usn_keywords = ["усн", "налог по усн", "упрощенная система"]
    contrib_keywords = ["страховые взносы", "фиксированные взносы", "пфр", "омс"]
    ndfl_keywords = ["ндфл", "налог на доходы"]

    for _, row in bank_df.iterrows():
        category = str(row.get("category", "")).lower()
        purpose = str(row.get("purpose", "")).lower()
        recipient = str(row.get("recipient", "")).lower()
        text = f"{category} {purpose} {recipient}"
        amount = abs(float(row.get("amount", 0)))

        if any(kw in text for kw in usn_keywords):
            payments["paid_usn_rub"] += amount
        elif any(kw in text for kw in contrib_keywords):
            payments["paid_contrib_rub"] += amount
        elif any(kw in text for kw in ndfl_keywords):
            payments["paid_ndfl_rub"] += amount

    return payments


def calc_tax_from_bank(
    bank_df: pd.DataFrame,
    period_label: str,
    year: int,
    months_in_period: int = 1,
    scheme: Optional[TaxScheme] = None,
) -> TaxResult:
    """
    Сокращённый вариант: считает налог по доходам из банковской выписки
    и сравнивает с фактически уплаченными суммами.

    Args:
        bank_df:           DataFrame из parser.py (фильтрованный по периоду).
        period_label:      Название периода.
        year:              Год.
        months_in_period:  Количество месяцев.
        scheme:            Налоговая схема.

    Returns:
        TaxResult с расчётными и фактическими данными.
    """
    # Доход = поступления (положительные суммы) из р/с
    income = 0.0
    if not bank_df.empty and "amount_rub" in bank_df.columns:
        income_rows = bank_df[bank_df["amount_rub"] > 0]
        # Исключаем возвраты налогов и внутренние переводы
        if "tx_type" in bank_df.columns:
            income_rows = income_rows[~income_rows["tx_type"].isin(
                ["Перевод (внутренний)", "Возврат налога"]
            )]
        income = income_rows["amount_rub"].sum()

    result = calc_tax(income, period_label, year, months_in_period, scheme=scheme)

    # Фактические платежи
    paid = extract_tax_payments(bank_df)
    result.paid_usn_rub = paid["paid_usn_rub"]
    result.paid_contrib_rub = paid["paid_contrib_rub"]
    result.paid_ndfl_rub = paid["paid_ndfl_rub"]

    return result
