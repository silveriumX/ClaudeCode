"""
Запись строк о загруженных файлах в Google Таблицу.
Поддержка: Service Account (JSON) или OAuth.
"""
import logging
import os
from datetime import datetime
from typing import Optional, List

import config

logger = logging.getLogger(__name__)

# Эталонные заголовки — единственный источник правды
MEDICAL_DOC_HEADERS: List[str] = [
    "Дата загрузки",
    "Название",
    "Тип документа",
    "Дата документа",
    "Врач",
    "Пациент",
    "Клиника / Учреждение",
    "Направление",
    "Диагноз",
    "Краткое содержание",
    "Ключевые показатели",
    "Рекомендации",
    "Оригинал файла",
    "Распознанный текст",
    "Имя файла",
    "Telegram ID",
    "Username",
]


def _get_credentials():
    """Сначала Service Account, при отсутствии - OAuth."""
    path = getattr(config, "GOOGLE_SERVICE_ACCOUNT_FILE", None) or "service_account_medical.json"
    if path and os.path.isfile(path):
        from google.oauth2.service_account import Credentials
        return Credentials.from_service_account_file(path, scopes=config.SCOPES)
    if all([config.GOOGLE_REFRESH_TOKEN, config.GOOGLE_CLIENT_ID, config.GOOGLE_CLIENT_SECRET]):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials(
            token=None,
            refresh_token=config.GOOGLE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            scopes=config.SCOPES,
        )
        creds.refresh(Request())
        return creds
    return None


def _ensure_sheet_with_headers(spreadsheet, sheet_name: str, headers: List[str]):
    """
    Получить лист с правильными заголовками.
    Если лист не существует - создать.
    Если заголовки не совпадают - переименовать старый в _archive, создать новый.
    """
    import gspread

    try:
        sheet = spreadsheet.worksheet(sheet_name)
        # Проверяем заголовки
        existing = sheet.row_values(1)
        if existing != headers:
            logger.warning(
                "Заголовки листа '%s' устарели (%d колонок -> %d). Архивирую старый лист.",
                sheet_name, len(existing), len(headers),
            )
            # Переименовываем старый лист
            archive_name = f"{sheet_name}_archive_{datetime.now().strftime('%Y%m%d_%H%M')}"
            sheet.update_title(archive_name)
            # Создаём новый с правильными заголовками
            sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
            sheet.append_row(headers, value_input_option="RAW")
            logger.info("Создан новый лист '%s' с %d колонками", sheet_name, len(headers))
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
        sheet.append_row(headers, value_input_option="RAW")
        logger.info("Создан лист '%s' с заголовками (%d колонок)", sheet_name, len(headers))
        return sheet


def append_medical_doc_row(
    filename: str,
    original_link: str,
    text_file_link: str,
    title: str,
    summary: str,
    upload_date: str,
    document_date: str,
    doc_type: str,
    doctor: str,
    patient: str,
    clinic: str,
    direction: str,
    diagnosis: str,
    key_indicators: str,
    recommendations: str,
    telegram_user_id: int,
    telegram_username: Optional[str],
) -> bool:
    """
    Добавить строку в лист 'Медицинские документы'.
    Автоматически проверяет и исправляет заголовки.
    """
    if not config.GOOGLE_SHEETS_ID:
        logger.error("GOOGLE_SHEETS_ID не задан")
        return False

    try:
        import gspread
        creds = _get_credentials()
        if not creds:
            logger.error("Нет credentials для Sheets")
            return False

        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config.GOOGLE_SHEETS_ID)

        sheet_name = getattr(config, "SHEET_NAME_MEDICAL_DOCS", "Медицинские документы")
        sheet = _ensure_sheet_with_headers(spreadsheet, sheet_name, MEDICAL_DOC_HEADERS)

        row = [
            upload_date,
            title,
            doc_type,
            document_date,
            doctor,
            patient,
            clinic,
            direction,
            diagnosis,
            summary,
            key_indicators,
            recommendations,
            original_link,
            text_file_link or "",
            filename,
            str(telegram_user_id),
            telegram_username or "",
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Строка добавлена в '%s': %s", sheet_name, title or filename)
        return True
    except Exception as e:
        logger.error("Ошибка записи в Sheets: %s", e)
        return False
