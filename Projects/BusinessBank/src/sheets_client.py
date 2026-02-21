#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sheets_client.py — Google Sheets клиент для WB финансовых отчётов.

Структура таблицы (5 листов):
    История отчётов    — все еженедельные отчёты (из Общего списка XLS)
    P&L по месяцам     — агрегат по месяцам, авто-пересчёт
    Артикулы (неделя)  — SKU-данные из последнего детального отчёта (перезаписывается)
    Артикулы (история) — накопительно все загруженные SKU-данные
    По выкупам         — данные из «по выкупам» отчётов

Использование:
    from src.sheets_client import WbSheetsClient

    client = WbSheetsClient(sa_path=Path("../FinanceBot/service_account.json"))
    # Создать таблицу один раз:
    sheets_id = client.create_spreadsheet("DBZ WB Финансовые отчёты")
    # Дальнейшая работа:
    client = WbSheetsClient(sa_path=..., spreadsheet_id=sheets_id)
    client.update_reports_history(df)   # из WbGeneralParser
    client.update_articles_current(df)  # из WbDetailParser
"""

import datetime
import logging
import time
from pathlib import Path
from typing import List, Optional

from .articles_aggregator import (
    build_article_pnl_by_period,
    build_article_summary,
    build_dashboard_rows,
)

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# ─── Конфигурация листов ──────────────────────────────────────────────────────

SHEET_REPORTS        = "История отчётов"
SHEET_PNL            = "P&L по месяцам"
SHEET_PNL_QUARTERS   = "P&L — Кварталы"
SHEET_PNL_YEARS      = "P&L — Годы"
SHEET_ARTICLES       = "Артикулы (неделя)"
SHEET_HISTORY        = "Артикулы (история)"
SHEET_ART_SUMMARY    = "Артикулы — Сводка"
SHEET_ART_MONTHLY    = "Артикулы — По месяцам"
SHEET_ART_QUARTERLY  = "Артикулы — По кварталам"
SHEET_ART_YEARLY     = "Артикулы — По годам"
SHEET_DASHBOARD      = "📊 Дашборд"
SHEET_BUYOUTS        = "По выкупам"


def _history_sheet_name(year: int) -> str:
    """Имя листа для года: «История 2026»."""
    return f"История {year}"

SHEET_NAMES = [SHEET_REPORTS, SHEET_PNL, SHEET_ARTICLES, SHEET_HISTORY, SHEET_BUYOUTS]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Колонки из детального отчёта (WbDetailParser) которые пишем в Sheets
ARTICLE_COLUMNS = [
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
    "Услуги по доставке товара покупателю",
    "Возмещение за выдачу и возврат товаров на ПВЗ",
    "Хранение",
    "Удержания",
    "Операции на приемке",
    "Возмещение издержек по перевозке/по складским операциям с товаром",
    "Общая сумма штрафов",
    "Эквайринг/Комиссии за организацию платежей",
    "Компенсация скидки по программе лояльности",
    "Склад",
    "Страна",
    "Способы продажи и тип товара",
    "Srid",
    "_file",
    "_freq",
    "_data_type",
]

# Колонки из общего списка (WbGeneralParser) для листа История отчётов
REPORT_COLUMNS = [
    "№ отчета",
    "Юридическое лицо",
    "Дата начала",
    "Дата конца",
    "Дата формирования",
    "Тип отчета",
    "Продажа",
    "В том числе Компенсация скидки по программе лояльности",
    "К перечислению за товар",
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
]


# ─── Клиент ───────────────────────────────────────────────────────────────────

class WbSheetsClient:
    """
    Google Sheets клиент для WB финансовых отчётов.

    Args:
        sa_path:        Путь к service_account.json
        spreadsheet_id: ID существующей таблицы (None → нужно создать)
    """

    def __init__(
        self,
        sa_path: Path,
        spreadsheet_id: Optional[str] = None,
    ) -> None:
        self.sa_path = sa_path
        self.spreadsheet_id = spreadsheet_id
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            creds = Credentials.from_service_account_file(
                str(self.sa_path), scopes=SCOPES
            )
            self._client = gspread.authorize(creds)
        return self._client

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        if self._spreadsheet is None:
            if self.spreadsheet_id is None:
                raise ValueError("spreadsheet_id не задан. Сначала вызови create_spreadsheet().")
            self._spreadsheet = self._get_client().open_by_key(self.spreadsheet_id)
        return self._spreadsheet

    def _get_or_create_sheet(self, name: str, rows: int = 1000, cols: int = 50) -> gspread.Worksheet:
        """Получить лист по имени или создать если не существует."""
        sh = self._get_spreadsheet()
        try:
            return sh.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=name, rows=rows, cols=cols)
            logger.info("Создан лист: %s", name)
            return ws

    # ─── Создание таблицы ─────────────────────────────────────────────────────

    def create_spreadsheet(self, title: str = "DBZ WB Финансовые отчёты") -> str:
        """
        Создать новую Google таблицу с нужными листами.

        Returns:
            spreadsheet_id — сохрани в .env как WB_SHEETS_ID
        """
        client = self._get_client()
        sh = client.create(title)
        self.spreadsheet_id = sh.id
        self._spreadsheet = sh

        # Переименовать первый лист
        first_ws = sh.sheet1
        first_ws.update_title(SHEET_REPORTS)

        # Создать остальные листы
        for name in SHEET_NAMES[1:]:
            sh.add_worksheet(title=name, rows=50000, cols=60)
            time.sleep(0.5)  # Google API rate limit

        logger.info("Таблица создана: %s (ID: %s)", title, sh.id)
        logger.info("URL: %s", sh.url)

        return sh.id

    @property
    def spreadsheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"

    # ─── Запись данных ────────────────────────────────────────────────────────

    def update_reports_history(self, df: pd.DataFrame) -> int:
        """
        Обновить лист «История отчётов» (upsert по № отчёта).

        Args:
            df: DataFrame из WbGeneralParser.parse() (все типы отчётов)

        Returns:
            Количество новых строк добавлено.
        """
        ws = self._get_or_create_sheet(SHEET_REPORTS)

        # Выбрать нужные колонки
        cols = [c for c in REPORT_COLUMNS if c in df.columns]
        src = df[cols].copy()

        # Конвертировать даты в строки
        for col in ("Дата начала", "Дата конца", "Дата формирования"):
            if col in src.columns:
                src[col] = src[col].dt.strftime("%Y-%m-%d").fillna("")

        # Получить существующие данные
        existing = ws.get_all_values()

        if not existing:
            # Таблица пустая — записываем всё
            data = [cols] + src.values.tolist()
            ws.update("A1", _sanitize(data))
            logger.info("История отчётов: записано %d строк (первая загрузка)", len(src))
            return len(src)

        # Найти колонку с № отчёта
        header = existing[0]
        report_id_col = header.index("№ отчета") if "№ отчета" in header else None

        if report_id_col is None:
            # Несовместимая схема — перезаписываем
            ws.clear()
            data = [cols] + src.values.tolist()
            ws.update("A1", _sanitize(data))
            return len(src)

        # Существующие ID отчётов
        existing_ids = {
            str(row[report_id_col]).strip()
            for row in existing[1:]
            if len(row) > report_id_col
        }

        # Новые строки (которых ещё нет)
        new_rows = src[~src["№ отчета"].astype(str).isin(existing_ids)]

        if new_rows.empty:
            logger.info("История отчётов: нет новых отчётов")
            return 0

        # Дописать в конец
        append_data = new_rows.values.tolist()
        ws.append_rows(_sanitize(append_data), value_input_option="USER_ENTERED")
        logger.info("История отчётов: добавлено %d новых отчётов", len(new_rows))
        return len(new_rows)

    def update_monthly_pnl(self, monthly_df: pd.DataFrame) -> None:
        """
        Перезаписать лист «P&L по месяцам».

        Args:
            monthly_df: DataFrame из WbGeneralParser.monthly_pnl()
        """
        ws = self._get_or_create_sheet(SHEET_PNL)
        ws.clear()

        if monthly_df.empty:
            return

        # Конвертировать Period-типы если есть
        data = monthly_df.copy()
        for col in data.select_dtypes(include=["period[M]", "datetime64[ns]"]).columns:
            data[col] = data[col].astype(str)

        rows = [data.columns.tolist()] + data.values.tolist()
        ws.update("A1", _sanitize(rows))
        logger.info("P&L по месяцам: обновлено %d строк", len(monthly_df))

    def update_pnl_quarters(self, df: pd.DataFrame) -> None:
        """
        Перезаписать лист «P&L — Кварталы».

        Args:
            df: DataFrame из WbGeneralParser.pnl_by_period(df, "Q")

        Side effects:
            - Лист SHEET_PNL_QUARTERS полностью перезаписывается.

        Invariants:
            - Другие листы не затрагиваются.
            - При пустом df — лист очищается, данные не пишутся.
        """
        ws = self._get_or_create_sheet(SHEET_PNL_QUARTERS)
        ws.clear()

        if df.empty:
            return

        data = df.copy()
        rows = [data.columns.tolist()] + data.values.tolist()
        ws.update("A1", _sanitize(rows))
        logger.info("P&L — Кварталы: обновлено %d строк", len(df))

    def update_pnl_years(self, df: pd.DataFrame) -> None:
        """
        Перезаписать лист «P&L — Годы».

        Args:
            df: DataFrame из WbGeneralParser.pnl_by_period(df, "Y")

        Side effects:
            - Лист SHEET_PNL_YEARS полностью перезаписывается.

        Invariants:
            - Другие листы не затрагиваются.
            - При пустом df — лист очищается, данные не пишутся.
        """
        ws = self._get_or_create_sheet(SHEET_PNL_YEARS)
        ws.clear()

        if df.empty:
            return

        data = df.copy()
        rows = [data.columns.tolist()] + data.values.tolist()
        ws.update("A1", _sanitize(rows))
        logger.info("P&L — Годы: обновлено %d строк", len(df))

    def update_articles_summary(self, summary_df: pd.DataFrame) -> None:
        """
        Перезаписать лист «Артикулы — Сводка».

        Args:
            summary_df: DataFrame из build_article_summary()

        Side effects:
            - Лист SHEET_ART_SUMMARY полностью перезаписывается.

        Invariants:
            - Лист SHEET_HISTORY не изменяется.
            - При пустом df — лист очищается, данные не пишутся.
        """
        ws = self._get_or_create_sheet(SHEET_ART_SUMMARY, rows=5000, cols=20)
        ws.clear()

        if summary_df.empty:
            return

        data = summary_df.copy()
        rows = [data.columns.tolist()] + data.values.tolist()
        ws.update("A1", _sanitize(rows))
        logger.info("Артикулы — Сводка: обновлено %d строк", len(summary_df))

    def update_articles_pnl_monthly(self, df: pd.DataFrame) -> None:
        """
        Перезаписать лист «Артикулы — По месяцам».

        Args:
            df: DataFrame из build_article_pnl_by_period(history_df, "M")

        Side effects:
            - Лист SHEET_ART_MONTHLY полностью перезаписывается.

        Invariants:
            - Другие листы не затрагиваются.
            - При пустом df — лист очищается, данные не пишутся.
        """
        ws = self._get_or_create_sheet(SHEET_ART_MONTHLY, rows=100000, cols=30)
        ws.clear()
        if df.empty:
            return
        rows = [df.columns.tolist()] + df.values.tolist()
        _batch_write(ws, rows)
        logger.info("Артикулы — По месяцам: обновлено %d строк", len(df))

    def update_articles_pnl_quarterly(self, df: pd.DataFrame) -> None:
        """
        Перезаписать лист «Артикулы — По кварталам».

        Args:
            df: DataFrame из build_article_pnl_by_period(history_df, "Q")

        Side effects:
            - Лист SHEET_ART_QUARTERLY полностью перезаписывается.

        Invariants:
            - Другие листы не затрагиваются.
            - При пустом df — лист очищается, данные не пишутся.
        """
        ws = self._get_or_create_sheet(SHEET_ART_QUARTERLY, rows=10000, cols=30)
        ws.clear()
        if df.empty:
            return
        rows = [df.columns.tolist()] + df.values.tolist()
        _batch_write(ws, rows)
        logger.info("Артикулы — По кварталам: обновлено %d строк", len(df))

    def update_articles_pnl_yearly(self, df: pd.DataFrame) -> None:
        """
        Перезаписать лист «Артикулы — По годам».

        Args:
            df: DataFrame из build_article_pnl_by_period(history_df, "Y")

        Side effects:
            - Лист SHEET_ART_YEARLY полностью перезаписывается.

        Invariants:
            - Другие листы не затрагиваются.
            - При пустом df — лист очищается, данные не пишутся.
        """
        ws = self._get_or_create_sheet(SHEET_ART_YEARLY, rows=5000, cols=30)
        ws.clear()
        if df.empty:
            return
        rows = [df.columns.tolist()] + df.values.tolist()
        _batch_write(ws, rows)
        logger.info("Артикулы — По годам: обновлено %d строк", len(df))

    def update_dashboard(self, rows: List[List]) -> None:
        """
        Перезаписать лист «📊 Дашборд».

        Args:
            rows: список строк из build_dashboard_rows()

        Side effects:
            - Лист SHEET_DASHBOARD полностью перезаписывается.

        Invariants:
            - Другие листы не изменяются.
            - При пустом rows — лист очищается, данные не пишутся.
        """
        ws = self._get_or_create_sheet(SHEET_DASHBOARD, rows=5000, cols=30)
        ws.clear()
        if not rows:
            return
        ws.update("A1", _sanitize(rows))
        logger.info("Дашборд: обновлено %d строк", len(rows))

    def rebuild_dashboard(self) -> str:
        """
        Собрать дашборд из истории и записать в «📊 Дашборд».

        Returns:
            Метка текущего периода (напр. «Февраль 2026») для ответа бота.
            «—» если данных нет.

        Side effects:
            - Вызывает _get_all_history_df() (чтение истории).
            - Перезаписывает SHEET_DASHBOARD.

        Invariants:
            - Листы истории не изменяются.
        """
        history_df = self._get_all_history_df()
        rows = build_dashboard_rows(history_df)
        self.update_dashboard(rows)

        # Период указан в первой строке: ["📊 Дашборд WB ...", "", "Текущий период: {label}", ...]
        if rows and len(rows[0]) >= 3:
            cell = str(rows[0][2])
            return cell.replace("Текущий период: ", "").strip()
        return "—"

    def rebuild_articles_summary(self) -> int:
        """
        Прочитать все История {year} → пересчитать → записать листы аналитики.

        Обновляет 4 листа:
            - Артикулы — Сводка        (all-time, 1 строка на артикул)
            - Артикулы — По месяцам    (артикул × месяц)
            - Артикулы — По кварталам  (артикул × квартал)
            - Артикулы — По годам      (артикул × год)

        Returns:
            Количество уникальных артикулов в сводке.

        Side effects:
            - Все четыре листа полностью перезаписываются.
            - Листы «История {year}» читаются, но не изменяются.

        Invariants:
            - Листы истории не изменяются ни при каком исходе.
            - При пустой истории — все 4 листа очищаются, возвращается 0.
        """
        history_df = self._get_all_history_df()

        if history_df.empty:
            logger.info("История артикулов: нет данных для построения сводки")
            self.update_articles_summary(pd.DataFrame())
            self.update_articles_pnl_monthly(pd.DataFrame())
            self.update_articles_pnl_quarterly(pd.DataFrame())
            self.update_articles_pnl_yearly(pd.DataFrame())
            return 0

        # All-time сводка
        summary = build_article_summary(history_df)
        self.update_articles_summary(summary)

        # P&L по периодам
        monthly   = build_article_pnl_by_period(history_df, "M")
        quarterly = build_article_pnl_by_period(history_df, "Q")
        yearly    = build_article_pnl_by_period(history_df, "Y")
        self.update_articles_pnl_monthly(monthly)
        self.update_articles_pnl_quarterly(quarterly)
        self.update_articles_pnl_yearly(yearly)

        n_articles = max(0, len(summary) - 1) if not summary.empty else 0
        logger.info(
            "rebuild_articles_summary: %d артикулов, месяцев=%d, кварталов=%d, годов=%d",
            n_articles,
            monthly["Период"].nunique() if not monthly.empty else 0,
            quarterly["Период"].nunique() if not quarterly.empty else 0,
            yearly["Период"].nunique() if not yearly.empty else 0,
        )
        return n_articles

    def _get_all_history_df(self) -> pd.DataFrame:
        """
        Прочитать все листы «История {year}» и объединить в один DataFrame.

        Если год-листов нет — читает устаревший лист «Артикулы (история)» как fallback.

        Returns:
            Объединённый DataFrame или пустой DataFrame если данных нет.

        Side effects:
            Нет — только чтение.

        Invariants:
            - Листы не изменяются.
        """
        sh = self._get_spreadsheet()
        all_ws = sh.worksheets()
        year_sheets = [ws for ws in all_ws if ws.title.startswith("История ")]

        if not year_sheets:
            # Fallback: legacy single sheet
            try:
                legacy_ws = sh.worksheet(SHEET_HISTORY)
                vals = legacy_ws.get_all_values()
                if len(vals) >= 2:
                    logger.info("_get_all_history_df: читаем legacy лист %s (%d строк)", SHEET_HISTORY, len(vals) - 1)
                    return pd.DataFrame(vals[1:], columns=vals[0])
            except gspread.WorksheetNotFound:
                pass
            return pd.DataFrame()

        frames = []
        for ws in sorted(year_sheets, key=lambda w: w.title):
            vals = ws.get_all_values()
            if len(vals) < 2:
                continue
            frames.append(pd.DataFrame(vals[1:], columns=vals[0]))
            logger.debug("_get_all_history_df: %s — %d строк", ws.title, len(vals) - 1)

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)
        logger.info("_get_all_history_df: итого %d строк из %d листов", len(combined), len(frames))
        return combined

    def _append_to_history_year_sheet(self, sheet_name: str, src: pd.DataFrame) -> int:
        """
        Дописать строки в лист истории за один год (дедупликация по Srid).

        Args:
            sheet_name: «История {year}»
            src: строки за этот год (уже без временных колонок)

        Returns:
            Количество добавленных строк.

        Side effects:
            - Лист sheet_name создаётся при необходимости.
            - В лист дописываются новые строки (не перезаписывается).

        Invariants:
            - Существующие строки не удаляются и не изменяются.
            - При пустом src — возвращает 0, лист не трогается.
        """
        if src.empty:
            return 0

        ws = self._get_or_create_sheet(sheet_name, rows=500000, cols=60)
        existing = ws.get_all_values()

        has_header = bool(existing) and "Артикул поставщика" in existing[0]

        if not existing or not has_header:
            if existing and not has_header:
                ws.insert_rows([src.columns.tolist()], row=1)
                logger.warning("%s: заголовок отсутствовал — восстановлен", sheet_name)
                existing = [src.columns.tolist()] + existing
            else:
                rows = [src.columns.tolist()] + src.values.tolist()
                _batch_write(ws, rows)
                logger.info("%s: первая запись %d строк", sheet_name, len(src))
                return len(src)

        header = existing[0]
        srid_col_idx = header.index("Srid") if "Srid" in header else None

        if srid_col_idx is not None and "Srid" in src.columns:
            existing_srids = {
                row[srid_col_idx].strip()
                for row in existing[1:]
                if len(row) > srid_col_idx and row[srid_col_idx].strip()
            }
            new_rows = src[~src["Srid"].astype(str).isin(existing_srids)]
        else:
            new_rows = src

        if new_rows.empty:
            logger.info("%s: нет новых строк", sheet_name)
            return 0

        ws.append_rows(_sanitize(new_rows.values.tolist()), value_input_option="USER_ENTERED")
        logger.info("%s: добавлено %d строк", sheet_name, len(new_rows))
        return len(new_rows)

    def migrate_history_to_year_sheets(self) -> int:
        """
        Однократная миграция: «Артикулы (история)» → «История {year}» листы.

        Проверяет есть ли уже год-листы (идемпотентна: повторный вызов = no-op).

        Returns:
            Количество перенесённых строк (0 если год-листы уже существуют).

        Side effects:
            - Создаёт листы «История {year}» и пишет в них данные.
            - «Артикулы (история)» НЕ удаляется (оставляется для ручной проверки).

        Invariants:
            - Если год-листы уже существуют — ничего не делает, возвращает 0.
            - Если SHEET_HISTORY не существует — возвращает 0.
        """
        sh = self._get_spreadsheet()
        all_ws = sh.worksheets()
        year_sheets = [ws for ws in all_ws if ws.title.startswith("История ")]

        if year_sheets:
            logger.info("migrate_history: год-листы уже существуют (%d шт.) — пропускаем", len(year_sheets))
            return 0

        try:
            legacy_ws = sh.worksheet(SHEET_HISTORY)
        except gspread.WorksheetNotFound:
            logger.info("migrate_history: лист %s не найден — нечего мигрировать", SHEET_HISTORY)
            return 0

        vals = legacy_ws.get_all_values()
        if len(vals) < 2:
            logger.info("migrate_history: %s пустой — нечего мигрировать", SHEET_HISTORY)
            return 0

        header = vals[0]
        df = pd.DataFrame(vals[1:], columns=header)

        date_col = "Дата продажи"
        if date_col in df.columns:
            df["_year"] = pd.to_datetime(df[date_col], errors="coerce").dt.year.fillna(0).astype(int)
        else:
            df["_year"] = 0

        total = 0
        for year, year_df in df.groupby("_year"):
            actual_year = int(year) if year != 0 else datetime.date.today().year
            year_df = year_df.drop(columns=["_year"])
            sheet_name = _history_sheet_name(actual_year)
            ws = self._get_or_create_sheet(sheet_name, rows=500000, cols=60)
            rows = [header] + year_df.values.tolist()
            _batch_write(ws, rows)
            logger.info("migrate_history: %s → %d строк", sheet_name, len(year_df))
            total += len(year_df)

        logger.info("migrate_history: перенесено %d строк в год-листы", total)
        return total

    def update_articles_current(self, df: pd.DataFrame) -> None:
        """
        Перезаписать лист «Артикулы (неделя)» — полностью заменяется каждый раз.

        Args:
            df: DataFrame из WbDetailParser.parse() (только основной тип)
        """
        ws = self._get_or_create_sheet(SHEET_ARTICLES, rows=50000, cols=60)
        ws.clear()

        if df.empty:
            return

        src = _prepare_article_df(df)
        rows = [src.columns.tolist()] + src.values.tolist()
        _batch_write(ws, rows)
        logger.info("Артикулы (неделя): записано %d строк", len(src))

    def append_articles_history(self, df: pd.DataFrame) -> int:
        """
        Дописать новые строки в год-партиционированные листы «История {year}».

        Разбивает входной DataFrame по году «Дата продажи» и пишет каждую
        часть в соответствующий лист. Дедупликация по Srid внутри каждого листа.

        Args:
            df: DataFrame из WbDetailParser.parse()

        Returns:
            Суммарное количество добавленных строк по всем год-листам.

        Side effects:
            - Создаёт листы «История {year}» при необходимости.
            - Дописывает строки в конец соответствующего листа.

        Invariants:
            - Существующие строки не удаляются.
            - Строки без даты попадают в лист текущего года.
        """
        src = _prepare_article_df(df)
        if src.empty:
            return 0

        # Определяем год для каждой строки
        sale_dates = pd.to_datetime(src.get("Дата продажи", pd.Series(dtype=str)), errors="coerce")
        years = sale_dates.dt.year.fillna(0).astype(int)

        total = 0
        for year in sorted(years.unique()):
            actual_year = int(year) if year != 0 else datetime.date.today().year
            year_mask = years == year
            year_df = src[year_mask].copy()
            sheet_name = _history_sheet_name(actual_year)
            total += self._append_to_history_year_sheet(sheet_name, year_df)

        return total

    def update_buyouts(self, df: pd.DataFrame) -> None:
        """
        Перезаписать лист «По выкупам».

        Args:
            df: DataFrame из WbDetailParser.parse() (по_выкупам тип)
        """
        ws = self._get_or_create_sheet(SHEET_BUYOUTS)
        ws.clear()

        if df.empty:
            return

        src = _prepare_article_df(df)
        rows = [src.columns.tolist()] + src.values.tolist()
        _batch_write(ws, rows)
        logger.info("По выкупам: записано %d строк", len(src))


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def _prepare_article_df(df: pd.DataFrame) -> pd.DataFrame:
    """Выбрать и подготовить колонки из детального отчёта для записи в Sheets."""
    cols = [c for c in ARTICLE_COLUMNS if c in df.columns]
    src = df[cols].copy()

    # Даты → строки
    for col in ("Дата заказа покупателем", "Дата продажи"):
        if col in src.columns:
            src[col] = pd.to_datetime(src[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")

    return src


def _sanitize(data: list) -> list:
    """Привести значения к типам, которые принимает gspread."""
    result = []
    for row in data:
        clean = []
        for v in row:
            if pd.isna(v) if not isinstance(v, (str, bool)) else False:
                clean.append("")
            elif isinstance(v, (int, float)):
                clean.append(v)
            else:
                clean.append(str(v))
        result.append(clean)
    return result


def _batch_write(ws: gspread.Worksheet, rows: list, chunk: int = 5000) -> None:
    """Записать большой массив данных чанками (Google API limit: ~10MB per request)."""
    if not rows:
        return

    # Заголовок
    ws.update("A1", [rows[0]])
    data = rows[1:]

    for i in range(0, len(data), chunk):
        batch = data[i : i + chunk]
        ws.append_rows(_sanitize(batch), value_input_option="USER_ENTERED")
        if i + chunk < len(data):
            time.sleep(1)  # rate limit между чанками
