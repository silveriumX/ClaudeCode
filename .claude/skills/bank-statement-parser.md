# Bank Statement Parser

> Парсинг банковских выписок в нормализованные записи для единого финансового журнала.
> Поддерживает Модульбанк (1C, HTML, Excel). Расширяемый для WB Банк, Озон Банк, Сбер, Т-Бизнес.

---

## Когда использовать

- Нужно распарсить выписку из банка в Python-словари/DataFrame
- Разрабатываешь импорт банковских транзакций в Google Sheets
- Добавляешь поддержку нового банка в систему

---

## Поддерживаемые форматы

| Банк | 1C (.txt) | HTML | Excel | CSV |
|------|-----------|------|-------|-----|
| Модульбанк | ✅ Лучший | ✅ | ✅ | — |
| Сбербанк | — | — | ✅ | ✅ |
| Т-Бизнес (Тинькофф) | — | — | ✅ | ✅ |
| WB Банк | — | — | ✅ (ожидается) | — |
| Озон Банк | — | — | ✅ (ожидается) | — |

---

## Нормализованная структура транзакции

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Literal

@dataclass
class BankTransaction:
    # Идентификация
    doc_number: str              # Номер документа/платёжного поручения
    date: date                   # Дата операции

    # Деньги
    amount: Decimal              # Сумма (всегда положительная)
    currency: str                # RUB, USD, EUR
    direction: Literal["IN", "OUT"]  # Приход или расход

    # Контрагент
    counterparty_name: str       # Название организации/ФИО
    counterparty_inn: Optional[str]   # ИНН
    counterparty_kpp: Optional[str]   # КПП
    counterparty_bank: Optional[str]  # Банк контрагента
    counterparty_bic: Optional[str]   # БИК банка контрагента
    counterparty_account: Optional[str]  # Счёт контрагента

    # Назначение
    purpose: str                 # Назначение платежа (полный текст)

    # Метаданные счёта
    account_number: str          # Номер нашего р/с
    account_holder: str          # Владелец счёта (ИП/ООО)
    bank_name: str               # Наш банк

    # Служебные
    source_file: str             # Имя файла-источника
    raw_operation_type: Optional[str]  # Оригинальный тип операции из банка
```

---

## Парсер 1C формата (Модульбанк)

```python
from pathlib import Path
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Literal
import logging
import re

logger = logging.getLogger(__name__)

# Кодировки для попытки чтения 1C файлов
# ВАЖНО: Модульбанк выгружает 1C файлы в Windows-1251, НЕ UTF-8
_1C_ENCODINGS = ["windows-1251", "utf-8", "cp866"]


def parse_1c_file(file_path: Path) -> dict:
    """
    Парсить файл формата 1C ClientBank Exchange (v1.03).

    Args:
        file_path: Путь к .txt файлу

    Returns:
        Словарь с ключами:
          - 'account': метаданные счёта (номер, сальдо, период)
          - 'transactions': List[dict] с полями транзакции

    Raises:
        ValueError: Если файл не является валидным 1C ClientBank Exchange
        UnicodeDecodeError: Если не удалось определить кодировку
    """
    content = _read_with_encoding(file_path, _1C_ENCODINGS)

    lines = content.splitlines()
    if not lines or lines[0].strip() != "1CClientBankExchange":
        raise ValueError(f"Файл {file_path.name} не является 1C ClientBank Exchange")

    result = {"account": {}, "transactions": []}
    current_block = None
    current_tx = {}

    for line in lines:
        line = line.strip()

        # Маркеры блоков
        if line == "СчетОтчет":
            current_block = "account"
            continue
        elif line == "КонецСчетОтчет":
            current_block = None
            continue
        elif line == "Платеж":
            if current_tx:
                result["transactions"].append(current_tx)
            current_tx = {}
            current_block = "payment"
            continue
        elif line == "КонецПлатеж":
            if current_tx:
                result["transactions"].append(current_tx)
            current_tx = {}
            current_block = None
            continue
        elif line in ("КонецФайла", ""):
            continue

        # Парсим key=value
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if current_block == "account":
            result["account"][key] = value
        elif current_block == "payment":
            current_tx[key] = value

    # Финальная транзакция если не закрыта маркером
    if current_tx:
        result["transactions"].append(current_tx)

    return result


