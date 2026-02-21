#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wb_general_report.py — Парсер общего списка финансовых отчётов WB.

Формат файла (xls/xlsx):
    Строка 0: Итого (сводная строка — пропускается)
    Строка 1: Упрощённые заголовки (пропускаются)
    Строка 2: Полные заголовки (используются как header)
    Строка 3+: Данные — по одной строке на каждый еженедельный отчёт

Типы отчётов в файле:
    «Основной»    — реальные продажи
    «По выкупам»  — самовыкупы (отслеживание)

Как получить файл из WB:
    WB Партнёр → Аналитика → Финансовые отчёты →
    кнопка «Список отчётов» (или «Экспорт всех отчётов»)

Использование:
    from src.wb_general_report import WbGeneralParser

    parser = WbGeneralParser()
    df = parser.parse(Path("Финансовые отчеты/Фин.отчет общий.ДБЗ..xls"))
    monthly = parser.monthly_pnl(df)
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ─── Схема ───────────────────────────────────────────────────────────────────

# Обязательные колонки — без них парсинг невозможен
REQUIRED_COLS: set[str] = {
    "№ отчета",
    "Дата начала",
    "Дата конца",
    "Тип отчета",
    "Продажа",
    "К перечислению за товар",
    "Итого к оплате",
}

# Эталонный полный набор колонок — изменения = предупреждение
EXPECTED_COLS: set[str] = {
    "№ отчета",
    "Юридическое лицо",
    "Дата начала",
    "Дата конца",
    "Дата формирования",
    "Тип отчета",
    "Продажа",
    "В том числе Компенсация скидки по программе лояльности",
    "К перечислению за товар",
    "Согласованная скидка, %",
    "Стоимость логистики",
    "Стоимость хранения",
    "Стоимость операций на приемке",
    "Прочие удержания/выплаты",
    "Общая сумма штрафов",
    "Корректировка Вознаграждения Вайлдберриз (ВВ)",
    "Стоимость участия в программе лояльности",
    "Сумма удержанная за начисленные баллы программы лояльности",
    "Разовое изменение срока перечисления денежных средств",
    "Итого к оплате",
    "Валюта",
}

# Финансовые колонки: логическое_имя → название в файле
FIN_COLS: Dict[str, str] = {
    "gross_sales":       "Продажа",
    "loyalty_comp":      "В том числе Компенсация скидки по программе лояльности",
    "payout":            "К перечислению за товар",
    "logistics":         "Стоимость логистики",
    "storage":           "Стоимость хранения",
    "acceptance":        "Стоимость операций на приемке",
    "other_holds":       "Прочие удержания/выплаты",
    "fines":             "Общая сумма штрафов",
    "commission_corr":   "Корректировка Вознаграждения Вайлдберриз (ВВ)",
    "loyalty_program":   "Стоимость участия в программе лояльности",
    "loyalty_points":    "Сумма удержанная за начисленные баллы программы лояльности",
    "payout_timing":     "Разовое изменение срока перечисления денежных средств",
    "net_payout":        "Итого к оплате",
}

# Русские названия месяцев для отображения
_MONTH_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май",    6: "Июнь",    7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


# ─── Валидация ────────────────────────────────────────────────────────────────

class SchemaError(ValueError):
    """Структура файла не соответствует ожидаемой схеме."""


class SchemaWarning:
    """Результат сравнения схемы с эталоном."""

    def __init__(self, added: set[str], removed: set[str]) -> None:
        self.added   = added    # новые колонки, которых не было в эталоне
        self.removed = removed  # удалённые колонки, которые были в эталоне

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


