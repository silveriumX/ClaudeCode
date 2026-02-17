"""
Конфигурация ChatManager Bot
"""
import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# Telegram Control Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# UserBot (Pyrogram)
USERBOT_API_ID = os.getenv('USERBOT_API_ID')
USERBOT_API_HASH = os.getenv('USERBOT_API_HASH')
USERBOT_SESSION = os.getenv('USERBOT_SESSION', 'chat_admin')

# Google Sheets
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')

# Названия листов
SHEET_USERS = 'Пользователи'
SHEET_CHATS = 'Чаты'
SHEET_PARTICIPANTS = 'Участники'

# Роли пользователей
ROLE_ADMIN = 'admin'
ROLE_MANAGER = 'manager'
ROLE_MEMBER = 'member'

# Статусы пользователей
USER_STATUS_ACTIVE = 'active'
USER_STATUS_BLOCKED = 'blocked'

# Статусы запросов на создание чата
CHAT_STATUS_PENDING = 'pending'
CHAT_STATUS_CREATING = 'creating'
CHAT_STATUS_CREATED = 'created'
CHAT_STATUS_FAILED = 'failed'
CHAT_STATUS_ARCHIVED = 'archived'

# Роли в чате
CHAT_ROLE_CREATOR = 'creator'
CHAT_ROLE_ADMIN = 'admin'
CHAT_ROLE_MEMBER = 'member'

# Настройки поведения
CHAT_POLL_INTERVAL = int(os.getenv('CHAT_POLL_INTERVAL', '10'))  # Интервал проверки Sheets (сек)
AUTO_APPROVE_ROLES = [ROLE_ADMIN, ROLE_MANAGER]  # Роли с автоматическим одобрением
REQUIRE_APPROVAL = os.getenv('REQUIRE_APPROVAL', 'False').lower() == 'true'  # Требуется ли одобрение

# Права участников по умолчанию
DEFAULT_CHAT_PERMISSIONS = {
    'can_send_messages': True,
    'can_send_media': True,
    'can_send_polls': False,
    'can_send_other_messages': True,
    'can_add_web_page_previews': True,
    'can_change_info': False,
    'can_invite_users': False,
    'can_pin_messages': False
}

# Ограничения
MAX_CHAT_TITLE_LEN = 255
MAX_CHAT_DESCRIPTION_LEN = 255
MAX_CHATS_PER_HOUR = 10  # Защита от спама
