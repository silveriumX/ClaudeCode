"""
Finance Bot - Главный файл
Telegram бот для управления финансовыми заявками через Google Sheets
"""
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from src import config
from src.sheets import SheetsManager
from src.handlers.start import start, help_command
from src.handlers.menu import handle_menu_button, menu_command
from src.handlers.request import (
    get_request_conversation_handler,
    my_requests,
    view_request_callback,
    back_to_list_callback,
    edit_menu_callback,
    cancel_request_callback,
    my_requests_navigation_callback,
    edit_qr_cny_callback,
    handle_qr_update
)
from src.handlers.edit_handlers import (
    get_edit_conversation_handler
)
from src.handlers.payment import (
    pending_payments,
    my_payments,
    my_payments_navigation,
    get_payment_conversation_handler
)
from src.handlers.fact_expense import fact_expense_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Инициализация после запуска приложения"""
    logger.info("Инициализация Finance Bot...")

    try:
        # Подключаемся к Google Sheets
        sheets = SheetsManager()
        application.bot_data['sheets'] = sheets
        logger.info("✅ Подключение к Google Sheets успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")
        logger.error("Проверьте наличие файла service_account.json и настройки в .env")
        raise

    try:
        # Инициализируем DriveManager для загрузки QR-кодов/чеков
        from src.drive_manager import DriveManager
        drive_manager = DriveManager()
        application.bot_data['drive_manager'] = drive_manager
        logger.info("✅ DriveManager инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации DriveManager: {e}")
        logger.warning("Загрузка QR-кодов в Google Drive будет недоступна")

    # Меню команд (кнопка / в чате) — на мобильном кнопки меню могут быть скрыты клавиатурой
    try:
        await application.bot.set_my_commands([
            BotCommand("start", "Начать"),
            BotCommand("new_request", "Новая заявка"),
            BotCommand("my_requests", "Мои заявки"),
            BotCommand("pending_payments", "Заявки на оплату"),
            BotCommand("my_payments", "Мои выплаты"),
            BotCommand("help", "Помощь"),
            BotCommand("menu", "Показать меню"),
        ])
        logger.info("✅ Меню команд установлено")
    except Exception as e:
        logger.warning(f"Не удалось установить меню команд: {e}")


def main():
    """Запуск бота"""
    logger.info("Запуск Finance Bot...")

    # Проверяем наличие токена
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в .env файле!")
        return

    if not config.GOOGLE_SHEETS_ID:
        logger.error("❌ GOOGLE_SHEETS_ID не найден в .env файле!")
        logger.info("Откройте вашу Google Таблицу и скопируйте ID из URL:")
        logger.info("https://docs.google.com/spreadsheets/d/[ВАШ_ID]/edit")
        return

    # Создаем приложение
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ========== БАЗОВЫЕ КОМАНДЫ ==========
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))

    # ========== ОБРАБОТЧИК КНОПОК МЕНЮ ==========
    # Добавляем ПЕРЕД conversation handlers чтобы кнопки работали всегда
    # НЕ добавляем "📝 Новая заявка" - она обрабатывается ConversationHandler
    menu_buttons = [
        "📋 Мои заявки",
        "💳 Оплата заявок",
        "💰 Мои выплаты",
        "ℹ️ Помощь",
        "🔄 Обновить меню"
    ]
    for button_text in menu_buttons:
        application.add_handler(
            MessageHandler(filters.Regex(f"^{button_text}$"), handle_menu_button)
        )

    # ========== СОЗДАНИЕ ЗАЯВОК ==========
    # ConversationHandler теперь обрабатывает и кнопку меню "📝 Новая заявка"
    application.add_handler(get_request_conversation_handler())
    application.add_handler(CommandHandler("my_requests", my_requests))
    application.add_handler(CallbackQueryHandler(my_requests_navigation_callback, pattern='^my_req_page_'))
    application.add_handler(CallbackQueryHandler(view_request_callback, pattern='^view_req_'))
    application.add_handler(CallbackQueryHandler(back_to_list_callback, pattern='^back_to_list'))
    application.add_handler(CallbackQueryHandler(edit_menu_callback, pattern='^edit_menu_'))
    application.add_handler(CallbackQueryHandler(cancel_request_callback, pattern='^cancel_req_'))
    application.add_handler(CallbackQueryHandler(edit_qr_cny_callback, pattern='^edit_qr_cny$'))

    # ========== РЕДАКТИРОВАНИЕ ЗАЯВОК ==========
    application.add_handler(get_edit_conversation_handler())

    # ========== ОПЛАТА ЗАЯВОК (ИСПОЛНИТЕЛИ) ==========
    # ConversationHandler ПЕРЕД standalone PHOTO handler чтобы receipt upload работал
    application.add_handler(CommandHandler("pending_payments", pending_payments))
    application.add_handler(CommandHandler("my_payments", my_payments))
    application.add_handler(CallbackQueryHandler(my_payments_navigation, pattern='^mypay_page_'))
    application.add_handler(get_payment_conversation_handler())

    # ========== ОБНОВЛЕНИЕ QR (standalone, ПОСЛЕ ConversationHandlers) ==========
    application.add_handler(MessageHandler(filters.PHOTO, handle_qr_update))

    # ========== ФАКТИЧЕСКИЕ РАСХОДЫ (ROLE_REPORT) ==========
    application.add_handler(fact_expense_handler)

    # Запуск бота
    logger.info("✅ Finance Bot запущен и готов к работе!")
    logger.info("Нажмите Ctrl+C для остановки")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
