#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py — Telegram бот для загрузки WB финансовых отчётов в Google Sheets.

Поддерживаемые файлы:
    Фин.отчет общий*.xls/xlsx  — Общий список еженедельных отчётов
    *еженедельный*дет*.xlsx    — Детализированный еженедельный отчёт (Артикулы)

Флоу:
    1. Пользователь отправляет файл в бот
    2. Бот определяет тип файла
    3. Парсит и записывает в Google Sheets
    4. Отвечает текстовой сводкой + ссылкой

Запуск:
    python -X utf8 bot.py
"""

import io
import logging
import os
import sys
import tempfile
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

sys.path.insert(0, str(Path(__file__).parent))

from src.reports_sheet import rebuild_reports_sheet
from src.sheets_client import WbSheetsClient
from src.wb_detail_report import SchemaError as DetailSchemaError
from src.wb_detail_report import WbDetailParser
from src.wb_general_report import SchemaError as GeneralSchemaError
from src.wb_general_report import WbGeneralParser

# ─── Конфигурация ─────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
WB_SHEETS_ID  = os.getenv("WB_SHEETS_ID", "")
SA_PATH       = Path(os.getenv("SA_PATH", "../FinanceBot/service_account.json"))
_allowed_raw  = os.getenv("BOT_ALLOWED_IDS", "")
ALLOWED_IDS: set[int] = {
    int(x.strip()) for x in _allowed_raw.split(",") if x.strip().isdigit()
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

SHEETS_URL = f"https://docs.google.com/spreadsheets/d/{WB_SHEETS_ID}"

# ─── Определение типа файла ───────────────────────────────────────────────────

def detect_file_type(filename: str) -> str:
    """
    Определить тип файла по имени.

    Returns:
        "general"  — Общий список (Фин.отчет общий)
        "detail"   — Детализированный еженедельный (Артикулы)
        "unknown"  — Неизвестный
    """
    name = filename.lower()

    # Общий список: "фин.отчет общий", "финотчет общий" и т.п.
    if any(kw in name for kw in ("фин.отчет", "финотчет", "общий")):
        return "general"

    # Детализированный еженедельный: "еженедельный" + "дет"
    if "еженедельн" in name and ("дет" in name or "детализ" in name):
        return "detail"

    # Дополнительно: просто "еженедельный" с размером > 1 МБ (проверяется позже)
    if "еженедельн" in name:
        return "detail"

    return "unknown"


# ─── Обработчики ──────────────────────────────────────────────────────────────

def _check_allowed(user_id: int) -> bool:
    """Проверить доступ. Если ALLOWED_IDS пустой — пускаем всех."""
    return not ALLOWED_IDS or user_id in ALLOWED_IDS


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not _check_allowed(uid):
        await update.message.reply_text("Нет доступа.")
        return

    text = (
        "Привет! Отправь мне файл WB-отчёта:\n\n"
        "📋 Общий список отчётов (XLS)\n"
        "    → обновит историю + P&L в Google Sheets\n\n"
        "📊 Еженедельный детализированный (XLSX)\n"
        "    → обновит данные по артикулам\n\n"
        f"📎 Таблица: {SHEETS_URL}"
    )
    await update.message.reply_text(text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not _check_allowed(uid):
        await update.message.reply_text("Нет доступа.")
        return

    try:
        sheets_client = WbSheetsClient(sa_path=SA_PATH, spreadsheet_id=WB_SHEETS_ID)
        sh = sheets_client._get_spreadsheet()
        sheets = [ws.title for ws in sh.worksheets()]
        text = f"✅ Подключение: OK\nТаблица: {sh.title}\nЛисты: {', '.join(sheets)}\n\n{SHEETS_URL}"
    except Exception as exc:
        text = f"❌ Ошибка подключения: {exc}"

    await update.message.reply_text(text)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработать загруженный файл."""
    uid = update.effective_user.id
    if not _check_allowed(uid):
        await update.message.reply_text("Нет доступа.")
        return

    doc = update.message.document
    if not doc:
        return

    filename = doc.file_name or "file"
    file_size_mb = (doc.file_size or 0) / 1024 / 1024

    logger.info("Получен файл: %s (%.1f MB) от uid=%d", filename, file_size_mb, uid)

    # Определяем тип
    file_type = detect_file_type(filename)

    if file_type == "unknown":
        await update.message.reply_text(
            f"Не могу определить тип файла: {filename}\n\n"
            "Ожидаю:\n"
            "• Общий список: имя содержит «общий» или «фин.отчет»\n"
            "• Детализированный: имя содержит «еженедельный»"
        )
        return

    # Предупреждение о большом файле
    if file_size_mb > 5:
        await update.message.reply_text(f"⏳ Файл {file_size_mb:.0f} МБ — обрабатываю, подожди...")
    else:
        await update.message.reply_text("⏳ Обрабатываю...")

    # Скачиваем файл
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / filename
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(str(tmp_path))

        logger.info("Файл скачан: %s", tmp_path)

        # Маршрутизация
        if file_type == "general":
            reply = await _process_general(tmp_path, update)
        else:
            reply = await _process_detail(tmp_path, update)

    await update.message.reply_text(reply, parse_mode=ParseMode.HTML)


