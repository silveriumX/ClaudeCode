#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wb_detail_report.py — Парсер WB «Отчёт реализации» (детализированный).

Поддерживает два формата:
  - Еженедельный (81 колонка): «еженедельный» в имени файла
  - Ежедневный   (79 колонок): «ежедневный» в имени файла

Два типа данных:
  - Основной      (реальные продажи)
  - По выкупам    (самовыкупы)

Использование:
    from src.wb_detail_report import WbDetailParser

    parser = WbDetailParser()
    df = parser.parse(Path("Финансовые отчеты/09.02.-15.02. осн. еженедельный дет..xlsx"))
    summary = parser.summarize(df)
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ─── Схема ───────────────────────────────────────────────────────────────────

# Минимальный набор колонок — без них парсинг невозможен (нормализованные)
REQUIRED_COLS: set[str] = {
    "К перечислению Продавцу за реализованный Товар",
    "Вознаграждение с продаж до вычета услуг поверенного, без НДС",
    "Тип документа",
    "Обоснование для оплаты",
    "Дата продажи",
    "Артикул поставщика",
    "Код номенклатуры",
}

# Эталонный набор колонок — изменения = предупреждение
EXPECTED_DETAIL_COLS: set[str] = {
    "Артикул поставщика",
    "Код номенклатуры",
    "Название",
    "Предмет",
    "Бренд",
    "Дата заказа покупателем",
    "Дата продажи",
    "Тип документа",
    "Обоснование для оплаты",
    "Кол-во",
    "Цена розничная",
    "Цена розничная с учетом согласованной скидки",
    "Вайлдберриз реализовал Товар (Пр)",
    "Размер кВВ, %",
    "К перечислению Продавцу за реализованный Товар",
    "Вознаграждение с продаж до вычета услуг поверенного, без НДС",
    "Вознаграждение Вайлдберриз (ВВ), без НДС",
    "Услуги по доставке товара покупателю",
    "Возмещение за выдачу и возврат товаров на ПВЗ",
    "Хранение",
    "Удержания",
    "Операции на приемке",
    "Возмещение издержек по перевозке/по складским операциям с товаром",
    "Общая сумма штрафов",
    "Корректировка Вознаграждения Вайлдберриз (ВВ)",
    "Эквайринг/Комиссии за организацию платежей",
    "Компенсация скидки по программе лояльности",
    "Склад",
    "Страна",
    "Способы продажи и тип товара",
    "Srid",
}

# Финансовые колонки (нормализованные): логическое_имя → список вариантов в файле
_FIN_COL_ALIASES: Dict[str, list[str]] = {
    "payout":            ["К перечислению Продавцу за реализованный Товар"],
    "commission_gross":  ["Вознаграждение с продаж до вычета услуг поверенного, без НДС"],
    "commission_net":    ["Вознаграждение Вайлдберриз (ВВ), без НДС"],
    "logistics":         ["Услуги по доставке товара покупателю"],
    "pvz_service":       ["Возмещение за выдачу и возврат товаров на ПВЗ"],
    "storage":           ["Хранение"],
    "holds":             ["Удержания"],
    "acceptance":        ["Операции на приемке"],
    "logistics_reimb":   ["Возмещение издержек по перевозке/по складским операциям с товаром"],
    "fines":             ["Общая сумма штрафов"],
    "commission_corr":   ["Корректировка Вознаграждения Вайлдберриз (ВВ)"],
    "loyalty_comp":      ["Компенсация скидки по программе лояльности"],
    "acquiring":         ["Эквайринг/Комиссии за организацию платежей"],
}

# Типы «Обоснование для оплаты» которые несут деньги (Тип документа = Продажа/Возврат)
_SALE_REASONS = {"Продажа"}
_RETURN_REASONS = {"Возврат"}
_LOGISTICS_REASONS = {"Логистика", "Коррекция логистики", "Возмещение за выдачу и возврат товаров на ПВЗ"}
_STORAGE_REASONS = {"Хранение"}
_HOLD_REASONS = {"Удержание"}
_REIMB_REASONS = {"Возмещение издержек по перевозке/по складским операциям с товаром"}