def normalize_1c_transactions(
    raw: dict,
    source_file: str
) -> tuple[dict, List[BankTransaction]]:
    """
    Нормализовать сырые данные из parse_1c_file в BankTransaction объекты.

    Returns:
        (account_meta, transactions)
        account_meta содержит: account_number, holder, bank, opening_balance,
                               total_in, total_out, closing_balance, period_start, period_end
    """
    acc = raw["account"]

    account_meta = {
        "account_number": acc.get("РасчетныйСчет", ""),
        "holder": "",          # В 1C формате нет имени держателя — берём из HTML/Excel
        "bank": "Модульбанк",  # Определяем по файлу
        "opening_balance": _parse_decimal(acc.get("ОстатокНачальный", "0")),
        "closing_balance": _parse_decimal(acc.get("ОстатокКонечный", "0")),
        "total_in": _parse_decimal(acc.get("ОборотПриход", "0")),
        "total_out": _parse_decimal(acc.get("ОборотРасход", "0")),
        "period_start": _parse_date(acc.get("ДатаНачала", "")),
        "period_end": _parse_date(acc.get("ДатаОкончания", "")),
    }

    transactions = []
    for raw_tx in raw["transactions"]:
        try:
            tx = _normalize_1c_tx(raw_tx, account_meta, source_file)
            transactions.append(tx)
        except Exception as e:
            logger.warning(f"Пропуск транзакции {raw_tx.get('НомерДокумента', '?')}: {e}")

    logger.info(
        f"Распарсено {len(transactions)} транзакций из {source_file} "
        f"(приход: {account_meta['total_in']}, расход: {account_meta['total_out']})"
    )
    return account_meta, transactions


def _normalize_1c_tx(
    raw_tx: dict,
    account_meta: dict,
    source_file: str
) -> BankTransaction:
    """Нормализовать одну транзакцию из 1C формата."""
    operation_type = raw_tx.get("НазваниеОперации", "").lower()

    # Определяем направление по типу операции
    if "приход" in operation_type or "входящий" in operation_type:
        direction = "IN"
    elif "расход" in operation_type or "исходящий" in operation_type or "списание" in operation_type:
        direction = "OUT"
    else:
        # Fallback: определяем по контрагенту (если наш счёт — приход)
        direction = "IN" if raw_tx.get("РасчетныйСчетКонтрагента") == account_meta["account_number"] else "OUT"

    # ИНН и КПП контрагента
    inn_raw = raw_tx.get("ИННКонтрагента", "")
    inn, kpp = _split_inn_kpp(inn_raw)

    return BankTransaction(
        doc_number=raw_tx.get("НомерДокумента", ""),
        date=_parse_date(raw_tx.get("Дата", "")),
        amount=_parse_decimal(raw_tx.get("Сумма", "0")),
        currency="RUB",
        direction=direction,
        counterparty_name=raw_tx.get("НазваниеКонтрагента", ""),
        counterparty_inn=inn or None,
        counterparty_kpp=kpp or None,
        counterparty_bank=raw_tx.get("БанкКонтрагента", "") or None,
        counterparty_bic=raw_tx.get("БИКБанкаКонтрагента", "") or None,
        counterparty_account=raw_tx.get("РасчетныйСчетКонтрагента", "") or None,
        purpose=raw_tx.get("НазначениеПлатежа", raw_tx.get("ОписаниеОперации", "")),
        account_number=account_meta["account_number"],
        account_holder=account_meta.get("holder", ""),
        bank_name=account_meta.get("bank", "Модульбанк"),
        source_file=source_file,
        raw_operation_type=raw_tx.get("НазваниеОперации", ""),
    )


# --- Парсер HTML формата (Модульбанк) ---