async def _process_general(file_path: Path, update: Update) -> str:
    """Обработать Общий список отчётов → History + P&L."""
    try:
        parser = WbGeneralParser()
        df, schema_warning = parser.parse(file_path)

        if df.empty:
            return "❌ Файл не содержит данных."

        monthly = parser.monthly_pnl(df)

        sheets_client = WbSheetsClient(sa_path=SA_PATH, spreadsheet_id=WB_SHEETS_ID)
        n_new = sheets_client.update_reports_history(df)

        # P&L по всем периодам (оба типа отчётов)
        monthly_all = parser.pnl_by_period(df, "M")
        quarterly   = parser.pnl_by_period(df, "Q")
        yearly      = parser.pnl_by_period(df, "Y")
        sheets_client.update_monthly_pnl(monthly_all)
        sheets_client.update_pnl_quarters(quarterly)
        sheets_client.update_pnl_years(yearly)

        # Перестроить лист с группировкой год/месяц
        sh = sheets_client._get_spreadsheet()
        rebuild_reports_sheet(sh, df, sheet_name="Финансовые отчёты")

        # Статистика по типам
        n_main   = int((df["Тип отчета"] == "Основной").sum())
        n_buyout = int((df["Тип отчета"] == "По выкупам").sum())
        date_from = df["Дата начала"].min().strftime("%d.%m.%Y")
        date_to   = df["Дата конца"].max().strftime("%d.%m.%Y")

        # P&L из итоговой строки
        totals = monthly[monthly["Год"] == "ИТОГО"]
        gross_sales = net_payout = 0.0
        if not totals.empty:
            gross_sales = float(totals["Продажа"].iloc[0] or 0)
            net_payout  = float(totals["Итого к оплате"].iloc[0] or 0)

        added_str = f"новых: +{n_new}" if n_new < len(df) else f"загружено: {n_new}"

        warning_block = ""
        if schema_warning.has_changes:
            lines = []
            if schema_warning.removed:
                lines.append("Удалены: " + ", ".join(sorted(schema_warning.removed)))
            if schema_warning.added:
                lines.append("Новые: " + ", ".join(sorted(schema_warning.added)))
            warning_block = "\n⚠️ <b>Схема изменилась!</b>\n" + "\n".join(lines) + "\n"

        return (
            f"✅ <b>Общий список обновлён</b>\n\n"
            f"📅 Период: {date_from} — {date_to}\n"
            f"📋 Отчётов: {len(df)} ({added_str})\n"
            f"   Основных: {n_main} | По выкупам: {n_buyout}\n\n"
            f"💰 Итого за весь период:\n"
            f"   Продажи:        {gross_sales:>14,.0f} ₽\n"
            f"   К оплате:       {net_payout:>14,.0f} ₽\n"
            f"{warning_block}\n"
            f"📎 <a href='{SHEETS_URL}'>Открыть таблицу</a>"
        )

    except GeneralSchemaError as exc:
        logger.warning("Не Общий список: %s", exc)
        return f"❌ Файл не соответствует формату Общего списка:\n{exc}"
    except Exception as exc:
        logger.exception("Ошибка обработки Общего списка")
        return f"❌ Ошибка: {exc}"


