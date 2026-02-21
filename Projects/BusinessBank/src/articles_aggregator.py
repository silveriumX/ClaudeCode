#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
articles_aggregator.py — P&L сводка по артикулам из истории WB детальных отчётов.

Четыре режима агрегации (аналог P&L для общих отчётов, но в разрезе артикулов):
    build_article_summary(df)              — all-time сводка, 1 строка на артикул
    build_article_pnl_by_period(df, "M")  — по месяцам (артикул × месяц)
    build_article_pnl_by_period(df, "Q")  — по кварталам
    build_article_pnl_by_period(df, "Y")  — по годам
    build_dashboard_rows(df)              — дашборд: последний период vs предыдущий

Источник данных: «История {year}» — год-партиционированные листы детальных отчётов.
"""

import logging
from datetime import date as _date
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ─── Константы ────────────────────────────────────────────────────────────────

_DOC_TYPE_COL = "Тип документа"
_SALE_TYPE    = "Продажа"
_RETURN_TYPE  = "Возврат"
_DATE_COL     = "Дата продажи"
_ARTICLE_COL  = "Артикул поставщика"

# Колонка выплаты продавцу (основная финансовая)
_PAYOUT_COL = "К перечислению Продавцу за реализованный Товар"

# Финансовые колонки для суммирования: логическое_имя → название в файле
# Знак берётся из данных как есть (затраты хранятся с отрицательным знаком).
_FIN_COLS: Dict[str, str] = {
    "commission_gross": "Вознаграждение с продаж до вычета услуг поверенного, без НДС",
    "logistics":        "Услуги по доставке товара покупателю",
    "pvz_service":      "Возмещение за выдачу и возврат товаров на ПВЗ",
    "storage":          "Хранение",
    "holds":            "Удержания",
    "acceptance":       "Операции на приемке",
    "logistics_reimb":  "Возмещение издержек по перевозке/по складским операциям с товаром",
    "fines":            "Общая сумма штрафов",
    "acquiring":        "Эквайринг/Комиссии за организацию платежей",
    "loyalty_comp":     "Компенсация скидки по программе лояльности",
}

# Колонки затрат которые входят в расчёт нетто-прибыли
# Нетто = К перечислению ИТОГО + сумма всех затратных колонок (затраты < 0)
_NET_PROFIT_FIN_KEYS = [
    "logistics", "pvz_service", "storage", "holds",
    "acceptance", "logistics_reimb", "fines", "acquiring",
]

# Русские названия месяцев
_MONTH_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май",    6: "Июнь",    7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}

# Мета-поля: берём первое непустое значение внутри группы артикула
_META_COLS = ["Название", "Предмет", "Бренд"]


# ─── Публичные функции ────────────────────────────────────────────────────────

def build_article_summary(history_df: pd.DataFrame) -> pd.DataFrame:
    """
    All-time P&L сводка по артикулам (1 строка = 1 артикул + строка ИТОГО).

    Включает полный набор финансовых метрик детального отчёта:
    продажи/возвраты шт., % возвратов, дата первой/последней продажи,
    К перечислению (продажи/возвраты/итого), все статьи затрат, нетто-прибыль.

    Args:
        history_df: DataFrame с колонками из ARTICLE_COLUMNS.
                    Числовые поля приводятся к float внутри функции
                    (обрабатывает и строки из Google Sheets, и нативные float).

    Returns:
        DataFrame отсортированный по Нетто-прибыль desc + строка ИТОГО.
        Пустой DataFrame если нет данных или нет колонки «Артикул поставщика».

    Side effects:
        Нет — только вычисление.

    Invariants:
        - history_df не мутируется.
        - При пустом df — возвращает пустой DataFrame.
    """
    if history_df.empty or _ARTICLE_COL not in history_df.columns:
        return pd.DataFrame()

    df = _prep_df(history_df)

    rows = []
    for article, grp in df.groupby(_ARTICLE_COL, sort=True):
        metrics = _article_metrics(grp)

        # Период по артикулу (первая и последняя дата продажи)
        if "_sale_date" in grp.columns:
            valid_dates = grp["_sale_date"].dropna()
            date_first = valid_dates.min().strftime("%d.%m.%Y") if not valid_dates.empty else ""
            date_last  = valid_dates.max().strftime("%d.%m.%Y") if not valid_dates.empty else ""
        else:
            date_first = date_last = ""

        row: Dict = {
            _ARTICLE_COL:              str(article),
            "Название":                _first_nonempty(grp, "Название"),
            "Предмет":                 _first_nonempty(grp, "Предмет"),
            "Бренд":                   _first_nonempty(grp, "Бренд"),
            "Первая продажа":          date_first,
            "Последняя продажа":       date_last,
            **metrics,
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)

    # Сортировка по нетто-прибыли (лучшие артикулы наверху)
    result = result.sort_values("Нетто-прибыль", ascending=False).reset_index(drop=True)

    # Строка ИТОГО
    totals: Dict = {
        _ARTICLE_COL:              "ИТОГО",
        "Название":                "",
        "Предмет":                 "",
        "Бренд":                   "",
        "Первая продажа":          result["Первая продажа"].min() if not result.empty else "",
        "Последняя продажа":       result["Последняя продажа"].max() if not result.empty else "",
        "Продажи (шт.)":           int(result["Продажи (шт.)"].sum()),
        "Возвраты (шт.)":          int(result["Возвраты (шт.)"].sum()),
        "% возвратов":             _total_return_rate(result),
        "К перечислению (Продажи)":  round(float(result["К перечислению (Продажи)"].sum()), 2),
        "К перечислению (Возвраты)": round(float(result["К перечислению (Возвраты)"].sum()), 2),
        "К перечислению ИТОГО":      round(float(result["К перечислению ИТОГО"].sum()), 2),
        "Нетто-прибыль":             round(float(result["Нетто-прибыль"].sum()), 2),
        "Логистика на ед.":          "",
    }
    for fin_key, col_name in _FIN_COLS.items():
        col_label = _fin_col_label(fin_key)
        if col_label in result.columns:
            totals[col_label] = round(float(result[col_label].sum()), 2)

    logger.info(
        "build_article_summary: %d артикулов, продажи=%d, возвраты=%d",
        len(result),
        totals["Продажи (шт.)"],
        totals["Возвраты (шт.)"],
    )

    return pd.concat([result, pd.DataFrame([totals])], ignore_index=True)


def build_article_pnl_by_period(
    history_df: pd.DataFrame,
    freq: str = "M",
) -> pd.DataFrame:
    """
    P&L по артикулам в разрезе периода (аналог pnl_by_period для общего отчёта).

    Args:
        history_df: DataFrame с колонками из ARTICLE_COLUMNS.
        freq: Частота агрегации — "M" (месяц), "Q" (квартал), "Y" (год).

    Returns:
        DataFrame: Год | Период | Артикул | Название | Бренд | Предмет
                   | Продажи шт. | Возвраты шт. | % возвратов
                   | К перечислению (Продажи/Возвраты/ИТОГО)
                   | Комиссия ВВ | Логистика | Услуги ПВЗ | Хранение
                   | Удержания | Приёмка | Возмещение логистики | Штрафы
                   | Эквайринг | Компенсация лояльности
                   | Нетто-прибыль | Логистика на ед.

        Строки отсортированы: год↓, месяц↓, нетто-прибыль↓ (новейшие периоды сверху).
        Пустой DataFrame если нет данных или нет «Дата продажи».

    Side effects:
        Нет — только вычисление.

    Invariants:
        - history_df не мутируется.
        - Строки без «Дата продажи» (NaT) исключаются из группировки по периоду.
    """
    if history_df.empty or _ARTICLE_COL not in history_df.columns:
        return pd.DataFrame()

    df = _prep_df(history_df)

    # Только строки с валидной датой продажи
    df = df.dropna(subset=["_sale_date"]).copy()
    if df.empty:
        return pd.DataFrame()

    df["_period"] = df["_sale_date"].dt.to_period(freq)

    rows = []
    for (period, article), grp in df.groupby(["_period", _ARTICLE_COL], sort=True):
        metrics = _article_metrics(grp)
        ts = period.start_time

        row: Dict = {
            "Год":      int(ts.year),
            "Период":   _period_label(ts, freq),
            "_ord":     period.ordinal,
            _ARTICLE_COL:  str(article),
            "Название":    _first_nonempty(grp, "Название"),
            "Бренд":       _first_nonempty(grp, "Бренд"),
            "Предмет":     _first_nonempty(grp, "Предмет"),
            **metrics,
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)

    # Сортировка: новые периоды сверху, внутри периода — по нетто-прибыли desc
    result = (
        result
        .sort_values(["_ord", "Нетто-прибыль"], ascending=[False, False])
        .drop(columns=["_ord"])
        .reset_index(drop=True)
    )

    logger.info(
        "build_article_pnl_by_period(freq=%s): %d строк (%d уникальных артикулов)",
        freq,
        len(result),
        result[_ARTICLE_COL].nunique(),
    )
    return result


def build_dashboard_rows(history_df: pd.DataFrame) -> List[List]:
    """
    Дашборд: последний загруженный месяц vs предыдущий.

    Структура вывода (список строк для Google Sheets):
        Строка 1:  заголовок (период, дата обновления)
        Строка 2:  пустая
        Строка 3:  «СВОДНЫЕ ИТОГИ»
        Строки 4+: метрика | текущий период | предыдущий период | Δ (абс.) | Δ (%)
        Пустая
        «ДЕТАЛИЗАЦИЯ ПО АРТИКУЛАМ — {cur_label}»
        Заголовок таблицы артикулов
        Строки артикулов (отсортировано по нетто-прибыли desc) + Δ Нетто-прибыль, Δ%

    Args:
        history_df: объединённый DataFrame из всех История {year} листов.

    Returns:
        list[list] — готово для ws.update("A1", rows).
        При пустых данных возвращает [["Нет данных"]].

    Side effects:
        Нет — только вычисление.

    Invariants:
        - history_df не мутируется.
        - Период определяется по «Дата продажи» (максимальный месяц).
    """
    if history_df.empty or _ARTICLE_COL not in history_df.columns:
        return [["Нет данных"]]

    df = _prep_df(history_df)
    df_valid = df.dropna(subset=["_sale_date"]).copy()

    if df_valid.empty:
        return [["Нет данных"]]

    df_valid["_period"] = df_valid["_sale_date"].dt.to_period("M")
    periods = sorted(df_valid["_period"].unique())

    cur_period  = periods[-1]
    prev_period = periods[-2] if len(periods) >= 2 else None

    cur_label  = _period_label(cur_period.start_time, "M")
    prev_label = _period_label(prev_period.start_time, "M") if prev_period else None

    cur_df  = df_valid[df_valid["_period"] == cur_period]
    prev_df = df_valid[df_valid["_period"] == prev_period] if prev_period else pd.DataFrame()

    # ── Summary metrics ──────────────────────────────────────────────────────
    _SUMMARY_KEYS = [
        ("Продажи (шт.)",               "Продажи (шт.)"),
        ("Возвраты (шт.)",              "Возвраты (шт.)"),
        ("% возвратов",                 "% возвратов"),
        ("К перечислению (Продажи)",    "К перечислению (Продажи)"),
        ("К перечислению (Возвраты)",   "К перечислению (Возвраты)"),
        ("К перечислению ИТОГО",        "К перечислению ИТОГО"),
        ("Комиссия ВВ",                 _fin_col_label("commission_gross")),
        ("Логистика",                   _fin_col_label("logistics")),
        ("Услуги ПВЗ",                  _fin_col_label("pvz_service")),
        ("Хранение",                    _fin_col_label("storage")),
        ("Удержания",                   _fin_col_label("holds")),
        ("Штрафы",                      _fin_col_label("fines")),
        ("Нетто-прибыль",               "Нетто-прибыль"),
    ]

    cur_tot  = _article_metrics(cur_df)
    prev_tot = _article_metrics(prev_df) if not prev_df.empty else {}

    rows: List[List] = []

    upd_str = _date.today().strftime("%d.%m.%Y")
    rows.append([
        "📊 Дашборд WB — Артикулы", "",
        f"Текущий период: {cur_label}", "",
        f"Предыдущий: {prev_label or '—'}", "",
        f"Обновлено: {upd_str}",
    ])
    rows.append([])
    rows.append(["СВОДНЫЕ ИТОГИ"])

    cmp_cols = [prev_label or "Предыдущий период", "Δ (абс.)", "Δ (%)"] if prev_label else []
    rows.append(["Метрика", cur_label] + cmp_cols)

    for label, key in _SUMMARY_KEYS:
        cur_v = cur_tot.get(key, 0)
        row: List = [label, cur_v]
        if prev_label:
            prev_v = prev_tot.get(key, 0)
            row += _delta_cells(cur_v, prev_v)
        rows.append(row)

    # ── Article detail ───────────────────────────────────────────────────────
    rows.append([])
    rows.append([f"ДЕТАЛИЗАЦИЯ ПО АРТИКУЛАМ — {cur_label}"])

    art_base_header = [
        _ARTICLE_COL, "Название", "Бренд", "Предмет",
        "Продажи (шт.)", "Возвраты (шт.)", "% возвратов",
        "К перечислению (Продажи)", "К перечислению (Возвраты)", "К перечислению ИТОГО",
        _fin_col_label("commission_gross"), _fin_col_label("logistics"),
        _fin_col_label("pvz_service"), _fin_col_label("storage"),
        _fin_col_label("holds"), _fin_col_label("acceptance"),
        _fin_col_label("logistics_reimb"), _fin_col_label("fines"),
        _fin_col_label("acquiring"), _fin_col_label("loyalty_comp"),
        "Нетто-прибыль", "Логистика на ед.",
    ]
    delta_header = ["Δ Нетто-прибыль", "Δ% Нетто-прибыль"] if prev_label else []
    rows.append(art_base_header + delta_header)

    # Previous period metrics by article
    prev_art: Dict[str, Dict] = {}
    if not prev_df.empty:
        for article, grp in prev_df.groupby(_ARTICLE_COL):
            prev_art[str(article)] = _article_metrics(grp)

    # Current period article rows
    art_rows = []
    for article, grp in cur_df.groupby(_ARTICLE_COL, sort=True):
        m = _article_metrics(grp)
        art_str = str(article)
        row = [
            art_str,
            _first_nonempty(grp, "Название"),
            _first_nonempty(grp, "Бренд"),
            _first_nonempty(grp, "Предмет"),
            m["Продажи (шт.)"],
            m["Возвраты (шт.)"],
            m["% возвратов"],
            m["К перечислению (Продажи)"],
            m["К перечислению (Возвраты)"],
            m["К перечислению ИТОГО"],
            m.get(_fin_col_label("commission_gross"), 0),
            m.get(_fin_col_label("logistics"), 0),
            m.get(_fin_col_label("pvz_service"), 0),
            m.get(_fin_col_label("storage"), 0),
            m.get(_fin_col_label("holds"), 0),
            m.get(_fin_col_label("acceptance"), 0),
            m.get(_fin_col_label("logistics_reimb"), 0),
            m.get(_fin_col_label("fines"), 0),
            m.get(_fin_col_label("acquiring"), 0),
            m.get(_fin_col_label("loyalty_comp"), 0),
            m["Нетто-прибыль"],
            m["Логистика на ед."],
        ]
        if prev_label:
            pm = prev_art.get(art_str, {})
            row += _delta_cells(m["Нетто-прибыль"], pm.get("Нетто-прибыль", 0))
        art_rows.append((float(m["Нетто-прибыль"]), row))

    art_rows.sort(key=lambda x: -x[0])
    rows.extend(r for _, r in art_rows)

    logger.info(
        "build_dashboard_rows: период=%s, артикулов=%d, сравнение=%s",
        cur_label, len(art_rows), prev_label or "нет",
    )
    return rows


# ─── Вспомогательные ──────────────────────────────────────────────────────────

def _prep_df(history_df: pd.DataFrame) -> pd.DataFrame:
    """Привести числовые и датовые колонки к нужным типам (без изменения оригинала)."""
    df = history_df.copy()

    # Числовые финансовые колонки (строки из Sheets → float)
    for col in [_PAYOUT_COL] + list(_FIN_COLS.values()):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Дата продажи → datetime
    if _DATE_COL in df.columns:
        df["_sale_date"] = pd.to_datetime(df[_DATE_COL], errors="coerce")
    else:
        df["_sale_date"] = pd.NaT

    return df


def _article_metrics(grp: pd.DataFrame) -> Dict:
    """Вычислить все P&L метрики для группы строк одного артикула (или артикул×период)."""
    has_doc_type = _DOC_TYPE_COL in grp.columns

    if has_doc_type:
        sales_grp   = grp[grp[_DOC_TYPE_COL] == _SALE_TYPE]
        returns_grp = grp[grp[_DOC_TYPE_COL] == _RETURN_TYPE]
    else:
        sales_grp   = grp
        returns_grp = pd.DataFrame(columns=grp.columns)

    n_sales   = len(sales_grp)
    n_returns = len(returns_grp)
    total     = n_sales + n_returns
    return_rate = round(n_returns / total * 100, 1) if total > 0 else 0.0

    # Выплаты продавцу
    payout_sales   = _fsum(sales_grp,   _PAYOUT_COL)
    payout_returns = _fsum(returns_grp, _PAYOUT_COL)
    payout_total   = _fsum(grp,         _PAYOUT_COL)

    # Все прочие финансовые колонки
    fin_sums: Dict[str, float] = {
        key: _fsum(grp, col)
        for key, col in _FIN_COLS.items()
    }

    # Нетто-прибыль = К перечислению ИТОГО + все затраты (затраты < 0 → суммирование корректно)
    net_profit = round(
        payout_total + sum(fin_sums[k] for k in _NET_PROFIT_FIN_KEYS),
        2,
    )

    logistics_per_unit = round(fin_sums["logistics"] / n_sales, 2) if n_sales > 0 else 0.0

    return {
        "Продажи (шт.)":              n_sales,
        "Возвраты (шт.)":             n_returns,
        "% возвратов":                return_rate,
        "К перечислению (Продажи)":   payout_sales,
        "К перечислению (Возвраты)":  payout_returns,
        "К перечислению ИТОГО":       payout_total,
        # Финансовые колонки с человекочитаемыми названиями
        _fin_col_label("commission_gross"): fin_sums["commission_gross"],
        _fin_col_label("logistics"):        fin_sums["logistics"],
        _fin_col_label("pvz_service"):      fin_sums["pvz_service"],
        _fin_col_label("storage"):          fin_sums["storage"],
        _fin_col_label("holds"):            fin_sums["holds"],
        _fin_col_label("acceptance"):       fin_sums["acceptance"],
        _fin_col_label("logistics_reimb"):  fin_sums["logistics_reimb"],
        _fin_col_label("fines"):            fin_sums["fines"],
        _fin_col_label("acquiring"):        fin_sums["acquiring"],
        _fin_col_label("loyalty_comp"):     fin_sums["loyalty_comp"],
        "Нетто-прибыль":                    net_profit,
        "Логистика на ед.":                 logistics_per_unit,
    }


def _fin_col_label(key: str) -> str:
    """Человекочитаемое название для финансового ключа (используется в заголовках Sheets)."""
    _LABELS = {
        "commission_gross": "Комиссия ВВ",
        "logistics":        "Логистика",
        "pvz_service":      "Услуги ПВЗ",
        "storage":          "Хранение",
        "holds":            "Удержания",
        "acceptance":       "Операции на приемке",
        "logistics_reimb":  "Возмещение логистики",
        "fines":            "Штрафы",
        "acquiring":        "Эквайринг",
        "loyalty_comp":     "Компенсация лояльности",
    }
    return _LABELS.get(key, key)


def _fsum(frame: pd.DataFrame, col: Optional[str]) -> float:
    """Сумма числовой колонки (0.0 если колонки нет или frame пустой)."""
    if col is None or frame.empty or col not in frame.columns:
        return 0.0
    return round(float(frame[col].fillna(0.0).sum()), 2)


def _period_label(ts: "pd.Timestamp", freq: str) -> str:
    """Человекочитаемая метка периода из timestamp."""
    if freq == "M":
        return f"{_MONTH_RU[ts.month]} {ts.year}"
    elif freq == "Q":
        quarter = (ts.month - 1) // 3 + 1
        return f"Q{quarter} {ts.year}"
    else:  # "Y"
        return str(ts.year)


def _total_return_rate(result: pd.DataFrame) -> float:
    """Общий % возвратов для строки ИТОГО."""
    n_sales   = result["Продажи (шт.)"].sum()
    n_returns = result["Возвраты (шт.)"].sum()
    total = n_sales + n_returns
    return round(n_returns / total * 100, 1) if total > 0 else 0.0


def _delta_cells(cur_v, prev_v) -> list:
    """Вернуть [prev_v, delta_abs, delta_pct] для ячеек сравнения периодов."""
    try:
        c = float(cur_v)
        p = float(prev_v)
    except (TypeError, ValueError):
        return [prev_v, "", ""]
    delta = round(c - p, 2)
    if p != 0:
        delta_pct = f"{delta / abs(p) * 100:+.1f}%"
    elif delta > 0:
        delta_pct = "+∞"
    elif delta < 0:
        delta_pct = "-∞"
    else:
        delta_pct = "0.0%"
    return [p, delta, delta_pct]


def _first_nonempty(grp: pd.DataFrame, col: str) -> str:
    """Вернуть первое непустое значение колонки, иначе пустую строку."""
    if col not in grp.columns:
        return ""
    vals = grp[col].dropna().astype(str)
    vals = vals[vals.str.strip() != ""]
    return vals.iloc[0] if not vals.empty else ""
