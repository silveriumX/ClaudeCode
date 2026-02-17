"""
Главное меню ChatManager Bot
"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.auth import require_auth, get_user_info
import config
import logging

logger = logging.getLogger(__name__)


@require_auth
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню"""
    user_info = get_user_info(update, context)
    role = user_info.get('role', config.ROLE_MEMBER)

    # Формируем клавиатуру в зависимости от роли
    keyboard = []

    if role in [config.ROLE_ADMIN, config.ROLE_MANAGER]:
        keyboard.append([KeyboardButton("New Chat")])

    keyboard.append([KeyboardButton("My Chats")])
    keyboard.append([KeyboardButton("Help")])

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(
        f"Main Menu\n\nYour role: {role}",
        reply_markup=reply_markup
    )


@require_auth
async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок меню"""
    text = update.message.text

    if text == "New Chat":
        # Перенаправляем на создание чата
        from handlers.chat_request import new_chat_start
        await new_chat_start(update, context)

    elif text == "My Chats":
        # Показываем список чатов
        from handlers.chat_request import my_chats
        await my_chats(update, context)

    elif text == "Help":
        from handlers.start import help_command
        await help_command(update, context)

    else:
        await update.message.reply_text(
            "[ERROR] Unknown command. Use /help to see available commands."
        )