def parse_modulbank_html(file_path: Path) -> tuple[dict, List[BankTransaction]]:
    """
    Парсить HTML выписку Модульбанка.
    Используй как fallback если 1C файл недоступен.

    Структура HTML:
    - <flex class="total balance"> — сальдо входящее
    - <row><flex> — строки транзакций (9 div элементов)
    - <flex class="total"> — итоговые обороты
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("pip install beautifulsoup4 lxml")

    content = _read_with_encoding(file_path, ["utf-8", "windows-1251"])
    soup = BeautifulSoup(content, "lxml")

    # Метаданные счёта
    account_meta = _parse_modulbank_html_header(soup)

    # Транзакции
    transactions = []
    rows = soup.find_all("row")
    for row in rows:
        flex = row.find("flex")
        if not flex:
            continue
        divs = flex.find_all("div", recursive=False)
        if len(divs) < 8:
            continue

        try:
            tx = _parse_modulbank_html_row(divs, account_meta, file_path.name)
            if tx:
                transactions.append(tx)
        except Exception as e:
            logger.debug(f"Пропуск строки HTML: {e}")

    logger.info(f"HTML: распарсено {len(transactions)} транзакций")
    return account_meta, transactions


def _parse_modulbank_html_header(soup) -> dict:
    """Извлечь метаданные счёта из заголовка HTML выписки."""
    text = soup.get_text(" ", strip=True)

    # Имя держателя счёта
    holder_match = re.search(
        r"(Индивидуальный предприниматель|ООО|АО|ИП)\s+(.+?)\s+(?:БИК|Дата)",
        text
    )
    holder = holder_match.group(0).split("БИК")[0].strip() if holder_match else ""

    # Номер счёта
    account_match = re.search(r"Расчётный счёт №\s*(\d+)", text)
    account_number = account_match.group(1) if account_match else ""

    # Сальдо входящее
    balance_match = re.search(
        r"Средства на начало периода.*?:\s*([\d\s]+,\d+)", text
    )
    opening_balance = _parse_decimal(balance_match.group(1)) if balance_match else Decimal("0")

    return {
        "account_number": account_number,
        "holder": holder,
        "bank": "Модульбанк",
        "opening_balance": opening_balance,
    }


def _parse_modulbank_html_row(divs: list, account_meta: dict, source_file: str):
    """Парсить одну строку транзакции из HTML."""
    # Структура: [doc_num, date, counterparty, inn_kpp, bank, bic, account, purpose, stretch_div]
    doc_number = divs[0].get_text(strip=True)
    date_str = divs[1].get_text(strip=True)
    counterparty = divs[2].get_text(strip=True)
    inn_kpp = divs[3].get_text(strip=True).replace("\xa0", "").strip()
    counterparty_bank = divs[4].get_text(strip=True)
    bic = divs[5].get_text(strip=True)
    counterparty_account = divs[6].get_text(strip=True)
    purpose = divs[7].get_text(strip=True)

    if not doc_number or not date_str:
        return None

    # Суммы из stretch div
    stretch = divs[8] if len(divs) > 8 else None
    amount_in = Decimal("0")
    amount_out = Decimal("0")
    if stretch:
        amount_divs = stretch.find_all("div", recursive=False)
        if len(amount_divs) >= 4:
            in_text = amount_divs[0].get_text(strip=True).replace("\xa0", "")
            out_text = amount_divs[2].get_text(strip=True).replace("\xa0", "")
            amount_in = _parse_decimal(in_text)
            amount_out = _parse_decimal(out_text)

    if amount_in == 0 and amount_out == 0:
        return None

    direction = "IN" if amount_in > 0 else "OUT"
    amount = amount_in if direction == "IN" else amount_out

    inn, kpp = _split_inn_kpp(inn_kpp)

    return BankTransaction(
        doc_number=doc_number,
        date=_parse_date(date_str),
        amount=amount,
        currency="RUB",
        direction=direction,
        counterparty_name=counterparty,
        counterparty_inn=inn or None,
        counterparty_kpp=kpp or None,
        counterparty_bank=counterparty_bank or None,
        counterparty_bic=bic or None,
        counterparty_account=counterparty_account or None,
        purpose=purpose,
        account_number=account_meta["account_number"],
        account_holder=account_meta.get("holder", ""),
        bank_name="Модульбанк",
        source_file=source_file,
        raw_operation_type=None,
    )


# --- Детектор банка и формата ---

def detect_bank_and_format(file_path: Path) -> tuple[str, str]:
    """
    Автоматически определить банк и формат файла.

    Returns:
        (bank_name, format) где format = '1c' | 'html' | 'excel' | 'csv'

    Examples:
        detect_bank_and_format(Path("kl_to_1c.txt")) → ("Модульбанк", "1c")
        detect_bank_and_format(Path("statement.html")) → ("Модульбанк", "html")
    """
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        content = _read_with_encoding(file_path, _1C_ENCODINGS, max_bytes=100)
        if "1CClientBankExchange" in content:
            return ("Модульбанк", "1c")
        return ("Неизвестный", "txt")

    if suffix == ".html":
        content = _read_with_encoding(file_path, ["utf-8"], max_bytes=2000)
        if "МОДУЛЬБАНК" in content.upper() or "modulbank" in content.lower():
            return ("Модульбанк", "html")
        return ("Неизвестный", "html")

    if suffix in (".xlsx", ".xls"):
        # По имени файла пытаемся угадать банк
        name = file_path.name.upper()
        if "MODULBANK" in name or "МОДУЛЬ" in name:
            return ("Модульбанк", "excel")
        if "SBERBANK" in name or "СБЕР" in name:
            return ("Сбербанк", "excel")
        if "TINKOFF" in name or "TBANK" in name or "ТИНЬКОФФ" in name:
            return ("Т-Бизнес", "excel")
        return ("Неизвестный", "excel")

    if suffix == ".csv":
        return ("Неизвестный", "csv")

    return ("Неизвестный", suffix.lstrip("."))


def parse_statement(file_path: Path) -> tuple[dict, List[BankTransaction]]:
    """
    Универсальная точка входа. Автоматически определяет банк и формат.

    Usage:
        account_meta, transactions = parse_statement(Path("выписка.txt"))
        for tx in transactions:
            print(tx.date, tx.direction, tx.amount, tx.counterparty_name)
    """
    bank, fmt = detect_bank_and_format(file_path)
    logger.info(f"Определён банк: {bank}, формат: {fmt}")

    if bank == "Модульбанк":
        if fmt == "1c":
            raw = parse_1c_file(file_path)
            return normalize_1c_transactions(raw, file_path.name)
        elif fmt == "html":
            return parse_modulbank_html(file_path)
        elif fmt == "excel":
            return parse_modulbank_excel(file_path)

    raise NotImplementedError(
        f"Парсер для банка '{bank}' формат '{fmt}' ещё не реализован. "
        f"Добавь примеры выписок в Projects/BusinessBank/ и реализуй парсер."
    )


# --- Парсер Excel формата (Модульбанк) ---

def parse_modulbank_excel(file_path: Path) -> tuple[dict, List[BankTransaction]]:
    """
    Парсить Excel выписку Модульбанка.
    Структура аналогична HTML: строки с 9 колонками.
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("pip install openpyxl")

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    account_meta = {"bank": "Модульбанк", "account_number": "", "holder": "", "opening_balance": Decimal("0")}
    transactions = []
    header_found = False

    for row in ws.iter_rows(values_only=True):
        row_text = " ".join(str(c or "") for c in row)

        # Ищем строку с заголовками колонок
        if "Назначение" in row_text and "Контрагент" in row_text:
            header_found = True
            continue

        # Ищем метаданные счёта в начале файла
        if not header_found:
            if "Расчётный счёт" in row_text or "Расчетный счет" in row_text:
                m = re.search(r"(\d{20})", row_text)
                if m:
                    account_meta["account_number"] = m.group(1)
            if "сальдо входящее" in row_text.lower():
                m = re.search(r"([\d\s]+[,\.]\d+)", row_text)
                if m:
                    account_meta["opening_balance"] = _parse_decimal(m.group(1))
            continue

        # Пропускаем итоговые строки
        if "Итого" in row_text or "Средства на конец" in row_text:
            break

        cells = list(row)
        if len(cells) < 8:
            continue

        doc_number = str(cells[0] or "").strip()
        date_val = cells[1]
        counterparty = str(cells[2] or "").strip()
        inn_kpp = str(cells[3] or "").strip()
        counterparty_bank = str(cells[4] or "").strip()
        bic = str(cells[5] or "").strip()
        c_account = str(cells[6] or "").strip()
        purpose = str(cells[7] or "").strip()

        if not doc_number or not date_val:
            continue

        # Суммы (колонки 8-11 обычно: приход, приход_нац, расход, расход_нац)
        amount_in = _parse_decimal(str(cells[8] or "0")) if len(cells) > 8 else Decimal("0")
        amount_out = _parse_decimal(str(cells[10] or "0")) if len(cells) > 10 else Decimal("0")

        if amount_in == 0 and amount_out == 0:
            continue

        direction = "IN" if amount_in > 0 else "OUT"
        amount = amount_in if direction == "IN" else amount_out

        # Дата из Excel может быть datetime объектом
        if hasattr(date_val, "date"):
            tx_date = date_val.date()
        else:
            tx_date = _parse_date(str(date_val))

        inn, kpp = _split_inn_kpp(inn_kpp)

        transactions.append(BankTransaction(
            doc_number=doc_number,
            date=tx_date,
            amount=amount,
            currency="RUB",
            direction=direction,
            counterparty_name=counterparty,
            counterparty_inn=inn or None,
            counterparty_kpp=kpp or None,
            counterparty_bank=counterparty_bank or None,
            counterparty_bic=bic or None,
            counterparty_account=c_account or None,
            purpose=purpose,
            account_number=account_meta["account_number"],
            account_holder=account_meta.get("holder", ""),
            bank_name="Модульбанк",
            source_file=file_path.name,
            raw_operation_type=None,
        ))

    wb.close()
    logger.info(f"Excel: распарсено {len(transactions)} транзакций")
    return account_meta, transactions


