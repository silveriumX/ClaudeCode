"""
Загрузка файлов в Google Drive.
Поддержка: Service Account (JSON) или OAuth.
"""
import io
import logging
import os
from typing import Optional

import config

logger = logging.getLogger(__name__)


def _build_credentials():
    """Сначала OAuth (обычная папка в «Мой диск»), при отсутствии — Service Account (нужен Shared Drive)."""
    has_oauth = all([
        getattr(config, "GOOGLE_DRIVE_REFRESH_TOKEN", None),
        getattr(config, "GOOGLE_DRIVE_CLIENT_ID", None),
        getattr(config, "GOOGLE_DRIVE_CLIENT_SECRET", None),
    ])
    if has_oauth:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials(
                token=None,
                refresh_token=config.GOOGLE_DRIVE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=config.GOOGLE_DRIVE_CLIENT_ID,
                client_secret=config.GOOGLE_DRIVE_CLIENT_SECRET,
                scopes=getattr(config, "DRIVE_OAUTH_SCOPES", None) or [config.SCOPES[0]],
            )
            creds.refresh(Request())
            logger.info("Drive: используется OAuth (обычная папка)")
            return creds, "oauth"
        except Exception as e:
            logger.error("OAuth Drive не сработал (проверь .env на VPS): %s", e)
            # пробуем Service Account дальше

    # 2) Service Account — только с Shared Drive (у SA нет квоты в обычном Drive)
    path = getattr(config, "GOOGLE_SERVICE_ACCOUNT_FILE", None) or "service_account_medical.json"
    if path and os.path.isfile(path):
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(path, scopes=config.SCOPES)
        logger.info("Drive: используется Service Account (нужен Shared Drive)")
        return creds, "sa"

    return None, None


class DriveManager:
    """Загрузка файлов в указанную папку Google Drive."""

    def __init__(self):
        self._creds, self._auth_type = _build_credentials()
        self._service = None
        if self._creds:
            from googleapiclient.discovery import build
            self._service = build("drive", "v3", credentials=self._creds)
        self.folder_id = (config.GOOGLE_DRIVE_FOLDER_ID or "").strip() or None
        if self.folder_id:
            logger.info("Drive: загрузка в папку %s", self.folder_id)

    def upload_file_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str = "application/octet-stream",
        folder_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Загрузить файл в Google Drive.
        Returns: ссылка на файл (uc?export=download&id=...) или None.
        """
        from google.auth.transport.requests import Request
        from googleapiclient.http import MediaIoBaseUpload

        if not self._service:
            logger.error("Drive: сервис не инициализирован (нужен Service Account JSON или OAuth)")
            return None

        try:
            if self._auth_type == "oauth" and (not self._creds.valid or self._creds.expired):
                self._creds.refresh(Request())

            target = folder_id or self.folder_id
            file_metadata = {"name": filename, "mimeType": mime_type}
            if target:
                file_metadata["parents"] = [target]

            media = MediaIoBaseUpload(
                io.BytesIO(file_bytes),
                mimetype=mime_type,
                resumable=True,
            )

            # OAuth — обычная папка; SA — только Shared Drive, иначе 403
            kwargs = {"body": file_metadata, "media_body": media, "fields": "id, webViewLink"}
            if self._auth_type == "sa":
                kwargs["supportsAllDrives"] = True
            file = self._service.files().create(**kwargs).execute()
            file_id = file.get("id")
            # Ссылка для просмотра в браузере (не скачивание)
            link = file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
            logger.info("Файл загружен: %s -> %s", filename, file_id)
            return link
        except Exception as e:
            logger.exception("Ошибка загрузки в Drive: %s", e)
            msg = str(e)
            if "403" in msg or "HttpError 403" in msg:
                if "storage quota" in msg.lower() or "shared drives" in msg.lower():
                    msg = (
                        "403: у Service Account нет квоты в обычной папке.\n"
                        "Варианты:\n"
                        "1) OAuth — обычная папка в «Мой диск». Запусти get_drive_refresh_token.py, добавь refresh token в .env и задеплой.\n"
                        "2) Shared Drive — создай общий диск, добавь туда папку и выдай доступ cursor@neat-geode-329707.iam.gserviceaccount.com (Редактор)."
                    )
                else:
                    msg = (
                        "403: нет доступа к папке.\n"
                        "Либо расшарь папку на cursor@neat-geode-329707.iam.gserviceaccount.com (Редактор), "
                        "либо настрой OAuth (get_drive_refresh_token.py) и укажи GOOGLE_DRIVE_FOLDER_ID обычной папки."
                    )
            setattr(e, "_drive_error_message", msg)
            raise

    def upload_text_as_file(
        self,
        text: str,
        filename: str,
        folder_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Сохранить текст как .txt файл в Google Drive.
        Returns: ссылка на файл для просмотра или None.
        """
        file_bytes = text.encode("utf-8")
        return self.upload_file_from_bytes(
            file_bytes,
            filename=filename,
            mime_type="text/plain",
            folder_id=folder_id,
        )
