"""
MedicalDocBot — загрузка медицинских документов в Google Drive и запись в таблицу.
Отдельный Google-аккаунт, не связан с FinanceBot.
"""
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import config
from drive_manager import DriveManager
from sheets_logger import append_medical_doc_row
from vision_ocr import ocr_image_bytes
from llm_extractor import extract_fields_with_llm

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context) -> None:
    await update.message.reply_text(
        "Привет. Отправь сюда документ или фото — я загружу его в Google Drive, "
        "распознаю текст (Vision OCR) и добавлю запись в таблицу.\n\nКоманды: /start, /help"
    )


async def help_cmd(update: Update, context) -> None:
    await update.message.reply_text(
        "Отправь любой файл (документ или фото).\n\n"
        "1. Файл загружается в Google Drive.\n"
        "2. Текст распознаётся через Google Cloud Vision.\n"
        "3. Полный текст сохраняется в отдельный .txt файл на Drive.\n"
        "4. В таблицу записывается строка: ссылки, краткое содержание, дата, клиника, тип и т.д."
    )


async def handle_document(update: Update, context) -> None:
    """Обработка отправленного документа (файла)."""
    doc = update.message.document
    if not doc:
        return
    await _upload_and_log(
        update,
        context,
        file_id=doc.file_id,
        filename=doc.file_name or f"document_{doc.file_unique_id}",
        mime_type=doc.mime_type or "application/octet-stream",
        file_type="документ",
    )


async def handle_photo(update: Update, context) -> None:
    """Обработка отправленного фото (берём самое большое разрешение)."""
    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        return
    ext = "jpg"
    filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo.file_unique_id}.{ext}"
    await _upload_and_log(
        update,
        context,
        file_id=photo.file_id,
        filename=filename,
        mime_type="image/jpeg",
        file_type="фото",
    )


async def _upload_and_log(
    update: Update,
    context,
    file_id: str,
    filename: str,
    mime_type: str,
    file_type: str,
) -> None:
    drive: DriveManager = context.bot_data.get("drive_manager")
    if not drive:
        await update.message.reply_text("Ошибка: Drive не настроен.")
        return

    await update.message.reply_text("Загружаю файл...")

    # --- 1. Скачиваем файл из Telegram ---
    try:
        tg_file = await context.bot.get_file(file_id)
        file_bytes = await tg_file.download_as_bytearray()
        file_bytes = bytes(file_bytes)
    except Exception as e:
        logger.exception("Ошибка загрузки файла из Telegram")
        await update.message.reply_text(f"Не удалось получить файл: {e}")
        return

    # --- 2. Загружаем оригинал в Drive ---
    try:
        original_link = drive.upload_file_from_bytes(
            file_bytes,
            filename=filename,
            mime_type=mime_type,
        )
    except Exception as e:
        err_msg = getattr(e, "_drive_error_message", None) or str(e)
        if len(err_msg) > 500:
            err_msg = err_msg[:500] + "..."
        await update.message.reply_text(f"Ошибка загрузки в Google Drive:\n{err_msg}")
        return

    if not original_link:
        await update.message.reply_text("Ошибка загрузки в Google Drive. Проверьте настройки и логи.")
        return

    # --- 3. OCR через Vision API ---
    await update.message.reply_text("Распознаю текст (Vision OCR)...")
    ocr_text = None
    text_file_link = ""
    fields = None
    try:
        ocr_text = ocr_image_bytes(file_bytes, mime_type=mime_type)
    except Exception as e:
        logger.exception("Ошибка Vision OCR: %s", e)

    # --- 4. Сохраняем полный текст как .txt в Drive ---
    if ocr_text:
        try:
            txt_filename = _make_txt_filename(filename)
            text_file_link = drive.upload_text_as_file(
                ocr_text,
                filename=txt_filename,
            ) or ""
        except Exception as e:
            logger.exception("Ошибка загрузки .txt в Drive: %s", e)
            text_file_link = ""

        # --- 5. Извлекаем поля из текста через GPT ---
        fields = extract_fields_with_llm(ocr_text)
        if not fields:
            logger.warning("LLM extraction не сработал, поля будут пустыми")

    # --- 6. Записываем в «Медицинские документы» ---
    user = update.effective_user
    upload_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    ok = append_medical_doc_row(
        filename=filename,
        original_link=original_link,
        text_file_link=text_file_link,
        title=fields.title if fields else filename,
        summary=fields.summary if fields else "",
        upload_date=upload_date,
        document_date=fields.document_date if fields else "",
        doc_type=fields.doc_type if fields else file_type,
        doctor=fields.doctor if fields else "",
        patient=fields.patient if fields else "",
        clinic=fields.clinic if fields else "",
        direction=fields.direction if fields else "",
        diagnosis=fields.diagnosis if fields else "",
        key_indicators=fields.key_indicators if fields else "",
        recommendations=fields.recommendations if fields else "",
        telegram_user_id=user.id if user else 0,
        telegram_username=user.username if user else None,
    )

    # --- 7. Ответ пользователю ---
    title = fields.title if fields and fields.title else filename
    lines = []
    lines.append(f"\U0001F4C4 {title}")
    lines.append("")

    # Информационный блок
    info = []
    if fields and fields.doc_type:
        info.append(f"Тип: {fields.doc_type}")
    if fields and fields.direction:
        info.append(f"Направление: {fields.direction}")
    if fields and fields.document_date:
        info.append(f"Дата: {fields.document_date}")
    if fields and fields.doctor:
        info.append(f"Врач: {fields.doctor}")
    if fields and fields.patient:
        info.append(f"Пациент: {fields.patient}")
    if fields and fields.clinic:
        info.append(f"Клиника: {fields.clinic}")
    if fields and fields.diagnosis:
        info.append(f"Диагноз: {fields.diagnosis}")
    if fields and fields.recommendations:
        info.append(f"Рекомендации: {fields.recommendations}")
    if fields and fields.key_indicators:
        info.append(f"Показатели: {fields.key_indicators}")

    if info:
        lines.extend(info)
    else:
        lines.append("(данные не извлечены)")

    if fields and fields.summary:
        lines.append("")
        lines.append(f"Содержание: {fields.summary[:200]}")

    # Ссылки
    lines.append("")
    lines.append(f"Оригинал: {original_link}")
    if text_file_link:
        lines.append(f"Текст: {text_file_link}")
    if not ocr_text:
        lines.append("(текст не распознан)")
    if not ok:
        lines.append("(в таблицу записать не удалось)")

    await update.message.reply_text("\n".join(lines))


def _make_txt_filename(original: str) -> str:
    """Из 'document.jpg' сделать 'document_ocr.txt'."""
    import os
    base, _ = os.path.splitext(original)
    return f"{base}_ocr.txt"


async def post_init(app: Application) -> None:
    try:
        dm = DriveManager()
        app.bot_data["drive_manager"] = dm
        logger.info("DriveManager инициализирован")
    except Exception as e:
        logger.exception("Ошибка инициализации Drive: %s", e)
        app.bot_data["drive_manager"] = None


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("Укажите TELEGRAM_BOT_TOKEN в .env")
        return
    if not config.GOOGLE_DRIVE_FOLDER_ID:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID не задан — загрузка в Drive может не сработать")
    if not config.GOOGLE_SHEETS_ID:
        logger.warning("GOOGLE_SHEETS_ID не задан — запись в таблицу отключена")

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("MedicalDocBot запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
