"""
Модуль для работы с Google Sheets
ChatManager - управление чатами через Google Sheets
"""
from datetime import datetime
from typing import Optional, List, Dict
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config
import logging

logger = logging.getLogger(__name__)


class GoogleApiManager:
    """Базовый класс для работы с Google API"""

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id

        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            credentials_path, scope)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)

    def get_worksheet(self, sheet_name: str):
        """Получить лист по названию"""
        return self.spreadsheet.worksheet(sheet_name)


class ChatSheetsManager(GoogleApiManager):
    """
    Менеджер для работы с таблицами ChatManager

    Листы:
    - Пользователи: telegram_id | имя | username | роль | статус
    - Чаты: id | название | creator_id | дата_создания | статус | invite_link | chat_id
    - Участники: chat_id | user_id | роль_в_чате | дата_добавления
    """

    def __init__(self):
        super().__init__(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            spreadsheet_id=config.GOOGLE_SHEETS_ID
        )

        # Инициализация листов
        try:
            self.users_sheet = self.get_worksheet(config.SHEET_USERS)
            self.chats_sheet = self.get_worksheet(config.SHEET_CHATS)
            self.participants_sheet = self.get_worksheet(config.SHEET_PARTICIPANTS)
        except Exception as e:
            logger.error(f"Failed to initialize sheets: {e}")
            raise

    # === ПОЛЬЗОВАТЕЛИ ===

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """
        Получить информацию о пользователе

        Returns:
            Dict с полями: telegram_id, name, username, role, status
            или None если не найден
        """
        try:
            records = self.users_sheet.get_all_records()
            for record in records:
                if str(record.get('telegram_id', '')) == str(telegram_id):
                    return {
                        'telegram_id': record.get('telegram_id'),
                        'name': record.get('имя', ''),
                        'username': record.get('username', ''),
                        'role': record.get('роль', ''),
                        'status': record.get('статус', config.USER_STATUS_ACTIVE)
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None

    def get_user_role(self, telegram_id: int) -> Optional[str]:
        """Получить роль пользователя"""
        user = self.get_user(telegram_id)
        return user['role'] if user else None

    def is_user_active(self, telegram_id: int) -> bool:
        """Проверить, активен ли пользователь"""
        user = self.get_user(telegram_id)
        if not user:
            return False
        return user.get('status', '').lower() == config.USER_STATUS_ACTIVE

    def add_user(self, telegram_id: int, name: str, username: str = '',
                 role: str = config.ROLE_MEMBER) -> bool:
        """
        Добавить нового пользователя

        Returns:
            True если успешно, False при ошибке
        """
        try:
            # Проверяем, не существует ли уже
            if self.get_user(telegram_id):
                logger.warning(f"User {telegram_id} already exists")
                return False

            # Добавляем строку
            row = [
                telegram_id,
                name,
                username,
                role,
                config.USER_STATUS_ACTIVE
            ]
            self.users_sheet.append_row(row)
            logger.info(f"Added user {telegram_id} with role {role}")
            return True
        except Exception as e:
            logger.error(f"Error adding user {telegram_id}: {e}")
            return False

    # === ЧАТЫ ===

    def create_chat_request(self, creator_id: int, chat_title: str,
                           description: str = '') -> Optional[str]:
        """
        Создать запрос на создание чата

        Args:
            creator_id: Telegram ID создателя
            chat_title: Название чата
            description: Описание чата (опционально)

        Returns:
            ID запроса (уникальная строка) или None при ошибке
        """
        try:
            # Генерируем ID запроса: REQ-YYYYMMDD-HHMMSS-XXX
            import uuid
            now = datetime.now()
            request_id = f"REQ-{now.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:3]}"

            # Добавляем строку в лист Чаты
            row = [
                request_id,                          # id
                chat_title,                          # название
                creator_id,                          # creator_id
                now.strftime('%d.%m.%Y %H:%M:%S'),  # дата_создания
                config.CHAT_STATUS_PENDING,          # статус
                '',                                  # invite_link (пусто)
                '',                                  # chat_id (пусто)
                description                          # описание
            ]
            self.chats_sheet.append_row(row)
            logger.info(f"Created chat request {request_id} by user {creator_id}")
            return request_id
        except Exception as e:
            logger.error(f"Error creating chat request: {e}")
            return None

    def get_pending_chat_requests(self) -> List[Dict]:
        """
        Получить все запросы со статусом 'pending'

        Returns:
            List of dicts с полями: id, title, creator_id, date, description, row_index
        """
        try:
            records = self.chats_sheet.get_all_records()
            pending = []

            for idx, record in enumerate(records, start=2):  # start=2 (заголовок в строке 1)
                if record.get('статус', '') == config.CHAT_STATUS_PENDING:
                    pending.append({
                        'id': record.get('id'),
                        'title': record.get('название', ''),
                        'creator_id': record.get('creator_id'),
                        'date': record.get('дата_создания', ''),
                        'description': record.get('описание', ''),
                        'row_index': idx
                    })

            return pending
        except Exception as e:
            logger.error(f"Error getting pending chat requests: {e}")
            return []

    def update_chat_created(self, request_id: str, chat_id: int,
                           invite_link: str) -> bool:
        """
        Обновить запрос после создания чата

        Args:
            request_id: ID запроса
            chat_id: Telegram chat_id созданного чата
            invite_link: Invite link для приглашения

        Returns:
            True если успешно, False при ошибке
        """
        try:
            # Находим строку с request_id
            records = self.chats_sheet.get_all_records()
            for idx, record in enumerate(records, start=2):
                if record.get('id') == request_id:
                    # Обновляем статус, chat_id, invite_link
                    self.chats_sheet.update_cell(idx, 5, config.CHAT_STATUS_CREATED)  # статус
                    self.chats_sheet.update_cell(idx, 6, invite_link)  # invite_link
                    self.chats_sheet.update_cell(idx, 7, chat_id)  # chat_id

                    logger.info(f"Updated chat request {request_id} to created")
                    return True

            logger.warning(f"Chat request {request_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating chat request {request_id}: {e}")
            return False

    def update_chat_failed(self, request_id: str, error_message: str = '') -> bool:
        """
        Обновить запрос при ошибке создания

        Args:
            request_id: ID запроса
            error_message: Сообщение об ошибке

        Returns:
            True если успешно
        """
        try:
            records = self.chats_sheet.get_all_records()
            for idx, record in enumerate(records, start=2):
                if record.get('id') == request_id:
                    self.chats_sheet.update_cell(idx, 5, config.CHAT_STATUS_FAILED)
                    if error_message:
                        # Записываем ошибку в описание
                        current_desc = record.get('описание', '')
                        new_desc = f"{current_desc}\n[ERROR] {error_message}" if current_desc else f"[ERROR] {error_message}"
                        self.chats_sheet.update_cell(idx, 8, new_desc)

                    logger.info(f"Marked chat request {request_id} as failed")
                    return True

            return False
        except Exception as e:
            logger.error(f"Error marking chat request {request_id} as failed: {e}")
            return False

    def get_user_chats(self, user_id: int) -> List[Dict]:
        """
        Получить все чаты пользователя (где он создатель)

        Returns:
            List of dicts с полями: id, title, status, invite_link, date
        """
        try:
            records = self.chats_sheet.get_all_records()
            user_chats = []

            for record in records:
                if str(record.get('creator_id', '')) == str(user_id):
                    user_chats.append({
                        'id': record.get('id'),
                        'title': record.get('название', ''),
                        'status': record.get('статус', ''),
                        'invite_link': record.get('invite_link', ''),
                        'date': record.get('дата_создания', ''),
                        'chat_id': record.get('chat_id', '')
                    })

            return user_chats
        except Exception as e:
            logger.error(f"Error getting user chats for {user_id}: {e}")
            return []

    # === УЧАСТНИКИ ===

    def add_participant(self, chat_id: int, user_id: int,
                       role: str = config.CHAT_ROLE_MEMBER) -> bool:
        """
        Добавить участника в чат

        Args:
            chat_id: Telegram chat_id
            user_id: Telegram user_id
            role: Роль в чате (creator/admin/member)

        Returns:
            True если успешно
        """
        try:
            now = datetime.now()
            row = [
                chat_id,
                user_id,
                role,
                now.strftime('%d.%m.%Y %H:%M:%S')
            ]
            self.participants_sheet.append_row(row)
            logger.info(f"Added participant {user_id} to chat {chat_id} with role {role}")
            return True
        except Exception as e:
            logger.error(f"Error adding participant {user_id} to chat {chat_id}: {e}")
            return False

    def get_chat_participants(self, chat_id: int) -> List[Dict]:
        """
        Получить всех участников чата

        Returns:
            List of dicts: user_id, role, date
        """
        try:
            records = self.participants_sheet.get_all_records()
            participants = []

            for record in records:
                if str(record.get('chat_id', '')) == str(chat_id):
                    participants.append({
                        'user_id': record.get('user_id'),
                        'role': record.get('роль_в_чате', config.CHAT_ROLE_MEMBER),
                        'date': record.get('дата_добавления', '')
                    })

            return participants
        except Exception as e:
            logger.error(f"Error getting participants for chat {chat_id}: {e}")
            return []