# --- Вспомогательные функции ---

def _read_with_encoding(
    file_path: Path,
    encodings: list[str],
    max_bytes: Optional[int] = None
) -> str:
    """Прочитать файл пробуя разные кодировки."""
    for enc in encodings:
        try:
            if max_bytes:
                with open(file_path, "rb") as f:
                    raw = f.read(max_bytes)
                return raw.decode(enc, errors="strict")
            else:
                return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise UnicodeDecodeError(
        f"Не удалось прочитать {file_path.name} ни одной из кодировок: {encodings}"
    )


def _parse_date(date_str: str) -> date:
    """Парсить дату из форматов DD.MM.YYYY или YYYY-MM-DD."""
    date_str = date_str.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    logger.warning(f"Неизвестный формат даты: '{date_str}', используется сегодня")
    return date.today()


def _parse_decimal(value: str) -> Decimal:
    """
    Парсить число из русского формата.
    Обрабатывает: '130 050 493,70', '49499.53', '—', '', None
    """
    if not value or value in ("—", "-", "\u2014", "\xa0"):
        return Decimal("0")
    # Убираем пробелы (разделитель тысяч) и неразрывные пробелы
    cleaned = value.replace(" ", "").replace("\xa0", "").replace(",", ".")
    # Убираем всё кроме цифр и точки
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    if not cleaned:
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _split_inn_kpp(inn_kpp: str) -> tuple[str, str]:
    """
    Разделить строку 'ИНН, КПП' или 'ИНН/КПП'.
    Например: '7727406020, 770801001' → ('7727406020', '770801001')
    """
    if not inn_kpp:
        return "", ""
    parts = re.split(r"[,/\s]+", inn_kpp.strip())
    inn = parts[0].strip() if parts else ""
    kpp = parts[1].strip() if len(parts) > 1 else ""
    return inn, kpp