def validate_schema(df: pd.DataFrame) -> SchemaWarning:
    """
    Проверить схему файла.

    Raises:
        SchemaError: если обязательные колонки отсутствуют.

    Returns:
        SchemaWarning с информацией об изменениях схемы (может быть пустым).
    """
    actual = set(df.columns)
    missing = REQUIRED_COLS - actual
    if missing:
        raise SchemaError(
            f"Общий список WB отчётов: отсутствуют обязательные колонки ({len(missing)} шт.):\n"
            + "\n".join(f"  - {c}" for c in sorted(missing))
        )

    # Сравниваем с эталоном
    added   = actual - EXPECTED_COLS
    removed = EXPECTED_COLS - actual
    warning = SchemaWarning(added=added, removed=removed)

    if warning.has_changes:
        logger.warning("Схема изменилась!\n%s", warning)

    return warning


# ─── Парсер ───────────────────────────────────────────────────────────────────

class WbGeneralParser:
    """
    Парсер общего списка финансовых отчётов WB (XLS/XLSX).

    Формат: строка 0 = Итого, строки 1-2 = заголовки, строки 3+ = данные.
    Читает header из строки 2, остальное отбрасывает.
    """

    # Строка с заголовками (0-based в XLS)
    HEADER_ROW = 2

    def parse(
        self,
        file_path: Path,
        report_type: Optional[str] = None,
    ) -> tuple[pd.DataFrame, "SchemaWarning"]:
        """
        Разобрать общий список отчётов WB.

        Args:
            file_path:   Путь к XLS/XLSX файлу
            report_type: Фильтр по типу: «Основной» | «По выкупам» | None (все)

        Returns:
            (DataFrame, SchemaWarning) — данные и информация об изменениях схемы.
            Пустой DataFrame при ошибке чтения.

        Raises:
            SchemaError: если обязательные колонки отсутствуют.
        """
        engine = "xlrd" if file_path.suffix.lower() == ".xls" else "openpyxl"
        _empty_warning = SchemaWarning(added=set(), removed=set())

        try:
            df = pd.read_excel(
                file_path,
                sheet_name=0,
                header=self.HEADER_ROW,
                engine=engine,
            )
        except Exception as exc:
            logger.error("Не удалось прочитать %s: %s", file_path.name, exc)
            return pd.DataFrame(), _empty_warning

        # Убрать безымянные колонки-артефакты (пустые)
        df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

        warning = validate_schema(df)

        # Нормализация дат
        for col in ("Дата начала", "Дата конца", "Дата формирования"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Убрать строки без ID отчёта (итоговые и пустые строки)
        df = df[pd.to_numeric(df["№ отчета"], errors="coerce").notna()].copy()
        df["№ отчета"] = df["№ отчета"].astype(int)

        # Числовые финансовые колонки → float
        for logical, col_name in FIN_COLS.items():
            if col_name in df.columns:
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce").fillna(0.0)

        # Фильтр по типу отчёта
        if report_type is not None:
            df = df[df["Тип отчета"] == report_type].copy()

        df = df.sort_values("Дата начала").reset_index(drop=True)

        logger.info(
            "Разобран %s: %d отчётов (тип=%s), период %s … %s",
            file_path.name,
            len(df),
            report_type or "все",
            df["Дата начала"].min().date() if not df.empty else "—",
            df["Дата конца"].max().date()  if not df.empty else "—",
        )
        return df, warning

    def monthly_pnl(
        self,
        df: pd.DataFrame,
        report_type: str = "Основной",
    ) -> pd.DataFrame:
        """
        Сводная P&L по месяцам.

        Args:
            df:          DataFrame из parse() (нефильтрованный или отфильтрованный)
            report_type: Использовать только этот тип отчёта (default: «Основной»)

        Returns:
            DataFrame: Месяц | Продажа | К перечислению | Логистика | Хранение | ... | Итого к оплате
        """
        src = df[df["Тип отчета"] == report_type].copy() if "Тип отчета" in df.columns else df.copy()

        if src.empty:
            return pd.DataFrame()

        src["_period"] = src["Дата начала"].dt.to_period("M")

        agg_cols = {logical: col for logical, col in FIN_COLS.items() if col in src.columns}

        rows = []
        for period, grp in src.groupby("_period"):
            ts = period.start_time
            row: Dict = {
                "Год":    int(ts.year),
                "Месяц":  int(ts.month),
                "Период": f"{_MONTH_RU[ts.month]} {ts.year}",
                "Отчётов (шт.)": len(grp),
            }
            for logical, col_name in agg_cols.items():
                row[col_name] = round(float(grp[col_name].sum()), 2)
            rows.append(row)

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows).sort_values(["Год", "Месяц"])

        # Строка ИТОГО
        totals: Dict = {"Год": "ИТОГО", "Месяц": "", "Период": "", "Отчётов (шт.)": result["Отчётов (шт.)"].sum()}
        for col_name in agg_cols.values():
            if col_name in result.columns:
                totals[col_name] = round(float(result[col_name].sum()), 2)

        return pd.concat([result, pd.DataFrame([totals])], ignore_index=True)

    def pnl_by_period(
        self,
        df: pd.DataFrame,
        freq: str = "M",
    ) -> pd.DataFrame:
        """
        P&L по периоду — оба типа отчётов в одной таблице.

        Args:
            df:   DataFrame из parse() (нефильтрованный — оба типа)
            freq: Частота агрегации: "M" (месяц) | "Q" (квартал) | "Y" (год)

        Returns:
            DataFrame: Год | Период | Тип отчета | Отчётов (шт.) | <финансовые колонки>
            Последняя строка: ИТОГО (суммарно по всем типам и периодам).

        Side effects:
            Нет — только вычисление, никаких записей.

        Invariants:
            - monthly_pnl() не вызывается и не изменяется.
            - Входной df не мутируется.
        """
        if df.empty or "Дата начала" not in df.columns:
            return pd.DataFrame()

        src = df.copy()
        src["_period"] = src["Дата начала"].dt.to_period(freq)

        agg_cols = {logical: col for logical, col in FIN_COLS.items() if col in src.columns}

        rows = []
        for (period, rtype), grp in src.groupby(["_period", "Тип отчета"]):
            ts = period.start_time

            if freq == "M":
                period_label = f"{_MONTH_RU[ts.month]} {ts.year}"
            elif freq == "Q":
                quarter = (ts.month - 1) // 3 + 1
                period_label = f"Q{quarter} {ts.year}"
            else:  # "Y"
                period_label = str(ts.year)

            row: Dict = {
                "Год":           int(ts.year),
                "Период":        period_label,
                "Тип отчета":    str(rtype),
                "Отчётов (шт.)": len(grp),
                "_ord":          period.ordinal,
            }
            for logical, col_name in agg_cols.items():
                row[col_name] = round(float(grp[col_name].sum()), 2)
            rows.append(row)

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows).sort_values(["_ord", "Тип отчета"])
        result = result.drop(columns=["_ord"])

        # Строка ИТОГО
        totals: Dict = {
            "Год":           "ИТОГО",
            "Период":        "",
            "Тип отчета":    "",
            "Отчётов (шт.)": int(result["Отчётов (шт.)"].sum()),
        }
        for col_name in agg_cols.values():
            if col_name in result.columns:
                totals[col_name] = round(float(result[col_name].sum()), 2)

        return pd.concat([result, pd.DataFrame([totals])], ignore_index=True)

    def weekly_table(
        self,
        df: pd.DataFrame,
        report_type: str = "Основной",
    ) -> pd.DataFrame:
        """
        Таблица по неделям (одна строка = один отчёт).

        Returns:
            DataFrame: № отчёта | Период | Продажа | К перечислению | Логистика | ...
        """
        src = df[df["Тип отчета"] == report_type].copy() if "Тип отчета" in df.columns else df.copy()

        display_cols = [
            "№ отчета",
            "Дата начала",
            "Дата конца",
            "Тип отчета",
        ] + [col for col in FIN_COLS.values() if col in src.columns]

        return src[[c for c in display_cols if c in src.columns]].reset_index(drop=True)