# ─── Определение типа отчёта ──────────────────────────────────────────────────

def detect_report_type(file_path: Path) -> Tuple[str, str]:
    """
    Определить тип отчёта из имени файла.

    Returns:
        (freq, data_type) где:
            freq      = "weekly" | "daily"
            data_type = "основной" | "по_выкупам"
    """
    name_lower = file_path.name.lower()

    freq = "weekly" if "еженедельн" in name_lower else "daily"

    if "выкуп" in name_lower:
        data_type = "по_выкупам"
    else:
        data_type = "основной"

    return freq, data_type


# ─── Нормализация колонок ─────────────────────────────────────────────────────

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Убрать лишние пробелы из названий колонок."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    # Normalize double-space variants (weekly has "Размер  кВВ" with 2 spaces)
    df.columns = [re.sub(r" {2,}", " ", c) for c in df.columns]
    return df


def _resolve_fin_col(df: pd.DataFrame, logical: str) -> Optional[str]:
    """Вернуть фактическое название колонки для логического имени."""
    aliases = _FIN_COL_ALIASES.get(logical, [])
    col_set = set(df.columns)
    for alias in aliases:
        if alias in col_set:
            return alias
    return None


def _safe_sum(df: pd.DataFrame, logical: str) -> float:
    """Суммировать финансовую колонку (0.0 если колонки нет)."""
    col = _resolve_fin_col(df, logical)
    if col is None:
        return 0.0
    return float(df[col].fillna(0.0).sum())


# ─── Валидация схемы ──────────────────────────────────────────────────────────

class SchemaError(ValueError):
    """Структура файла не соответствует ожидаемой схеме."""


class DetailSchemaWarning:
    """Результат сравнения схемы детального отчёта с эталоном."""

    def __init__(self, added: set[str], removed: set[str]) -> None:
        self.added   = added    # новые колонки (не было в эталоне)
        self.removed = removed  # удалённые колонки (были в эталоне)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)

    def __str__(self) -> str:
        parts = []
        if self.removed:
            parts.append("Удалены колонки:\n" + "\n".join(f"  - {c}" for c in sorted(self.removed)))
        if self.added:
            parts.append("Новые колонки:\n" + "\n".join(f"  + {c}" for c in sorted(self.added)))
        return "\n".join(parts)


def validate_schema(df: pd.DataFrame) -> "DetailSchemaWarning":
    """
    Проверить схему детального отчёта.

    Raises:
        SchemaError: если обязательные колонки отсутствуют.

    Returns:
        DetailSchemaWarning с информацией об изменениях схемы (может быть пустым).
    """
    existing = set(df.columns)
    missing = REQUIRED_COLS - existing
    if missing:
        raise SchemaError(
            f"Отчёт реализации: отсутствуют колонки ({len(missing)} шт.):\n"
            + "\n".join(f"  - {c}" for c in sorted(missing))
        )

    added   = existing - EXPECTED_DETAIL_COLS
    removed = EXPECTED_DETAIL_COLS - existing
    warning = DetailSchemaWarning(added=added, removed=removed)

    if warning.has_changes:
        logger.warning("Схема детального отчёта изменилась!\n%s", warning)

    return warning


# ─── Парсер ───────────────────────────────────────────────────────────────────

