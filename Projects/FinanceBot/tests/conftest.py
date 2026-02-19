"""
FinanceBot — pytest конфигурация и fixtures
============================================
Инфраструктура для тестирования PTB (python-telegram-bot) хендлеров.

Ключевые решения (из исследования PTB v20+ testing):
- pytest-asyncio==0.21.x  — НЕ обновлять выше, PTB сам не обновился (PR #4607: 330 падений)
- asyncio_mode="auto"      — не нужно @pytest.mark.asyncio на каждом тесте
- OfflineRequest           — блокирует любые сетевые вызовы, тесты 100% offline
- ApplicationBuilder().updater(None) — не вызывает getMe() при initialize()
- session-scoped event_loop — без этого session-scoped fixtures вызывают ScopeMismatch
- WindowsSelectorEventLoopPolicy — предотвращает "Event loop closed" на Windows
"""
import asyncio
import datetime
import sys
from typing import Optional
from unittest.mock import AsyncMock

import pytest
from telegram import Bot, CallbackQuery, Chat, Message, MessageEntity, Update, User
from telegram.ext import Application, ApplicationBuilder
from telegram.request import BaseRequest


# ── Исключить legacy-тесты (кастомный runner, несовместим с pytest) ────────────
# Эти файлы запускаются через: inv test-legacy
collect_ignore = [
    "comprehensive_test.py",
    "test_suite.py",
    "test_usdt_and_structure.py",
    "test_block4_users.py",
    "test_usdt_fixes.py",
]


# ── Offline Bot — никогда не обращается к Telegram API ────────────────────────

class OfflineRequest(BaseRequest):
    """Блокирует все сетевые вызовы. Падает с pytest.fail при любом запросе."""

    def __init__(self, *args, **kwargs):
        pass

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    @property
    def read_timeout(self) -> float:
        return 1.0

    async def do_request(self, url, method, request_data=None,
                         read_timeout=None, write_timeout=None,
                         connect_timeout=None, pool_timeout=None):
        pytest.fail(f"OfflineRequest: неожиданный сетевой вызов — {method} {url}")


# ── Event Loop (для pytest-asyncio 0.21.x) ────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """
    Session-scoped event loop.

    Side effects:
        - На Windows принудительно устанавливает WindowsSelectorEventLoopPolicy
          чтобы избежать "Event loop is closed" после shutdown PTB.
        - Без этой фикстуры session-scoped async fixtures вызывают ScopeMismatch.

    Invariants:
        - Цикл создаётся один раз на всю тест-сессию.
        - Закрывается после завершения последнего теста.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ── Bot Fixtures ──────────────────────────────────────────────────────────────

FAKE_TOKEN = "1234567890:AABBCCDDEEFFaabbccddeeff-FakeTokenForTests"


@pytest.fixture(scope="session")
def offline_bot() -> Bot:
    """
    Bot без сети — все outbound методы заменены AsyncMock-ами.

    Side effects:
        - bot.send_message, edit_message_text, answer_callback_query,
          send_photo, delete_message — все возвращают None (AsyncMock).
        - Сетевые вызовы внутри Bot полностью заблокированы OfflineRequest.

    Invariants:
        - Создаётся один раз на сессию (scope="session").
        - Не вызывает getMe() и не проверяет токен.
    """
    bot = Bot(
        token=FAKE_TOKEN,
        request=OfflineRequest(),
        get_updates_request=OfflineRequest(),
    )
    bot._unfreeze()  # разрешает monkeypatching атрибутов
    # Stub всех outbound методов
    bot.send_message = AsyncMock(return_value=None)
    bot.edit_message_text = AsyncMock(return_value=None)
    bot.answer_callback_query = AsyncMock(return_value=None)
    bot.send_photo = AsyncMock(return_value=None)
    bot.delete_message = AsyncMock(return_value=None)
    bot.send_document = AsyncMock(return_value=None)
    return bot


@pytest.fixture
def app(offline_bot) -> Application:
    """
    Application без updater — не поллит Telegram.

    Использование в тестах:
        async with app:
            await app.process_update(make_update("/start", offline_bot))

    Side effects:
        - Создаётся новый Application для каждого теста (scope="function").
        - Хендлеры регистрируются заново каждый раз → нет state leak между тестами.
    """
    application = (
        ApplicationBuilder()
        .token(FAKE_TOKEN)
        .updater(None)   # не вызывает getMe() при initialize()
        .bot(offline_bot)
        .build()
    )
    return application


# ── Update Factory Functions ──────────────────────────────────────────────────

DATE = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
_update_counter = 0


def _next_id() -> int:
    global _update_counter
    _update_counter += 1
    return _update_counter


def make_user(user_id: int = 1, first_name: str = "Test") -> User:
    """Создать тестового пользователя."""
    return User(id=user_id, first_name=first_name, is_bot=False)


def make_message(
    text: str,
    bot: Bot,
    user_id: int = 1,
    chat_id: Optional[int] = None,
) -> Message:
    """
    Создать Message с текстом.

    Side effects:
        - Вызывает msg.set_bot(bot) — без этого методы reply_text и т.д. упадут.

    Invariants:
        - Команды (/start, /help) автоматически получают BOT_COMMAND entities.
    """
    user = make_user(user_id)
    chat = Chat(id=chat_id or user_id, type="private")
    entities = None
    if text.startswith("/"):
        import re
        m = re.search(r"/[\da-z_]{1,32}", text)
        if m:
            entities = [MessageEntity(
                type=MessageEntity.BOT_COMMAND,
                offset=m.start(),
                length=len(m.group()),
            )]
    msg = Message(
        message_id=_next_id(),
        from_user=user,
        date=DATE,
        chat=chat,
        text=text,
        entities=entities,
    )
    msg.set_bot(bot)
    return msg


def make_update(text: str, bot: Bot, user_id: int = 1) -> Update:
    """Создать Update с текстовым сообщением."""
    msg = make_message(text, bot, user_id=user_id)
    return Update(update_id=_next_id(), message=msg)


def make_callback_update(data: str, bot: Bot, user_id: int = 1) -> Update:
    """
    Создать Update с нажатием inline-кнопки (CallbackQuery).

    Side effects:
        - Вызывает cbq.set_bot(bot).

    Используй для тестирования CallbackQueryHandler:
        update = make_callback_update("ow_user_123", offline_bot)
        async with app:
            await app.process_update(update)
    """
    user = make_user(user_id)
    msg = make_message("original message", bot, user_id=user_id)
    cbq = CallbackQuery(
        id=f"cbq_{_next_id()}",
        from_user=user,
        chat_instance=str(user_id),
        data=data,
        message=msg,
    )
    cbq.set_bot(bot)
    return Update(update_id=_next_id(), callback_query=cbq)


# ── Google Sheets Mock ────────────────────────────────────────────────────────

@pytest.fixture
def mock_sheets():
    """
    Мок SheetsManager для тестов хендлеров.

    Заменяет реальное подключение к Google Sheets.
    Все методы — MagicMock, настраивай return_value в каждом тесте.

    Использование:
        def test_something(mock_sheets):
            mock_sheets.get_user_role.return_value = "owner"
            mock_sheets.get_all_users.return_value = [...]
    """
    from unittest.mock import MagicMock
    sheets = MagicMock()
    sheets.get_user_role = MagicMock(return_value="owner")
    sheets.get_user = MagicMock(return_value=None)
    sheets.get_all_users = MagicMock(return_value=[])
    sheets.update_user_role = MagicMock(return_value=True)
    sheets.deactivate_user = MagicMock(return_value=True)
    return sheets
