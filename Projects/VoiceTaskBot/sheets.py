"""
Google Sheets integration for VoiceTaskBot.
Schema: ID | Дата | Задача | Статус
"""
import logging
from datetime import date
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Задачи"
HEADERS = ["ID", "Дата", "Задача", "Статус"]
STATUS_NEW = "Новая"
STATUS_IN_PROGRESS = "В работе"
STATUS_DONE = "Выполнена"


class TaskSheets:
    def __init__(self, credentials_path: str, spreadsheet_id: str) -> None:
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        self.spreadsheet = client.open_by_key(spreadsheet_id)
        self.sheet = self._get_or_create_sheet()

    def _get_or_create_sheet(self) -> gspread.Worksheet:
        """Получить лист с правильной схемой, архивировав старый если нужно."""
        try:
            ws = self.spreadsheet.worksheet(SHEET_NAME)
            existing = ws.row_values(1)
            if existing != HEADERS:
                # Архивируем старый лист
                archive_name = f"{SHEET_NAME} (архив)"
                try:
                    ws.update_title(archive_name)
                    logger.info(f"Archived '{SHEET_NAME}' → '{archive_name}'")
                except Exception:
                    pass
                ws = self.spreadsheet.add_worksheet(SHEET_NAME, rows=1000, cols=len(HEADERS))
                ws.append_row(HEADERS)
        except gspread.exceptions.WorksheetNotFound:
            # Архивируем старый «Входящие» если есть
            try:
                old = self.spreadsheet.worksheet("Входящие")
                old.update_title("Входящие (архив)")
                logger.info("Archived 'Входящие' → 'Входящие (архив)'")
            except Exception:
                pass
            ws = self.spreadsheet.add_worksheet(SHEET_NAME, rows=1000, cols=len(HEADERS))
            ws.append_row(HEADERS)
            logger.info(f"Created sheet '{SHEET_NAME}'")
        return ws

    def _next_id(self) -> int:
        ids = self.sheet.col_values(1)[1:]  # skip header
        if not ids:
            return 1
        numeric = [int(x) for x in ids if str(x).strip().isdigit()]
        return max(numeric) + 1 if numeric else len(ids) + 1

    def _find_row(self, task_id: int) -> Optional[int]:
        """Номер строки для task_id (1-indexed). None если не найден."""
        col = self.sheet.col_values(1)
        for i, val in enumerate(col):
            if str(val) == str(task_id):
                return i + 1
        return None

    def append_tasks(self, tasks: list[str]) -> list[int]:
        """Добавить задачи в таблицу. Возвращает список созданных ID."""
        today = date.today().strftime("%d.%m.%Y")
        start_id = self._next_id()
        rows = [[start_id + i, today, text, STATUS_NEW] for i, text in enumerate(tasks)]
        if rows:
            self.sheet.append_rows(rows, value_input_option="USER_ENTERED")
            logger.info(f"Добавлено {len(rows)} задач в Sheets")
        return [start_id + i for i in range(len(tasks))]

    def get_active_tasks(self) -> list[dict]:
        """Все задачи кроме выполненных."""
        try:
            return [r for r in self.sheet.get_all_records() if r.get("Статус") != STATUS_DONE]
        except Exception as e:
            logger.exception(f"Ошибка чтения Sheets: {e}")
            return []

    def get_pending_tasks(self) -> list[dict]:
        """Задачи со статусом Новая."""
        try:
            return [r for r in self.sheet.get_all_records() if r.get("Статус") == STATUS_NEW]
        except Exception as e:
            logger.exception(f"Ошибка чтения Sheets: {e}")
            return []

    def set_status(self, task_id: int, status: str) -> bool:
        """Изменить статус задачи."""
        row = self._find_row(task_id)
        if not row:
            return False
        col = HEADERS.index("Статус") + 1
        self.sheet.update_cell(row, col, status)
        logger.info(f"Task {task_id} → {status}")
        return True

    def update_task(self, task_id: int, new_text: str) -> bool:
        """Обновить текст задачи."""
        row = self._find_row(task_id)
        if not row:
            return False
        col = HEADERS.index("Задача") + 1
        self.sheet.update_cell(row, col, new_text)
        logger.info(f"Task {task_id} updated")
        return True

    def delete_task(self, task_id: int) -> bool:
        """Удалить задачу из таблицы."""
        row = self._find_row(task_id)
        if not row:
            return False
        self.sheet.delete_rows(row)
        logger.info(f"Task {task_id} deleted")
        return True