async def _process_detail(file_path: Path, update: Update) -> str:
    """Обработать Детализированный еженедельный → Артикулы."""
    try:
        parser = WbDetailParser()
        df, schema_warning = parser.parse(file_path)

        if df.empty:
            return "❌ Файл не содержит данных."

        summary = parser.summarize(df)
        data_type = summary.get("data_type", "основной")
        freq      = summary.get("freq", "weekly")
        date_from = summary.get("date_from")
        date_to   = summary.get("date_to")
        net_payout   = summary.get("net_payout", 0.0)
        gross_sales  = summary.get("gross_sales", 0.0)
        gross_returns = summary.get("gross_returns", 0.0)
        n_sales   = summary.get("n_sales", 0)
        n_returns = summary.get("n_returns", 0)
        logistics = summary.get("logistics", 0.0)
        commission = summary.get("commission_gross", 0.0)

        period_str = ""
        if date_from and date_to:
            period_str = (
                f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"
            )

        sheets_client = WbSheetsClient(sa_path=SA_PATH, spreadsheet_id=WB_SHEETS_ID)

        if data_type == "по_выкупам":
            sheets_client.update_buyouts(df)
            n_appended = 0
            n_articles = 0
            sheet_info = "По выкупам — обновлён"
        else:
            sheets_client.update_articles_current(df)
            n_appended = sheets_client.append_articles_history(df)
            n_articles = sheets_client.rebuild_articles_summary()
            sheet_info = f"Артикулы (неделя) обновлён, +{n_appended} в историю"

        # Топ-5 артикулов по выручке (только для основного)
        top_block = ""
        if data_type != "по_выкупам":
            payout_col = "К перечислению Продавцу за реализованный Товар"
            art_col    = "Артикул поставщика"
            name_col   = "Название"
            if payout_col in df.columns and art_col in df.columns:
                grp = (
                    df[df["Тип документа"] == "Продажа"]
                    .groupby(art_col)[payout_col]
                    .sum()
                    .nlargest(5)
                )
                if not grp.empty:
                    lines = []
                    for art, val in grp.items():
                        lines.append(f"   • {art}: {val:,.0f} ₽")
                    top_block = "\n🔝 <b>Топ-5 артикулов:</b>\n" + "\n".join(lines) + "\n"

        type_label = "По выкупам" if data_type == "по_выкупам" else "Основной"

        articles_summary_line = (
            f"📦 Сводка артикулов обновлена: {n_articles} SKU\n" if n_articles > 0 else ""
        )

        detail_warning_block = ""
        if schema_warning.has_changes:
            lines = []
            if schema_warning.removed:
                lines.append("Удалены: " + ", ".join(sorted(schema_warning.removed)))
            if schema_warning.added:
                lines.append("Новые: " + ", ".join(sorted(schema_warning.added)))
            detail_warning_block = "\n⚠️ <b>Схема отчёта изменилась!</b>\n" + "\n".join(lines) + "\n"

        return (
            f"✅ <b>Детальный отчёт загружен</b>\n\n"
            f"📅 Период: {period_str}\n"
            f"📋 Тип: {type_label} ({freq})\n"
            f"   Строк обработано: {len(df):,}\n"
            f"   Продаж: {n_sales} | Возвратов: {n_returns}\n\n"
            f"💰 Финансы:\n"
            f"   Продажи (к перечисл.): {gross_sales:>12,.0f} ₽\n"
            f"   Возвраты:              {gross_returns:>12,.0f} ₽\n"
            f"   К перечислению ИТОГО:  {net_payout:>12,.0f} ₽\n"
            f"   Комиссия WB:           {commission:>12,.0f} ₽\n"
            f"   Логистика:             {logistics:>12,.0f} ₽\n"
            f"{top_block}\n"
            f"📊 Sheets: {sheet_info}\n"
            f"{articles_summary_line}"
            f"{detail_warning_block}"
            f"📎 <a href='{SHEETS_URL}'>Открыть таблицу</a>"
        )

    except DetailSchemaError as exc:
        logger.warning("Не детальный отчёт: %s", exc)
        return f"❌ Файл не соответствует формату детального отчёта:\n{exc}"
    except Exception as exc:
        logger.exception("Ошибка обработки детального отчёта")
        return f"❌ Ошибка: {exc}"


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан в .env")
        sys.exit(1)
    if not WB_SHEETS_ID:
        logger.error("WB_SHEETS_ID не задан в .env")
        sys.exit(1)

    logger.info("Запуск бота...")
    logger.info("Sheets: %s", SHEETS_URL)
    if ALLOWED_IDS:
        logger.info("Разрешённые ID: %s", ALLOWED_IDS)
    else:
        logger.info("Ограничений по ID нет (добавь BOT_ALLOWED_IDS в .env)")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
