"""
Парсер банковских выписок.

Поддерживаемые форматы:
- Модульбанк XLSX (формат iSimpleBank)

Возвращает нормализованный DataFrame с единой схемой колонок
независимо от банка-источника.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# Единая схема выходного DataFrame
NORMALIZED_COLUMNS = [
    "date",           # дата операции (datetime)
    "doc_num",        # номер документа
    "counterparty",   # контрагент (название)
    "inn",            # ИНН/КПП контрагента
    "bank",           # банк контрагента
    "bic",            # БИК банка контрагента
    "account",        # счёт корреспондента
    "purpose",        # назначение платежа
    "amount_in",      # приход (0 если нет)
    "amount_out",     # расход (0 если нет)
    "is_income",      # True = приход, False = расход
    "amount",         # абсолютная сумма операции
]


class ModulbankParser:
    """
    Парсер выписки Модульбанка в XLSX формате.

    Структура файла:
    - Строки 0-5: метаданные (номер счёта, период, остаток)
    - Строка 6-8: заголовки (могут занимать 2 строки из-за merged cells)
    - Строка 9+: данные транзакций
    """

    # Маппинг: паттерн в названии колонки → стандартное имя
    _COLUMN_MAP = [
        (re.compile(r'номер.*документ|документ.*номер', re.IGNORECASE),        "doc_num"),
        (re.compile(r'^дата', re.IGNORECASE),                                  "date"),
        (re.compile(r'контрагент', re.IGNORECASE),                             "counterparty"),
        (re.compile(r'инн.*кпп|кпп.*инн|инн$', re.IGNORECASE),                "inn"),
        (re.compile(r'банк.*контраг|банк корр', re.IGNORECASE),                "bank"),
        (re.compile(r'бик', re.IGNORECASE),                                    "bic"),
        (re.compile(r'счет.*корр|счёт.*корр|корр.*счет', re.IGNORECASE),       "account"),
        (re.compile(r'назначение', re.IGNORECASE),                             "purpose"),
        # Приход: берём первую колонку (без "нац.покрытия")
        (re.compile(r'^приход$', re.IGNORECASE),                               "amount_in"),
        # Расход: берём первую колонку (без "нац.покрытия")
        (re.compile(r'^расход$', re.IGNORECASE),                               "amount_out"),
    ]

    def parse(self, file_path: Path) -> pd.DataFrame:
        """
        Читает XLSX-выписку Модульбанка и возвращает нормализованный DataFrame.

        Args:
            file_path: путь к .xlsx файлу

        Returns:
            DataFrame с колонками из NORMALIZED_COLUMNS
        """
        logger.info(f"Парсинг выписки: {file_path.name}")

        raw_df = self._read_with_correct_header(file_path)
        df = self._clean_and_cast(raw_df)

        logger.info(
            f"Прочитано: {len(df)} операций | "
            f"Приход: {df['amount_in'].sum():,.0f} | "
            f"Расход: {df['amount_out'].sum():,.0f}"
        )
        return df

    # Паттерн даты DD.MM.YYYY для поиска первой строки данных
    _DATE_PATTERN = re.compile(r'^\d{2}\.\d{2}\.\d{4}$')

    def _read_with_correct_header(self, file_path: Path) -> pd.DataFrame:
        """
        Находит первую строку с данными (где второй столбец = дата DD.MM.YYYY).
        Использует позиционный маппинг колонок — работает независимо от кодировки.

        Модульбанк XLSX колонки (0-indexed):
          0=Номер документа, 1=Дата, 2=Контрагент, 3=ИНН/КПП,
          4=Банк, 5=БИК, 6=Счёт, 7=Назначение, 8=Приход, 9=Расход
        """
        probe = pd.read_excel(file_path, header=None, nrows=30)

        data_start_row = None
        for i, row in probe.iterrows():
            val = str(row.iloc[1]).strip()
            if self._DATE_PATTERN.match(val):
                data_start_row = i
                break

        if data_start_row is None:
            raise ValueError(
                f"Не найдены строки с данными в файле {file_path.name}. "
                "Убедитесь, что это выписка Модульбанка в формате XLSX."
            )

        # Читаем данные начиная со строки с датами
        df = pd.read_excel(file_path, header=None, skiprows=data_start_row)

        # Позиционный маппинг — обходит проблемы с кодировкой
        position_map = {
            0: "doc_num",
            1: "date",
            2: "counterparty",
            3: "inn",
            4: "bank",
            5: "bic",
            6: "account",
            7: "purpose",
            8: "amount_in",
            9: "amount_out",
        }
        df = df.rename(columns={
            i: position_map.get(i, f"col_{i}") for i in range(len(df.columns))
        })
        df = df.dropna(how="all")
        logger.debug(f"Данные начиная со строки {data_start_row}, прочитано {len(df)} строк")
        return df

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Переименовывает колонки по маппингу."""
        rename_map = {}
        used_targets: set[str] = set()

        for col in df.columns:
            col_str = str(col).strip()
            for pattern, target in self._COLUMN_MAP:
                if target in used_targets:
                    continue
                if pattern.search(col_str):
                    rename_map[col] = target
                    used_targets.add(target)
                    break

        df = df.rename(columns=rename_map)

        # Добавляем отсутствующие стандартные колонки как пустые
        for col in ["doc_num", "date", "counterparty", "inn", "bank",
                    "bic", "account", "purpose", "amount_in", "amount_out"]:
            if col not in df.columns:
                df[col] = None

        return df

    def _clean_and_cast(self, df: pd.DataFrame) -> pd.DataFrame:
        """Приводит типы данных и фильтрует мусорные строки."""
        # Дата
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        df = df[df["date"].notna()].copy()

        # Суммы
        df["amount_in"] = pd.to_numeric(df["amount_in"], errors="coerce").fillna(0)
        df["amount_out"] = pd.to_numeric(df["amount_out"], errors="coerce").fillna(0)

        # Строки должны иметь хоть какую-то сумму
        df = df[(df["amount_in"] > 0) | (df["amount_out"] > 0)].copy()

        # Производные колонки
        df["is_income"] = df["amount_in"] > df["amount_out"]
        df["amount"] = df.apply(
            lambda r: r["amount_in"] if r["is_income"] else r["amount_out"],
            axis=1,
        )

        # Строковые колонки — убираем NaN
        for col in ["doc_num", "counterparty", "inn", "bank", "bic", "account", "purpose"]:
            df[col] = df[col].fillna("").astype(str).str.strip()

        df = df.reset_index(drop=True)
        return df[NORMALIZED_COLUMNS]


