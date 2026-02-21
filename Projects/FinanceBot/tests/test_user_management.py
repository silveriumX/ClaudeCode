"""
Тесты управления пользователями — pytest формат
================================================
Это первый тест-файл в новом стиле (pytest + pytest-asyncio).
Все новые тесты пишем сюда или в аналогичные файлы.

Запуск: inv test  (или: .venv/Scripts/python -m pytest tests/test_user_management.py -v)
"""
import pytest
from unittest.mock import MagicMock, call

from src import config
from src.sheets import SheetsManager


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_sheets_with_users(users: list[dict]) -> SheetsManager:
    """
    Создать SheetsManager с замоканным листом пользователей.

    Args:
        users: список dict с ключами: telegram_id, name, role
               пример: [{"telegram_id": 111, "name": "Иван", "role": "Владелец"}]

    Returns:
        SheetsManager с настроенным users_sheet моком.

    Side effects:
        - Мокает users_sheet.get_all_values() возвращая заголовок + строки из users.
        - НЕ подключается к Google Sheets.
    """
    sheets = SheetsManager.__new__(SheetsManager)
    ws = MagicMock()

    header = ["Telegram ID", "Имя", "Username", "Роль"]
    rows = [[str(u["telegram_id"]), u["name"], "", u["role"]] for u in users]
    ws.get_all_values.return_value = [header] + rows

    sheets.users_sheet = ws
    sheets._user_cache = {}
    sheets._hdr_cache = {}
    return sheets


# ── sheets.deactivate_user ─────────────────────────────────────────────────────

class TestDeactivateUser:
    """
    Поведение: deactivate_user очищает ячейку роли, строка остаётся.

    Контракт (согласован 2026-02-19):
    - Строка НЕ удаляется из таблицы.
    - Только ячейка роли очищается пустой строкой "".
    - После деактивации get_user_role() → None (доступ заблокирован).
    - При несуществующем TID возвращает False.
    """

    def test_given_active_user_when_deactivated_then_role_cell_is_cleared(self):
        """Роль очищается через update_cell("") — не delete_rows."""
        sheets = make_sheets_with_users([
            {"telegram_id": 111, "name": "Иван", "role": "Владелец"},
        ])

        result = sheets.deactivate_user(111)

        assert result is True
        # Строка НЕ удалена
        assert not sheets.users_sheet.delete_rows.called
        # Ячейка роли (колонка 4) очищена пустой строкой
        sheets.users_sheet.update_cell.assert_called_once_with(2, 4, "")

    def test_given_active_user_when_deactivated_then_row_is_preserved(self):
        """Количество строк в таблице не меняется."""
        sheets = make_sheets_with_users([
            {"telegram_id": 222, "name": "Мария", "role": "Менеджер"},
        ])

        sheets.deactivate_user(222)

        # delete_rows не вызывался — строка на месте
        sheets.users_sheet.delete_rows.assert_not_called()

    def test_given_nonexistent_user_when_deactivated_then_returns_false(self):
        """Несуществующий TID → False."""
        sheets = make_sheets_with_users([
            {"telegram_id": 111, "name": "Иван", "role": "Владелец"},
        ])

        result = sheets.deactivate_user(99999)

        assert result is False
        sheets.users_sheet.update_cell.assert_not_called()

    def test_given_no_users_sheet_when_deactivated_then_returns_false(self):
        """Если лист недоступен — False без исключений."""
        sheets = SheetsManager.__new__(SheetsManager)
        sheets.users_sheet = None

        result = sheets.deactivate_user(111)

        assert result is False


# ── sheets.update_user_role ───────────────────────────────────────────────────