class WbDetailParser:
    """
    Парсер WB «Отчёт реализации» (детализированный).

    Supports weekly (81 cols) and daily (79 cols) formats.
    Returns normalized DataFrame with key financial columns + metadata.
    """

    def parse(
        self,
        file_path: Path,
    ) -> tuple[pd.DataFrame, "DetailSchemaWarning"]:
        """
        Разобрать файл Отчёта реализации.

        Args:
            file_path: Путь к Excel-файлу (.xlsx)

        Returns:
            (DataFrame, DetailSchemaWarning) — данные и информация об изменениях схемы.
            Пустой DataFrame + пустое предупреждение при ошибке чтения.

        Raises:
            SchemaError: если структура файла не соответствует схеме.
        """
        _empty_warning = DetailSchemaWarning(added=set(), removed=set())

        try:
            raw = pd.read_excel(file_path, sheet_name=0, header=0)
        except Exception as exc:
            logger.error("Не удалось прочитать файл %s: %s", file_path.name, exc)
            return pd.DataFrame(), _empty_warning

        df = _normalize_columns(raw)
        schema_warning = validate_schema(df)

        freq, data_type = detect_report_type(file_path)

        # Нормализация дат
        for date_col in ("Дата заказа покупателем", "Дата продажи"):
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        # Добавить метаданные
        df["_file"]      = file_path.name
        df["_freq"]      = freq
        df["_data_type"] = data_type

        logger.info(
            "Разобран %s: %d строк, %s, %s",
            file_path.name, len(df), freq, data_type,
        )
        return df, schema_warning

    def summarize(self, df: pd.DataFrame) -> Dict:
        """
        Агрегировать P&L из разобранного DataFrame (один файл).

        Args:
            df: DataFrame из parse()

        Returns:
            dict с финансовыми итогами.
        """
        if df.empty:
            return {}

        reason_col = "Обоснование для оплаты"
        doctype_col = "Тип документа"
        payout_col = _resolve_fin_col(df, "payout") or "К перечислению Продавцу за реализованный Товар"

        # Суммы по Обоснованию
        reason_payout = (
            df.groupby(reason_col)[payout_col]
            .sum()
            .fillna(0.0)
            .to_dict()
        )

        gross_sales   = reason_payout.get("Продажа", 0.0)
        gross_returns = reason_payout.get("Возврат", 0.0)
        voluntary_ret = reason_payout.get("Добровольная компенсация при возврате", 0.0)
        net_payout    = float(df[payout_col].fillna(0.0).sum())

        # Количества по типу документа
        n_sales    = int((df[doctype_col] == "Продажа").sum())
        n_returns  = int((df[doctype_col] == "Возврат").sum())
        n_logistic = int(df[reason_col].isin(_LOGISTICS_REASONS).sum())
        n_storage  = int(df[reason_col].isin(_STORAGE_REASONS).sum())
        n_holds    = int(df[reason_col].isin(_HOLD_REASONS).sum())

        # Дата диапазон
        date_col = "Дата продажи" if "Дата продажи" in df.columns else None
        date_from = date_to = None
        if date_col:
            valid_dates = df[date_col].dropna()
            if not valid_dates.empty:
                date_from = valid_dates.min()
                date_to   = valid_dates.max()

        return {
            "file":              df["_file"].iloc[0] if "_file" in df.columns else "",
            "freq":              df["_freq"].iloc[0] if "_freq" in df.columns else "",
            "data_type":         df["_data_type"].iloc[0] if "_data_type" in df.columns else "",
            "date_from":         date_from,
            "date_to":           date_to,
            "n_rows":            len(df),
            "n_sales":           n_sales,
            "n_returns":         n_returns,
            "n_logistics":       n_logistic,
            "n_storage":         n_storage,
            "n_holds":           n_holds,
            # Ключевые суммы
            "gross_sales":       round(gross_sales, 2),
            "gross_returns":     round(gross_returns, 2),
            "voluntary_returns": round(voluntary_ret, 2),
            "net_payout":        round(net_payout, 2),
            # Расходы (из финансовых колонок)
            "commission_gross":  round(_safe_sum(df, "commission_gross"), 2),
            "commission_net":    round(_safe_sum(df, "commission_net"), 2),
            "logistics":         round(_safe_sum(df, "logistics"), 2),
            "pvz_service":       round(_safe_sum(df, "pvz_service"), 2),
            "storage":           round(_safe_sum(df, "storage"), 2),
            "holds":             round(_safe_sum(df, "holds"), 2),
            "acceptance":        round(_safe_sum(df, "acceptance"), 2),
            "logistics_reimb":   round(_safe_sum(df, "logistics_reimb"), 2),
            "fines":             round(_safe_sum(df, "fines"), 2),
            "commission_corr":   round(_safe_sum(df, "commission_corr"), 2),
            "loyalty_comp":      round(_safe_sum(df, "loyalty_comp"), 2),
            "acquiring":         round(_safe_sum(df, "acquiring"), 2),
        }

    def parse_folder(
        self,
        folder: Path,
        pattern: str = "*.xlsx",
    ) -> Tuple[pd.DataFrame, list[Dict]]:
        """
        Разобрать все файлы в папке.

        Args:
            folder: Папка с Excel-файлами
            pattern: Glob-паттерн (default: *.xlsx)

        Returns:
            (combined_df, summaries) — объединённый DataFrame + список сводок
        """
        files = sorted(folder.glob(pattern))
        if not files:
            logger.warning("Нет файлов в %s по паттерну %s", folder, pattern)
            return pd.DataFrame(), []

        all_dfs: list[pd.DataFrame] = []
        summaries: list[Dict] = []

        for f in files:
            try:
                df, warning = self.parse(f)
                if df.empty:
                    continue
                if warning.has_changes:
                    logger.warning("Схема %s: %s", f.name, warning)
                all_dfs.append(df)
                summaries.append(self.summarize(df))
            except SchemaError as exc:
                logger.warning("Пропускаем %s — не Отчёт реализации: %s", f.name, exc)
            except Exception as exc:
                logger.error("Ошибка обработки %s: %s", f.name, exc, exc_info=True)

        combined = (
            pd.concat(all_dfs, ignore_index=True)
            if all_dfs
            else pd.DataFrame()
        )
        return combined, summaries