```

---

## Добавление нового банка

### Шаблон для нового банка:

```python
# 1. Добавь определение в detect_bank_and_format()
if suffix == ".csv":
    content = _read_with_encoding(file_path, ["utf-8", "windows-1251"], max_bytes=500)
    if "Тинькофф" in content or "Т-Банк" in content:
        return ("Т-Бизнес", "csv")

# 2. Добавь парсер
def parse_tbank_csv(file_path: Path) -> tuple[dict, List[BankTransaction]]:
    """Парсить CSV выписку Т-Бизнес."""
    import csv
    # Структура Т-Бизнес CSV:
    # Дата операции;Дата платежа;Номер карты;Статус;Операция;Сумма платежа;Валюта платежа;
    # Кэшбэк;Категория;MCC;Описание;Бонусы (начислено);Бонусы (списано);Округление
    ...

# 3. Добавь в parse_statement()
if bank == "Т-Бизнес" and fmt == "csv":
    return parse_tbank_csv(file_path)
```

### Форматы выписок основных банков:

| Банк | Лучший формат | Кодировка | Разделитель |
|------|--------------|-----------|-------------|
| Сбербанк | Excel/CSV | UTF-8 | ; |
| Т-Бизнес | CSV | UTF-8 | ; |
| Альфа-Банк | 1C / CSV | Windows-1251 | ; |
| WB Банк | Excel (ожидается) | UTF-8 | — |
| Озон Банк | Excel (ожидается) | UTF-8 | — |

---

## Установка зависимостей

```bash
pip install beautifulsoup4 lxml openpyxl
```

---

## Быстрый тест

```python
from pathlib import Path
from bank_statement_parser import parse_statement

# Тест на выписке Модульбанка
account, txs = parse_statement(Path("kl_to_1c.txt"))
print(f"Счёт: {account['account_number']}")
print(f"Транзакций: {len(txs)}")
print(f"Приход: {account['total_in']:,.2f}")
print(f"Расход: {account['total_out']:,.2f}")

# Фильтр расходов
expenses = [t for t in txs if t.direction == "OUT"]
taxes = [t for t in expenses if "казначейство" in t.counterparty_name.lower()]
print(f"Налоговых платежей: {len(taxes)}, сумма: {sum(t.amount for t in taxes):,.2f}")
```

---

## Связанные скиллы

- `/bank-import-bot` — Telegram-бот для загрузки выписок (использует этот парсер)
- `/transaction-categorizer` — Категоризация распарсенных транзакций
- `/financial-journal-schema` — Схема Google Sheets куда записываются результаты