def parse_statement(file_path: Path, bank: str = "auto") -> pd.DataFrame:
    """
    Единая точка входа для парсинга выписок разных банков.

    Args:
        file_path: путь к файлу выписки
        bank: 'modulbank' | 'auto' (автоопределение)

    Returns:
        Нормализованный DataFrame
    """
    if bank == "auto":
        bank = _detect_bank(file_path)

    parsers = {
        "modulbank": ModulbankParser,
        # Сюда добавлять парсеры других банков:
        # "tinkoff": TinkoffParser,
        # "sberbank": SberbankParser,
    }

    if bank not in parsers:
        raise ValueError(
            f"Неизвестный банк: '{bank}'. "
            f"Поддерживаются: {list(parsers.keys())}"
        )

    return parsers[bank]().parse(file_path)


def _detect_bank(file_path: Path) -> str:
    """Автоматически определяет банк по содержимому файла."""
    try:
        probe = pd.read_excel(file_path, header=None, nrows=10)
        content = " ".join(str(v) for v in probe.values.flatten() if pd.notna(v))
        if re.search(r'модульбанк|iSimpleBank|044525092', content, re.IGNORECASE):
            return "modulbank"
    except Exception:
        pass

    # По умолчанию пробуем Модульбанк
    logger.warning(f"Не удалось определить банк для {file_path.name}, пробуем modulbank")
    return "modulbank"