class TestUpdateUserRole:
    """Поведение: update_user_role меняет роль пользователя в таблице."""

    def test_given_existing_user_when_role_changed_then_update_cell_called(self):
        """Роль обновляется через update_cell с русским названием."""
        sheets = make_sheets_with_users([
            {"telegram_id": 333, "name": "Пётр", "role": "Менеджер"},
        ])

        result = sheets.update_user_role(333, "Исполнитель")

        assert result is True
        sheets.users_sheet.update_cell.assert_called_once_with(2, 4, "Исполнитель")

    def test_given_scientific_notation_tid_when_role_changed_then_success(self):
        """Google Sheets хранит большие ID как 8.45E+09 — должно работать."""
        sheets = SheetsManager.__new__(SheetsManager)
        ws = MagicMock()
        # Google Sheets возвращает научную нотацию для больших TID
        ws.get_all_values.return_value = [
            ["Telegram ID", "Имя", "Username", "Роль"],
            ["8.45E+09", "Константин", "", "Менеджер"],
        ]
        sheets.users_sheet = ws
        sheets._user_cache = {}
        sheets._hdr_cache = {}

        result = sheets.update_user_role(8450000000, "Владелец")

        assert result is True


# ── sheets.get_all_users ──────────────────────────────────────────────────────

class TestGetAllUsers:
    """Поведение: get_all_users возвращает список всех пользователей."""

    def test_returns_all_users_with_correct_fields(self):
        """Каждый пользователь содержит telegram_id, name, role."""
        sheets = make_sheets_with_users([
            {"telegram_id": 111, "name": "Иван", "role": "Владелец"},
            {"telegram_id": 222, "name": "Мария", "role": "Менеджер"},
        ])

        users = sheets.get_all_users()

        assert len(users) == 2
        assert users[0]["telegram_id"] == 111
        assert users[0]["role"] == config.ROLE_OWNER
        assert users[1]["telegram_id"] == 222
        assert users[1]["role"] == config.ROLE_MANAGER

    def test_empty_sheet_returns_empty_list(self):
        """Пустой лист → []."""
        sheets = SheetsManager.__new__(SheetsManager)
        ws = MagicMock()
        ws.get_all_values.return_value = [
            ["Telegram ID", "Имя", "Username", "Роль"]  # только заголовок
        ]
        sheets.users_sheet = ws

        result = sheets.get_all_users()

        assert result == []

    def test_no_sheet_returns_empty_list(self):
        """users_sheet=None → [] без исключений."""
        sheets = SheetsManager.__new__(SheetsManager)
        sheets.users_sheet = None

        result = sheets.get_all_users()

        assert result == []


# ── Owner Panel — access control ──────────────────────────────────────────────

class TestOwnerUsersAccessControl:
    """Безопасность: только owner может открыть управление пользователями."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_non_owner_roles_are_denied(self, mock_sheets):
        """manager, executor, report — все получают отказ."""
        from unittest.mock import AsyncMock
        from src.handlers.owner import owner_users

        for role in [config.ROLE_MANAGER, config.ROLE_EXECUTOR, config.ROLE_REPORT]:
            mock_sheets.get_user_role.return_value = role
            mock_sheets.get_all_users = MagicMock()

            update = MagicMock()
            update.message = AsyncMock()
            update.effective_user = MagicMock(id=999)

            context = MagicMock()
            context.bot_data = {"sheets": mock_sheets}

            await owner_users(update, context)

            # get_all_users не должен был вызваться
            assert not mock_sheets.get_all_users.called, \
                f"Роль {role!r}: get_all_users был вызван несмотря на блокировку"

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_owner_can_access_user_management(self, mock_sheets):
        """owner получает список пользователей."""
        from unittest.mock import AsyncMock
        from src.handlers.owner import owner_users

        mock_sheets.get_user_role.return_value = config.ROLE_OWNER
        mock_sheets.get_all_users.return_value = []

        update = MagicMock()
        update.message = AsyncMock()
        update.effective_user = MagicMock(id=100)

        context = MagicMock()
        context.bot_data = {"sheets": mock_sheets}

        await owner_users(update, context)

        mock_sheets.get_all_users.assert_called_once()
