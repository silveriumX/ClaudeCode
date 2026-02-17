import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Union

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GoogleApiManager")

class GoogleApiManager:
    """
    Универсальный менеджер для работы с Google Sheets и Google Drive.
    Обеспечивает централизованное управление подключениями и кэширование объектов API.
    """

    def __init__(self, credentials_path: Optional[str] = None, spreadsheet_id: Optional[str] = None):
        """
        Инициализация менеджера.

        Args:
            credentials_path: Путь к JSON файлу сервисного аккаунта.
                             Если None, ищет в переменной окружения GOOGLE_SERVICE_ACCOUNT_FILE.
            spreadsheet_id: ID таблицы Google Sheets.
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_ID')

        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        self._creds = None
        self._gc = None
        self._spreadsheet = None
        self._drive_service = None
        self._sheets_service = None

    @property
    def creds(self):
        if not self._creds:
            creds_path = Path(self.credentials_path)
            if not creds_path.exists():
                # Попытка найти файл в корне воркспейса, если путь относительный
                alt_path = Path(__file__).resolve().parent.parent / self.credentials_path
                if alt_path.exists():
                    creds_path = alt_path
                else:
                    raise FileNotFoundError(f"Файл учетных данных не найден: {self.credentials_path}")

            self._creds = ServiceAccountCredentials.from_json_keyfile_name(str(creds_path), self.scopes)
        return self._creds

    @property
    def gc(self):
        """Клиент gspread (высокоуровневый для Sheets)"""
        if not self._gc:
            self._gc = gspread.authorize(self.creds)
        return self._gc

    @property
    def spreadsheet(self):
        """Объект таблицы gspread"""
        if not self._spreadsheet:
            if not self.spreadsheet_id:
                raise ValueError("spreadsheet_id не задан")
            self._spreadsheet = self.gc.open_by_key(self.spreadsheet_id)
        return self._spreadsheet

    @property
    def drive(self):
        """Сервис Google Drive (низкоуровневый v3)"""
        if not self._drive_service:
            self._drive_service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
        return self._drive_service

    # --- Методы для работы с Google Sheets (gspread) ---

    def get_worksheet(self, name: str):
        """Получить объект листа по имени"""
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Лист '{name}' не найден в таблице {self.spreadsheet_id}")
            raise

    def get_all_records(self, sheet_name: str) -> List[Dict]:
        """Получить все записи из листа в виде списка словарей"""
        return self.get_worksheet(sheet_name).get_all_records()

    def append_row(self, sheet_name: str, row: List[Any], value_input_option: str = 'USER_ENTERED'):
        """Добавить строку в конец листа"""
        return self.get_worksheet(sheet_name).append_row(row, value_input_option=value_input_option)

    def update_cell(self, sheet_name: str, row: int, col: int, value: Any):
        """Обновить конкретную ячейку"""
        return self.get_worksheet(sheet_name).update_cell(row, col, value)

    # --- Методы для работы с Google Drive ---

    def upload_file(self, local_path: Union[str, Path], folder_id: Optional[str] = None, mimetype: Optional[str] = None) -> str:
        """
        Загрузить локальный файл на Google Drive.

        Returns:
            ID загруженного файла.
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Локальный файл не найден: {local_path}")

        file_metadata = {'name': local_path.name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(str(local_path), mimetype=mimetype, resumable=True)
        file = self.drive.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"Файл {local_path.name} успешно загружен на Drive. ID: {file.get('id')}")
        return file.get('id')

    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Создать папку на Google Drive"""
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        file = self.drive.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')

    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """Список файлов в конкретной папке"""
        query = f"'{folder_id}' in parents and trashed = false"
        results = self.drive.files().list(q=query, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])

    def share_file(self, file_id: str, email: str, role: str = 'reader', type: str = 'user'):
        """Открыть доступ к файлу/папке"""
        user_permission = {
            'type': type,
            'role': role,
            'emailAddress': email
        }
        return self.drive.permissions().create(fileId=file_id, body=user_permission, fields='id').execute()

# Пример использования (для тестирования)
if __name__ == "__main__":
    # Этот блок сработает только при прямом запуске файла
    try:
        # Пытаемся инициализироваться с дефолтными настройками из .env
        manager = GoogleApiManager()
        print("GoogleApiManager успешно инициализирован")
    except Exception as e:
        print(f"Ошибка при инициализации: {e}")
