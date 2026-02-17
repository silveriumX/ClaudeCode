"""
ChatManager Bot - Control Bot
Telegram бот для управления запросами на создание чатов через Google Sheets
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)
import config
from sheets import ChatSheetsManager
from handlers.start import start, help_command
from handlers.menu import menu_command, handle_menu_button
from handlers.chat_request import (
    get_chat_request_conversation_handler,
    my_chats
)
from handlers.authorize import authorize_conv_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Инициализация после запуска приложения"""
    logger.info("Initializing ChatManager Bot...")

    try:
        # Инициализация Google Sheets
        sheets = ChatSheetsManager()
        application.bot_data['sheets'] = sheets
        logger.info("Google Sheets connection established")
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets: {e}")
        raise

    logger.info("ChatManager Bot is ready!")


def main():
    """Главная функция - запуск бота"""
    logger.info("Starting ChatManager Bot...")

    # Создаем приложение
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Регистрация handlers

    # Основные команды
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('menu', menu_command))
    application.add_handler(CommandHandler('my_chats', my_chats))

    # ConversationHandler для создания чата
    application.add_handler(get_chat_request_conversation_handler())

    # ConversationHandler для авторизации UserBot (только для админов)
    application.add_handler(authorize_conv_handler)

    # Обработка кнопок меню
    application.add_handler(
        MessageHandler(
            filters.Regex('^(New Chat|My Chats|Help)$'),
            handle_menu_button
        )
    )

    logger.info("Handlers registered")

    # Запуск бота
    logger.info("Starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
