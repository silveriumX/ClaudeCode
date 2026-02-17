"""
Модуль для работы с Google Drive
Загрузка QR-кодов через OAuth (от имени пользователя)
"""
import logging
from typing import Optional
import io

from src import config

logger = logging.getLogger(__name__)


def _build_drive_service_and_creds():
    """
    Создать (service, oauth_creds или None).

    Приоритет:
    1. OAuth (если есть refresh_token и он валиден)
    2. Service Account (fallback -- всегда работает)
    """
    from googleapiclient.discovery import build

    # Попытка 1: OAuth (загрузка на личный Drive пользователя)
    if config.GOOGLE_DRIVE_REFRESH_TOKEN and config.GOOGLE_DRIVE_CLIENT_ID and config.GOOGLE_DRIVE_CLIENT_SECRET:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            creds = Credentials(
                token=None,
                refresh_token=config.GOOGLE_DRIVE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=config.GOOGLE_DRIVE_CLIENT_ID,
                client_secret=config.GOOGLE_DRIVE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            creds.refresh(Request())
            logger.info("Drive: OAuth connection successful")
            return build("drive", "v3", credentials=creds), creds
        except Exception as e:
            logger.warning(
                "Drive OAuth failed (%s). Falling back to Service Account.", e
            )

    # Попытка 2: Service Account (загрузка через сервисный аккаунт)
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            config.GOOGLE_SERVICE_ACCOUNT_FILE, scope
        )
        logger.info("Drive: using Service Account")
        return build("drive", "v3", credentials=creds), None
    except Exception as e:
        logger.error("Drive: Service Account also failed: %s", e)
        raise


class DriveManager:
    """Менеджер для загрузки файлов в Google Drive (OAuth или Service Account)."""

    def __init__(self):
        self.service, self._oauth_creds = _build_drive_service_and_creds()
        self.qr_codes_folder_id = config.GOOGLE_DRIVE_FOLDER_ID if config.GOOGLE_DRIVE_FOLDER_ID else None
        self._using_oauth = self._oauth_creds is not None
        if self.qr_codes_folder_id:
            logger.info("Files will be uploaded to folder: %s", self.qr_codes_folder_id)
        logger.info("Drive mode: %s", "OAuth" if self._using_oauth else "Service Account")

    def upload_file_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str = "image/jpeg",
        folder_id: str = None,
    ) -> Optional[str]:
        """
        Загрузить файл из байтов в Google Drive.

        Returns:
            Ссылка на файл или None при ошибке.
        """
        from googleapiclient.http import MediaIoBaseUpload
        from google.auth.transport.requests import Request

        try:
            if self._oauth_creds and (not self._oauth_creds.valid or self._oauth_creds.expired):
                self._oauth_creds.refresh(Request())

            logger.info("Начало загрузки файла: %s, размер: %s байт", filename, len(file_bytes))

            media = MediaIoBaseUpload(
                io.BytesIO(file_bytes),
                mimetype=mime_type,
                resumable=True,
            )

            file_metadata = {"name": filename, "mimeType": mime_type}
            target_folder = folder_id or self.qr_codes_folder_id
            if target_folder:
                file_metadata["parents"] = [target_folder]
                logger.info("Upload to folder: %s", target_folder)

            logger.info("Sending file to Google Drive...")
            try:
                file = (
                    self.service.files()
                    .create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, webViewLink, webContentLink",
                    )
                    .execute()
                )
            except Exception as folder_err:
                # If folder upload fails (e.g. no access), try without folder
                if target_folder:
                    logger.warning(
                        "Upload to folder failed (%s). Retrying without folder...",
                        folder_err
                    )
                    file_metadata.pop("parents", None)
                    media = MediaIoBaseUpload(
                        io.BytesIO(file_bytes),
                        mimetype=mime_type,
                        resumable=True,
                    )
                    file = (
                        self.service.files()
                        .create(
                            body=file_metadata,
                            media_body=media,
                            fields="id, webViewLink, webContentLink",
                        )
                        .execute()
                    )
                else:
                    raise

            file_id = file.get("id")
            logger.info("Файл загружен, ID: %s", file_id)

            # Доступ по ссылке (anyone with link)
            permission = {"type": "anyone", "role": "reader"}
            self.service.permissions().create(fileId=file_id, body=permission).execute()

            download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
            logger.info("Файл успешно загружен: %s (ID: %s)", filename, file_id)
            return download_link

        except Exception as e:
            logger.error("Ошибка загрузки в Google Drive: %s", e)
            logger.error("Файл: %s, размер: %s байт", filename, len(file_bytes) if file_bytes else 0)
            import traceback
            logger.error(traceback.format_exc())
            return None

    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> Optional[str]:
        """Создать папку в Google Drive."""
        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]

            folder = self.service.files().create(body=file_metadata, fields="id").execute()
            folder_id = folder.get("id")
            logger.info("Папка создана: %s (ID: %s)", folder_name, folder_id)
            return folder_id
        except Exception as e:
            logger.error("Ошибка создания папки: %s", e)
            return None

    def set_qr_codes_folder(self, folder_id: str):
        """Установить ID папки для QR-кодов."""
        self.qr_codes_folder_id = folder_id
        logger.info("Папка для QR-кодов: %s", folder_id)

    def upload_receipt(self, file_bytes: bytes, filename: str,
                       mime_type: str = "image/jpeg") -> Optional[str]:
        """
        Загрузить чек (фото или PDF) в Google Drive.

        Использует ту же папку что и QR-коды (GOOGLE_DRIVE_FOLDER_ID).
        Можно создать подпапку "Чеки" при необходимости.

        Args:
            file_bytes: Содержимое файла
            filename: Имя файла (с расширением)
            mime_type: MIME-тип (image/jpeg, image/png, application/pdf)

        Returns:
            Ссылка на файл или None при ошибке
        """
        logger.info("Uploading receipt: %s (%d bytes)", filename, len(file_bytes))
        return self.upload_file_from_bytes(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
            folder_id=self.qr_codes_folder_id
        )
