"""
Парсеры PDF выписок личных счетов физлиц.

Поддерживаемые банки:
  - АльфаБанк   (alfa)
  - ВТБ          (vtb)
  - Сбербанк     (sber)
  - Т-Банк       (tbank)

Возвращают нормализованный DataFrame той же схемы, что ModulbankParser:
  date, doc_num, counterparty, inn, bank, bic, account,
  purpose, amount_in, amount_out, is_income, amount
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pdfplumber

from .parser import NORMALIZED_COLUMNS

logger = logging.getLogger(__name__)


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def _parse_ru_amount(s: str) -> float:
    """Парсит российский формат суммы: '1 234,56' → 1234.56, '+300 000,00' → 300000.0."""
    s = str(s).strip()
    if not s or s in ("nan", "None", "-", ""):
        return 0.0
    sign = -1.0 if s.startswith("-") else 1.0
    s = re.sub(r"[\s\u00a0]", "", s.lstrip("+-"))
    s = s.replace(",", ".")
    try:
        return sign * float(s)
    except ValueError:
        return 0.0


def _parse_en_amount(s: str) -> float:
    """Парсит английский формат ВТБ: '300,000.00 RUB' → 300000.0."""
    s = str(s).strip()
    if not s or s in ("nan", "None", "-", "0.00", "0"):
        return 0.0
    sign = -1.0 if s.startswith("-") else 1.0
    # Убираем суффикс валюты, пробелы, переносы строк
    s = re.sub(r"[A-Za-zА-Яа-я₽\s\u00a0\n]", "", s.lstrip("+-"))
    s = s.replace(",", "")  # запятая = разделитель тысяч в формате ВТБ
    try:
        return sign * float(s)
    except ValueError:
        return 0.0


def _parse_rub_amount(s: str) -> float:
    """Парсит формат Т-Банка: '-1 200.52 ₽' → -1200.52, '+500 000.00' → 500000.0."""
    s = str(s).strip()
    if not s:
        return 0.0
    sign = -1.0 if s.startswith("-") else 1.0
    s = re.sub(r"[₽A-Za-z\s\u00a0]", "", s.lstrip("+-"))
    try:
        return sign * float(s)
    except ValueError:
        return 0.0


def _make_row(
    date_str: str,
    doc_num: str,
    counterparty: str,
    purpose: str,
    signed_amount: float,
    inn: str = "",
    bank_name: str = "",
    bic: str = "",
    account: str = "",
) -> Optional[dict]:
    """Создаёт нормализованную строку DataFrame. Возвращает None если дата не распознана."""
    date = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
    if pd.isna(date):
        return None
    is_income = signed_amount > 0
    abs_amount = abs(signed_amount)
    return {
        "date": date,
        "doc_num": str(doc_num).strip(),
        "counterparty": str(counterparty).strip()[:200],
        "inn": inn,
        "bank": bank_name,
        "bic": bic,
        "account": account,
        "purpose": str(purpose).strip()[:500],
        "amount_in": abs_amount if is_income else 0.0,
        "amount_out": abs_amount if not is_income else 0.0,
        "is_income": is_income,
        "amount": abs_amount,
    }


def _rows_to_df(rows: List[Optional[dict]]) -> pd.DataFrame:
    valid = [r for r in rows if r is not None]
    if not valid:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)
    return pd.DataFrame(valid)[NORMALIZED_COLUMNS]


# ─── АльфаБанк ───────────────────────────────────────────────────────────────

class AlfaBankParser:
    """
    Парсер PDF выписки АльфаБанка.

    Формат: каждая транзакция — одна строка:
        DD.MM.YYYY  CODE  DESCRIPTION  [-]AMOUNT,NN RUR
    Описание иногда переносится на следующие строки,
    но сумма всегда присутствует на первой.
    """

    # Начало строки транзакции: дата + буквенно-цифровой код
    _TX_START_RE = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s+([A-Za-z0-9_]+)\s+")
    # Сумма в конце строки: "[-]N NNN,NN RUR"
    _AMOUNT_END_RE = re.compile(r"([-+]?\d[\d\s\u00a0]*,\d{2})\s+RUR\s*$")

    def parse(self, file_path: Path) -> pd.DataFrame:
        logger.info(f"[Alfa] Парсинг: {file_path.name}")
        rows: List[Optional[dict]] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                rows.extend(self._parse_text(text))
        df = _rows_to_df(rows)
        logger.info(
            f"[Alfa] {len(df)} операций | "
            f"Приход: {df['amount_in'].sum():,.0f} | "
            f"Расход: {df['amount_out'].sum():,.0f}"
        )
        return df

    def _parse_text(self, text: str) -> List[Optional[dict]]:
        rows = []
        for line in text.split("\n"):
            m = self._TX_START_RE.match(line)
            if not m:
                continue
            date_str = m.group(1)
            doc_num = m.group(2)
            rest = line[m.end():]

            # Сумма всегда в конце первой строки транзакции
            am = self._AMOUNT_END_RE.search(rest)
            if not am:
                # Иногда сумма идёт сразу за кодом без пробела — ищем во всей строке
                am = self._AMOUNT_END_RE.search(line)
            if not am:
                continue

            amount_str = am.group(1)
            amount = _parse_ru_amount(amount_str)
            # Описание — между кодом и суммой
            desc = rest[: rest.rfind(amount_str)].strip()
            counterparty = self._extract_counterparty(desc)
            row = _make_row(date_str, doc_num, counterparty, desc, amount)
            if row:
                rows.append(row)
        return rows

    def _extract_counterparty(self, desc: str) -> str:
        # "в MERCHANT через"  (СБП-платёж)
        m = re.search(r"\bв\s+([^\n.]+?)\s+через\b", desc)
        if m:
            return m.group(1).strip()[:100]
        # "Получатель MERCHANT"  (QR-платёж)
        m = re.search(r"Получатель\s+(.+?)(?:\s*[-\d]|\s*$)", desc)
        if m:
            return m.group(1).strip()[:100]
        # Операция по карте — "...\MERCHANT MCC"
        m = re.search(r"\\([^\\]+?)\s+MCC\d{4}", desc)
        if m:
            return m.group(1).strip()[:100]
        # СБП-перевод на/от телефона
        m = re.search(r"(?:на|от)\s+(\+\d[\d\s]{9,})", desc)
        if m:
            return m.group(1).strip()[:20]
        # "в пользу MERCHANT"
        m = re.search(r"в пользу\s+(.+?)(?:\s+[-\d]|\s*$)", desc)
        if m:
            return m.group(1).strip()[:100]
        # Банковские комиссии
        if re.search(r"комиссия|пакет услуг|обслуживание", desc, re.IGNORECASE):
            return "АльфаБанк"
        if re.search(r"внутрибанк", desc, re.IGNORECASE):
            return "АльфаБанк (внутр.)"
        return desc[:80]


# ─── ВТБ ─────────────────────────────────────────────────────────────────────

class VTBParser:
    """
    Парсер PDF выписки ВТБ.

    Использует pdfplumber table extraction — таблицы распознаются корректно.

    Колонки (0-indexed):
      0 — дата + время операции
      1 — дата обработки банком
      2 — сумма в валюте операции
      3 — Приход (в валюте счёта)
      4 — Расход (в валюте счёта)
      5 — Комиссия
      6 — Описание операции

    Итоговый расход = Расход + Комиссия (взаимоисключающие колонки).
    """

    _DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}")

    def parse(self, file_path: Path) -> pd.DataFrame:
        logger.info(f"[VTB] Парсинг: {file_path.name}")
        rows: List[Optional[dict]] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    rows.extend(self._parse_table(table))
        df = _rows_to_df(rows)
        logger.info(
            f"[VTB] {len(df)} операций | "
            f"Приход: {df['amount_in'].sum():,.0f} | "
            f"Расход: {df['amount_out'].sum():,.0f}"
        )
        return df

    def _parse_table(self, table: list) -> List[Optional[dict]]:
        rows = []
        for raw in table:
            if len(raw) < 7:
                continue
            cell0 = str(raw[0] or "").strip()
            if not self._DATE_RE.match(cell0):
                continue  # заголовок или пустая строка

            date_str = self._DATE_RE.match(cell0).group()
            income     = _parse_en_amount(raw[3] or "0")
            expense    = _parse_en_amount(raw[4] or "0")
            commission = _parse_en_amount(raw[5] or "0")
            desc       = str(raw[6] or "").replace("\n", " ").strip()

            total_out = expense + commission
            if income > 0:
                signed = income
            elif total_out > 0:
                signed = -total_out
            else:
                continue  # нулевая строка

            counterparty = self._extract_counterparty(desc)
            row = _make_row(date_str, "", counterparty, desc, signed)
            if row:
                rows.append(row)
        return rows

    def _extract_counterparty(self, desc: str) -> str:
        # "Оплата товаров и услуг. MERCHANT. по карте *NNNN"
        parts = [p.strip() for p in re.split(r"\.\s+", desc)]
        if len(parts) >= 2:
            cp = parts[1].rstrip(".")
            cp = re.sub(r"\s+по\s+карте\s+\*\d+.*$", "", cp).strip()
            if cp and not cp.lower().startswith("по карте"):
                return cp[:100]
        # "Переводы через СБП. ... Пирожкова Наталья Викторовна."
        m = re.search(r"(?:средств|перевод)[.\s]+(.+?)\.\s*$", desc, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:100]
        return desc[:100]


# ─── Сбербанк ────────────────────────────────────────────────────────────────

class SberbankParser:
    """
    Парсер PDF выписки Сбербанка.

    Формат (2-3 строки на транзакцию):
      Строка 1 (главная): DD.MM.YYYY HH:MM AUTH_CODE CATEGORY [+]AMOUNT,NN BALANCE,NN
      Строка 2 (описание): DD.MM.YYYY DESCRIPTION. Операция по [карте|счету] ****NNNN
      Строка 3+: продолжение описания (иногда)

    Признак дохода: сумма начинается с '+'. Без знака = расход.
    """

    # Главная строка транзакции: дата + время (HH:MM) + 5-7-значный код авторизации
    _MAIN_RE = re.compile(
        r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+(\d{5,7})\s+(.+?)\s+"
        r"(\+?\d[\d\s\u00a0]*,\d{2})\s+(\d[\d\s\u00a0]*,\d{2})\s*$"
    )
    # Строка с датой обработки: DD.MM.YYYY без времени следом
    _PROC_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}\s+(?!\d{2}:\d{2})")

    _HEADER_KEYWORDS = (
        "Выписка по", "ДАТА ОПЕРАЦИИ", "КАТЕГОРИЯ", "СУММА В ВАЛЮТЕ",
        "Дата обработки", "Описание операции", "Действителен до",
        "Зайдите", "QR-код", "Продолжение на следующей", "приложение",
        "ОСТАТОК НА", "ВСЕГО ПОПОЛНЕНИЙ", "ВСЕГО СПИСАНИЙ",
        "900 www", "ул. Вавилова", "Заказано в", "РОССИЙСКИЙ РУБЛЬ",
        "Номер счёта", "Дата открытия", "ПИРОЖКОВА", "Итого по",
    )

    def parse(self, file_path: Path) -> pd.DataFrame:
        logger.info(f"[Sber] Парсинг: {file_path.name}")
        all_lines: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_lines.extend(text.split("\n"))
        rows = self._parse_lines(all_lines)
        df = _rows_to_df(rows)
        logger.info(
            f"[Sber] {len(df)} операций | "
            f"Приход: {df['amount_in'].sum():,.0f} | "
            f"Расход: {df['amount_out'].sum():,.0f}"
        )
        return df

    def _parse_lines(self, lines: List[str]) -> List[Optional[dict]]:
        rows = []
        current: Optional[dict] = None

        for line in lines:
            m = self._MAIN_RE.match(line)
            if m:
                if current:
                    rows.append(self._finalize(current))
                date_str, time_str, auth, category, amount_raw, balance_raw = m.groups()
                # Признак дохода: '+' в начале суммы
                amount_str = amount_raw.strip()
                is_income = amount_str.startswith("+")
                amount_abs = _parse_ru_amount(amount_str.lstrip("+"))
                signed = amount_abs if is_income else -amount_abs
                current = {
                    "date": date_str,
                    "auth": auth,
                    "category": category.strip(),
                    "signed": signed,
                    "desc_lines": [],
                }
            elif current is not None:
                stripped = line.strip()
                if not stripped or self._is_header(line):
                    continue
                if self._PROC_DATE_RE.match(line):
                    # Строка "дата обработки + описание": убираем дату из начала
                    desc_part = re.sub(r"^\d{2}\.\d{2}\.\d{4}\s*", "", line).strip()
                    if desc_part:
                        current["desc_lines"].append(desc_part)
                else:
                    current["desc_lines"].append(stripped)

        if current:
            rows.append(self._finalize(current))
        return rows

    def _finalize(self, cur: dict) -> Optional[dict]:
        desc_raw = " ".join(cur["desc_lines"]).strip()
        # Убираем суффикс "Операция по карте/счету ****NNNN"
        desc_clean = re.sub(
            r"\.?\s*Операция\s+по\s+(?:карте|счету)\s+\*+\d+.*$",
            "", desc_raw, flags=re.IGNORECASE
        ).strip()
        # Убираем ". по карте ****NNNN"
        desc_clean = re.sub(r"\.\s+по\s+карте\s+\*+\d+.*$", "", desc_clean).strip()
        counterparty = self._extract_counterparty(desc_clean, cur["category"])
        purpose = f"{cur['category']} | {desc_raw}" if desc_raw else cur["category"]
        return _make_row(cur["date"], cur["auth"], counterparty, purpose, cur["signed"])

    def _extract_counterparty(self, desc_clean: str, category: str) -> str:
        if not desc_clean:
            return category[:100]
        # Убираем " RUS" суффикс
        cp = re.sub(r"\s+RUS\.?\s*$", "", desc_clean).strip()
        if cp:
            return cp[:100]
        return category[:100]

    def _is_header(self, line: str) -> bool:
        return any(kw in line for kw in self._HEADER_KEYWORDS)


# ─── Т-Банк ──────────────────────────────────────────────────────────────────

class TBankParser:
    """
    Парсер PDF справки о движении средств Т-Банка (Тинькофф).

    Формат (2+ строк на транзакцию):
      Строка 1: DD.MM.YYYY DD.MM.YYYY [-+]AMOUNT ₽ [-+]AMOUNT ₽ DESCRIPTION CARD
      Строка 2: HH:MM HH:MM DESCRIPTION_CONTINUATION
      (строк 3+ при длинном описании)

    Сумма берётся из 4-го поля (в валюте карты = RUB).
    Признак дохода: знак '+' в начале суммы.
    """

    # Строка транзакции: две даты → подписанная сумма с ₽ → описание → 4-значный номер карты
    _TX_RE = re.compile(
        r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}\.\d{2}\.\d{4})\s+"
        r"([-+]\d[\d\s]*\.\d{2})\s*₽\s+"
        r"([-+]\d[\d\s]*\.\d{2})\s*₽\s+"
        r"(.*?)\s+(\d{4})\s*$"
    )
    # Строка времени (продолжение): HH:MM HH:MM ...
    _TIME_RE = re.compile(r"^\d{2}:\d{2}\s+\d{2}:\d{2}")

    _HEADER_KEYWORDS = (
        "Дата и время", "Дата списания", "Сумма в валюте", "Описание операции",
        "ТБАНК", "РОССИЯ, 127287", "ТЕЛ.:", "TBANK.RU", "Справка о движении",
        "О продукте", "Дата заключения", "Номер договора", "Номер лицевого",
        "Сумма доступного", "Движение средств за период", "АО «ТБАНК»",
        "Пирожкова Наталья", "Адрес места жительства",
    )
    # Строки, состоящие только из служебных слов заголовка
    _HEADER_SOLO = frozenset(["операции", "карты", "списания", "Номер"])

    def parse(self, file_path: Path) -> pd.DataFrame:
        logger.info(f"[TBank] Парсинг: {file_path.name}")
        all_lines: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_lines.extend(text.split("\n"))
        rows = self._parse_lines(all_lines)
        df = _rows_to_df(rows)
        logger.info(
            f"[TBank] {len(df)} операций | "
            f"Приход: {df['amount_in'].sum():,.0f} | "
            f"Расход: {df['amount_out'].sum():,.0f}"
        )
        return df

    def _parse_lines(self, lines: List[str]) -> List[Optional[dict]]:
        rows = []
        current: Optional[dict] = None

        for line in lines:
            m = self._TX_RE.match(line)
            if m:
                if current:
                    rows.append(self._finalize(current))
                op_date, proc_date, amount_cur, amount_card, desc_part, card = m.groups()
                # amount_card — сумма в валюте карты (RUB)
                signed = _parse_rub_amount(amount_card.strip())
                current = {
                    "date": op_date,
                    "card": card,
                    "signed": signed,
                    "desc_parts": [desc_part.strip()] if desc_part.strip() else [],
                }
            elif current is not None:
                stripped = line.strip()
                if not stripped or self._is_header(line, stripped):
                    continue
                if self._TIME_RE.match(line):
                    # Убираем два времени из начала, берём остаток (описание)
                    extra = re.sub(r"^\d{2}:\d{2}\s+\d{2}:\d{2}\s*", "", line).strip()
                    if extra:
                        current["desc_parts"].append(extra)
                else:
                    current["desc_parts"].append(stripped)

        if current:
            rows.append(self._finalize(current))
        return rows

    def _finalize(self, cur: dict) -> Optional[dict]:
        desc = " ".join(cur["desc_parts"]).strip() or "Операция по карте"
        counterparty = self._extract_counterparty(desc)
        purpose = f"{desc} (карта *{cur['card']})"
        return _make_row(cur["date"], "", counterparty, purpose, cur["signed"])

    def _extract_counterparty(self, desc: str) -> str:
        # "Оплата в MERCHANT" / "Оплата услуг MERCHANT"
        m = re.search(r"Оплата\s+(?:в|услуг)\s+(.+)", desc)
        if m:
            cp = m.group(1)
            # Убираем географические хвосты (RUS, город и т.п.)
            cp = re.sub(r"\s+(?:RUS|RU)\s*$", "", cp).strip()
            cp = re.sub(r"\s+(?:Kukushtan|Platoshino|Perm|Shalya|Ekaterinburg|MOSKVA)\b.*$", "", cp).strip()
            # Убираем числовые коды магазинов (например "4177" в "PYATEROCHKA 4177")
            cp = re.sub(r"\s+\d{3,6}\s*$", "", cp).strip()
            return cp[:80]
        # "перевод по номеру телефона +7..."
        m = re.search(r"перевод\s+по\s+номеру\s+телефона\s+(\+?\d+)", desc, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # "Банковский перевод. INSTITUTION"
        m = re.search(r"Банковский\s+перевод\.\s+(.+)", desc, re.IGNORECASE)
        if m:
            return re.sub(r'["«»]', "", m.group(1)).strip()[:80]
        # Внутренний перевод
        if re.search(r"Внутренний\s+перевод", desc, re.IGNORECASE):
            return "Т-Банк (внутр. перевод)"
        # Пополнение через СБП
        if re.search(r"Систем[аы]\s+быстрых\s+платежей|Пополнение", desc, re.IGNORECASE):
            return "СБП (пополнение)"
        return desc[:80]

    def _is_header(self, line: str, stripped: str) -> bool:
        if stripped in self._HEADER_SOLO:
            return True
        return any(kw in line for kw in self._HEADER_KEYWORDS)


# ─── Определение банка и единая точка входа ──────────────────────────────────

PDF_PARSERS: Dict[str, type] = {
    "alfa":  AlfaBankParser,
    "vtb":   VTBParser,
    "sber":  SberbankParser,
    "tbank": TBankParser,
}

# Паттерны для определения банка по содержимому PDF
_BANK_PATTERNS: Dict[str, re.Pattern] = {
    "alfa":  re.compile(r"АО\s*[«\"]?\s*АЛЬФА.?БАНК|Альфа.?Банк|AO .ALFA.BANK", re.IGNORECASE),
    "vtb":   re.compile(r"\bВТБ\b|Банк ВТБ|\bVTB\b", re.IGNORECASE),
    "sber":  re.compile(r"Сбербанк|СБЕРБАНК|sberbank\.ru|ул\.\s*Вавилова", re.IGNORECASE),
    "tbank": re.compile(r"ТБАНК|T.BANK|TBANK\.RU|Тинькофф|TINKOFF", re.IGNORECASE),
}


def detect_pdf_bank(file_path: Path) -> str:
    """
    Определяет банк по имени файла, затем по содержимому первых 2 страниц.

    Returns:
        'alfa' | 'vtb' | 'sber' | 'tbank'

    Raises:
        ValueError если банк не определён.
    """
    # Быстрый поиск по имени файла
    stem = file_path.stem.lower()
    for bank, aliases in {
        "alfa":  ("альфа", "alfa", "alphabank"),
        "vtb":   ("втб", "vtb"),
        "sber":  ("сбер", "sber", "sberbank"),
        "tbank": ("тинькофф", "тбанк", "tbank", "t-банк", "t_банк"),
    }.items():
        if any(alias in stem for alias in aliases):
            logger.debug(f"Банк определён по имени файла: {bank}")
            return bank

    # Определение по содержимому
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "".join(
                (page.extract_text() or "")
                for page in pdf.pages[:2]
            )
    except Exception as e:
        raise ValueError(f"Не удалось открыть PDF {file_path.name}: {e}") from e

    for bank, pattern in _BANK_PATTERNS.items():
        if pattern.search(text):
            logger.debug(f"Банк определён по содержимому: {bank}")
            return bank

    raise ValueError(
        f"Не удалось определить банк для '{file_path.name}'. "
        f"Укажите --bank явно. Поддерживаются: {list(PDF_PARSERS)}"
    )


def parse_personal_pdf(file_path: Path, bank: str = "auto") -> pd.DataFrame:
    """
    Единая точка входа: парсинг PDF выписки личного счёта.

    Args:
        file_path: путь к PDF файлу
        bank: 'alfa' | 'vtb' | 'sber' | 'tbank' | 'auto'

    Returns:
        Нормализованный DataFrame (схема NORMALIZED_COLUMNS)
    """
    if bank == "auto":
        bank = detect_pdf_bank(file_path)
    if bank not in PDF_PARSERS:
        raise ValueError(f"Неизвестный банк: {bank!r}. Поддерживаются: {list(PDF_PARSERS)}")
    return PDF_PARSERS[bank]().parse(file_path)