# ─── Агрегация по периодам ────────────────────────────────────────────────────

def summarize_by_period(summaries: list[Dict]) -> pd.DataFrame:
    """
    Свести список сводок (один элемент = один файл) в таблицу P&L.

    Args:
        summaries: Список dict из WbDetailParser.summarize()

    Returns:
        DataFrame с одной строкой на файл + строка ИТОГО.
    """
    if not summaries:
        return pd.DataFrame()

    LABEL_MAP = {
        "file":              "Файл",
        "freq":              "Частота",
        "data_type":         "Тип данных",
        "date_from":         "Дата от",
        "date_to":           "Дата до",
        "n_rows":            "Строк",
        "n_sales":           "Продаж (шт.)",
        "n_returns":         "Возвратов (шт.)",
        "gross_sales":       "Продажи (к перечислению)",
        "gross_returns":     "Возвраты (к перечислению)",
        "net_payout":        "К перечислению ИТОГО",
        "commission_gross":  "Вознаграждение ВВ (gross)",
        "commission_net":    "Вознаграждение ВВ (net)",
        "logistics":         "Логистика",
        "pvz_service":       "Услуги ПВЗ",
        "storage":           "Хранение",
        "holds":             "Удержания",
        "acceptance":        "Приёмка",
        "logistics_reimb":   "Возмещение логистики",
        "fines":             "Штрафы",
        "loyalty_comp":      "Компенсация лояльности",
        "acquiring":         "Эквайринг",
    }

    rows = []
    numeric_keys = [
        k for k in LABEL_MAP
        if k not in ("file", "freq", "data_type", "date_from", "date_to", "n_rows")
        and k.startswith(("n_", "gross_", "net_", "commission_", "logistics", "pvz_", "storage", "holds", "acceptance", "fines", "loyalty_", "acquiring", "voluntary_"))
    ]

    for s in summaries:
        rows.append({LABEL_MAP.get(k, k): v for k, v in s.items() if k in LABEL_MAP})

    df = pd.DataFrame(rows)

    # Строка ИТОГО
    totals: Dict = {"Файл": "ИТОГО", "Частота": "", "Тип данных": "", "Дата от": "", "Дата до": ""}
    for key in numeric_keys:
        label = LABEL_MAP.get(key, key)
        if label in df.columns:
            try:
                totals[label] = df[label].sum()
            except TypeError:
                totals[label] = ""

    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
