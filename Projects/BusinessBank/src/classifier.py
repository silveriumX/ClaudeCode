"""
Классификатор операций банковской выписки.

Правила определены на основе анализа реальной выписки Модульбанка
(счёт 40802810570010435344, ИП Пирожкова — юрлицо DBZ).

Порядок проверки важен: более специфичные правила идут первыми.
"""

import re
import logging
from typing import Optional

import pandas as pd

from .categories import (
    TYPE_INCOME, TYPE_EXPENSE, TYPE_TRANSFER_INTERNAL, TYPE_TRANSFER_WITHDRAWAL,
    CAT_INCOME_WB, CAT_INCOME_OZON, CAT_INCOME_OTHER,
    CAT_GOODS, CAT_FULFILLMENT, CAT_LOGISTICS, CAT_MARKETPLACE,
    CAT_SALARY, CAT_RENT, CAT_TAXES, CAT_CERT, CAT_MARKETING,
    CAT_IT, CAT_OFFICE, CAT_BANK, CAT_REPR, CAT_OTHER,
)

logger = logging.getLogger(__name__)


class TransactionClassifier:
    """
    Классифицирует строку банковской выписки по типу и категории.

    Возвращает dict с ключами: type, category, subcategory, confidence.
    confidence = 'auto' (правило сработало) или 'manual' (нужна проверка).
    """

    # ── Паттерны поиска ────────────────────────────────────────────────────────

    _TRANSFER_RE = re.compile(r'перевод между счет|перевод собственн', re.IGNORECASE)
    # Назначения, характерные для выплат зарплаты ИП владельцу (не расход в PnL)
    _OWNER_WITHDRAWAL_PURPOSE_RE = re.compile(
        r'зарплата ип|выплата ип|вывод средств|перевод личн|прибыль ип',
        re.IGNORECASE
    )
    _SALARY_RE = re.compile(
        r'зарплат|оплата труда|выплата заработ|заработная плата',
        re.IGNORECASE
    )
    _FULFILLMENT_RE = re.compile(
        r'фулфилмент|склад(ское|овое)?\s+обслуж|оказани[яе].{0,15}(услуг|улсуг).{0,20}склад|'
        r'хранени[ея]|маркировк|упаковк|приёмк|приемк|логистик|сборк|'
        r'доставк.{0,10}груз|доставк.{0,10}товар|перевозк',
        re.IGNORECASE
    )
    # Паттерны по НАЗВАНИЮ КОНТРАГЕНТА (дополнительная проверка)
    _FULFILLMENT_COUNTERPARTY_RE = re.compile(
        r'склад|фулфилмент|логистик|склада|хранени',
        re.IGNORECASE
    )
    _CERT_RE = re.compile(
        r'сертификат|декларац|протокол соответст|испытани[ея]|эцп|'
        r'электронн.{0,5}подпис|подтверждени[яи] соответств|сертотека',
        re.IGNORECASE
    )
    _IT_RE = re.compile(
        r'телефони|интернет|хостинг|домен|подписка|1[Сс][\s:]|'
        r'лицензи[яи]|программ|CRM|ERP|SaaS|облако|облачн|'
        r'\bМТТ\b|мобильн.{0,10}(телефон|связ)|бухгалтери|онлайн.{0,10}бухг',
        re.IGNORECASE
    )
    _RENT_RE = re.compile(
        r'аренд|субаренд|коммунальн|электроэнерги|водоснабж',
        re.IGNORECASE
    )
    _GOODS_RE = re.compile(
        r'за товар|поставк|закупк|приобретени[ея]\s+товар|'
        r'за отпугива|за продукци[юи]|за изделия|за комплектующ',
        re.IGNORECASE
    )
    _MARKETING_RE = re.compile(
        r'дизайн|фотосъемк|фото[- ]?сессия|видео|блогер|реклам|контент|'
        r'съемк|инфлюенс|креатив',
        re.IGNORECASE
    )
    _WB_INCOME_RE = re.compile(
        r'wildberries|вайлдберр|РВБ|ВАЙЛДБЕРРИЗ',
        re.IGNORECASE
    )
    _OZON_INCOME_RE = re.compile(
        r'\bOzon\b|\bОзон\b',
        re.IGNORECASE
    )
    _MODULBANK_COUNTERPARTY_RE = re.compile(r'модульбанк', re.IGNORECASE)
    _MBH_RE = re.compile(r'модульбух|МодульБух', re.IGNORECASE)
    _TAX_PATTERNS = [
        ("НДС",               re.compile(r'\bНДС\b', re.IGNORECASE)),
        ("УСН",               re.compile(r'\bУСН\b', re.IGNORECASE)),
        ("НДФЛ",              re.compile(r'\bНДФЛ\b', re.IGNORECASE)),
        ("Страховые взносы",  re.compile(r'страховые|взнос 1%|взнос ИП|фиксированн.{0,10}взнос', re.IGNORECASE)),
        ("ЕНП / ЕНС",        re.compile(r'\bЕНП\b|\bЕНС\b|единый налог', re.IGNORECASE)),
    ]
    _BANK_FEE_SUBTYPES = [
        ("Комиссия за операцию", re.compile(r'комиссия за (перевод|операцию|платёж|платеж)', re.IGNORECASE)),
        ("Обслуживание счёта",   re.compile(r'обслуживание (расч|счет|карт|плат)', re.IGNORECASE)),
        ("Тариф",                re.compile(r'тариф', re.IGNORECASE)),
        ("Подключение сервиса",  re.compile(r'подключение|\"белый бизнес\"', re.IGNORECASE)),
    ]

    # ── ИНН известных контрагентов ─────────────────────────────────────────────

    # Wildberries платит через ООО "РВБ"
    INN_WB_RVB = "9714053621"
    # ФНС России / Казначейство
    INN_FNS = "7727406020"
    # Фулфилмент-партнёры (можно расширять)
    FULFILLMENT_INNS: set[str] = {
        "503802069670",  # ИП Брасова
        "561608327250",  # ИП Укасов
        "581906088302",  # ИП Девляшкина
        "0275978918",    # ИП Бахтиева
    }
    # МТТ — телефония/IT
    INN_MTT = "7733119038"

    MODULBANK_BIC = "044525092"

    def classify(self, row: pd.Series, owner_name: str = "") -> dict:
        """
        Классифицирует одну строку выписки.

        Args:
            row: строка DataFrame с полями: purpose, counterparty, inn,
                 bank, bic, account, is_income.
            owner_name: имя владельца р/с (ФИО ИП/директора). Если контрагент
                        совпадает с владельцем — это вывод на личный счёт, не расход.

        Returns:
            dict(type, category, subcategory, confidence)
        """
        purpose     = str(row.get("purpose", "")).strip()
        counterparty = str(row.get("counterparty", "")).strip()
        bank        = str(row.get("bank", "")).strip()
        bic         = str(row.get("bic", "")).strip()
        inn_raw     = str(row.get("inn", "")).strip()
        inn         = inn_raw.split("/")[0].strip()  # убираем КПП
        is_income   = bool(row.get("is_income", False))

        # ── 1a. Пополнение р/с с личного счёта (входящее, но НЕ доход) ──────
        # "Внесение собственных средств" = Наташа вернула деньги на р/с с карты
        if is_income and re.search(r'внесение собственн|пополнение счёт|пополнение счет', purpose, re.IGNORECASE):
            return self._result(TYPE_TRANSFER_INTERNAL, "—", "пополнение р/с с личного счёта")

        # ── 1b. Возврат платежа (счёт получателя закрыт и т.п.) ─────────────
        if is_income and re.search(r'возврат (средств|п/п|платеж|платёж)|счет получателя закрыт', purpose, re.IGNORECASE):
            return self._result(TYPE_TRANSFER_INTERNAL, "—", "возврат платежа")

        # ── 1. Внутренний перевод / вывод на карту ───────────────────────────
        if self._TRANSFER_RE.search(purpose):
            if bic == self.MODULBANK_BIC or self._MODULBANK_COUNTERPARTY_RE.search(bank):
                return self._result(TYPE_TRANSFER_INTERNAL, "—", "р/с ↔ Маркет-карта")
            else:
                return self._result(TYPE_TRANSFER_WITHDRAWAL, "—", f"→ {bank}" if bank else "→ другой банк")

        # ── 1b. Вывод на личный счёт (контрагент = владелец р/с) ─────────────
        # Покрывает переводы владельцу ИП без пометки "перевод между счетами"
        if not is_income and owner_name:
            owner_parts = owner_name.lower().split()
            cp_lower = counterparty.lower()
            # Совпадение по фамилии + имени (2 из 3 слов ФИО)
            matches = sum(1 for part in owner_parts if len(part) > 2 and part in cp_lower)
            if matches >= 2:
                return self._result(
                    TYPE_TRANSFER_WITHDRAWAL, "—",
                    f"→ {bank}" if bank else "→ личный счёт"
                )

        # ── 2. Доход ──────────────────────────────────────────────────────────
        if is_income:
            if inn == self.INN_WB_RVB or self._WB_INCOME_RE.search(counterparty):
                return self._result(TYPE_INCOME, CAT_INCOME_WB, counterparty)
            if self._OZON_INCOME_RE.search(counterparty):
                return self._result(TYPE_INCOME, CAT_INCOME_OZON, counterparty)
            return self._result(TYPE_INCOME, CAT_INCOME_OTHER, counterparty, confidence="manual")

        # ── Дальше только расходы ─────────────────────────────────────────────

        # ── 3. Налоги и сборы ─────────────────────────────────────────────────
        is_tax_receiver = (
            inn == self.INN_FNS
            or "казначейство" in counterparty.lower()
            or "осфр" in counterparty.lower()
            or "социальн" in counterparty.lower()
            or "пенсионн" in counterparty.lower()
        )
        if is_tax_receiver:
            subcategory = self._detect_tax_subtype(purpose)
            if not subcategory or subcategory == "ЕНП / ЕНС":
                # ОСФР = страховые взносы
                if "осфр" in counterparty.lower() or "социальн" in counterparty.lower():
                    subcategory = "Страховые взносы (СФР)"
            return self._result(TYPE_EXPENSE, CAT_TAXES, subcategory)

        # ── 4. Банковские расходы (Модульбанк) ───────────────────────────────
        if self._MODULBANK_COUNTERPARTY_RE.search(counterparty):
            if self._MBH_RE.search(purpose):
                return self._result(TYPE_EXPENSE, CAT_IT, "МодульБух (бухгалтерия)")
            return self._result(TYPE_EXPENSE, CAT_BANK, self._detect_bank_fee(purpose))

        # ── 5. Фулфилмент (по ИНН, назначению или названию контрагента) ──────
        if (inn in self.FULFILLMENT_INNS
                or self._FULFILLMENT_RE.search(purpose)
                or self._FULFILLMENT_COUNTERPARTY_RE.search(counterparty)):
            return self._result(TYPE_EXPENSE, CAT_FULFILLMENT, counterparty)

        # ── 6. IT и сервисы ───────────────────────────────────────────────────
        if inn == self.INN_MTT or self._IT_RE.search(counterparty) or self._IT_RE.search(purpose):
            return self._result(TYPE_EXPENSE, CAT_IT, counterparty)

        # ── 7. Зарплата ───────────────────────────────────────────────────────
        if self._SALARY_RE.search(purpose):
            return self._result(TYPE_EXPENSE, CAT_SALARY, counterparty)

        # ── 8. Аренда ─────────────────────────────────────────────────────────
        if self._RENT_RE.search(purpose):
            return self._result(TYPE_EXPENSE, CAT_RENT, counterparty)

        # ── 9. Сертификация ───────────────────────────────────────────────────
        if self._CERT_RE.search(purpose):
            return self._result(TYPE_EXPENSE, CAT_CERT, counterparty)

        # ── 10. Закупка товара ────────────────────────────────────────────────
        if self._GOODS_RE.search(purpose):
            return self._result(TYPE_EXPENSE, CAT_GOODS, counterparty)

        # ── 11. Маркетинг ─────────────────────────────────────────────────────
        if self._MARKETING_RE.search(purpose):
            return self._result(TYPE_EXPENSE, CAT_MARKETING, counterparty)

        # ── 12. Прочее (требует ручной проверки) ─────────────────────────────
        return self._result(TYPE_EXPENSE, CAT_OTHER, counterparty, confidence="manual")

    # ── Вспомогательные методы ────────────────────────────────────────────────

    def _detect_tax_subtype(self, purpose: str) -> str:
        for subtype, pattern in self._TAX_PATTERNS:
            if pattern.search(purpose):
                return subtype
        return "ЕНП / ЕНС"  # дефолт: единый налоговый платёж

    def _detect_bank_fee(self, purpose: str) -> str:
        for subtype, pattern in self._BANK_FEE_SUBTYPES:
            if pattern.search(purpose):
                return subtype
        return "Прочие банковские расходы"

    @staticmethod
    def _result(
        op_type: str,
        category: str,
        subcategory: str = "",
        confidence: str = "auto",
    ) -> dict:
        return {
            "type": op_type,
            "category": category,
            "subcategory": subcategory,
            "confidence": confidence,
        }
