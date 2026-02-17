"""
Конфигурация TelegramHub
"""
import os
from pathlib import Path

# Пути
BASE_DIR = Path(__file__).parent.parent
SERVER_DIR = BASE_DIR / "server"
ACCOUNTS_DIR = BASE_DIR / "accounts"
SESSIONS_DIR = ACCOUNTS_DIR / "sessions"
CONTEXT_DIR = BASE_DIR / "context"
DRAFTS_DIR = BASE_DIR / "drafts"

# Ayugram tdata
AYUGRAM_TDATA_PATH = Path(r"C:\Users\Admin\Documents\AyuGram\tdata")

# Telegram API credentials
# Получить на https://my.telegram.org/apps
API_ID = 32312469
API_HASH = "05af5006176e98bb3f60db45afc21d90"

# Server
HOST = "127.0.0.1"
PORT = 8765

# Sync settings
SYNC_INTERVAL_SECONDS = 60  # Как часто синхронизировать чаты
MAX_MESSAGES_PER_CHAT = 100  # Сколько сообщений загружать из каждого чата

# =============================================================================
# AI Configuration
# =============================================================================
# Supported providers: "openai", "anthropic"
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")

# API Key for AI provider
# Set via environment variable or directly here
AI_API_KEY = os.environ.get("AI_API_KEY", "")

# Model to use
# OpenAI: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
# Anthropic 2026: "claude-sonnet-4-5" (лучший для кодинга и сложных задач), "claude-opus-4-5"
# Anthropic 2024-2025: "claude-3-5-sonnet@20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-5")

# AI features toggle
AI_ENABLED = bool(AI_API_KEY)

# Custom AI instructions (Tone of Voice, style guidelines)
# These instructions will be included in every AI request
AI_CUSTOM_INSTRUCTIONS = os.getenv("AI_CUSTOM_INSTRUCTIONS", """
При написании ответов соблюдай эти правила:
- НЕ использовать длинное тире (—), только дефис (-)
- НЕ использовать двоеточие (:) без крайней необходимости
- Писать естественно, как в обычной переписке
- Быть кратким и по делу
- Адаптироваться под стиль и тон собеседника
- Избегать излишней формальности
""".strip())

# =============================================================================
# Review Mode Settings
# =============================================================================
# Minimum unread count to include chat in review
REVIEW_MIN_UNREAD = 1
# Maximum chats to process in one review session
REVIEW_MAX_CHATS = 50
# Skip groups/channels in review by default
REVIEW_SKIP_GROUPS = True

# Создание директорий
for dir_path in [ACCOUNTS_DIR, SESSIONS_DIR, CONTEXT_DIR, DRAFTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

(CONTEXT_DIR / "active_chats").mkdir(exist_ok=True)
(CONTEXT_DIR / "summaries").mkdir(exist_ok=True)
(CONTEXT_DIR / "pending_replies").mkdir(exist_ok=True)
