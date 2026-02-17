"""
Start и help команды для ChatManager Bot
"""
from telegram import Update
from telegram.ext import ContextTypes
from utils.auth import get_user_info
import config
import logging

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_info = get_user_info(update, context)

    if not user_info:
        await update.message.reply_text(
            f"Hello, {user.first_name}!\n\n"
            f"[ACCESS DENIED] You are not registered in the system.\n"
            f"Your Telegram ID: {user.id}\n\n"
            f"Contact administrator to get access."
        )
        return

    role = user_info.get('role', config.ROLE_MEMBER)

    welcome_text = (
        f"Hello, {user.first_name}!\n\n"
        f"ChatManager Bot - AI-first chat management system.\n\n"
        f"Your role: {role}\n\n"
        f"Available commands:\n"
        f"/new_chat - Create new chat\n"
        f"/my_chats - View your chats\n"
        f"/help - Show this help\n"
    )

    if role == config.ROLE_ADMIN:
        welcome_text += f"\n[ADMIN] You can create unlimited chats."

    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user_info = get_user_info(update, context)

    if not user_info:
        await update.message.reply_text(
            "[ACCESS DENIED] You need to be registered to use this bot.\n"
            "Contact administrator."
        )
        return

    role = user_info.get('role', config.ROLE_MEMBER)

    help_text = (
        "ChatManager Bot - Commands:\n\n"
        "/start - Start bot and show info\n"
        "/new_chat - Create new chat request\n"
        "/my_chats - View all your chats\n"
        "/help - Show this help\n\n"
    )

    if role == config.ROLE_ADMIN:
        help_text += (
            "[ADMIN COMMANDS]\n"
            "/authorize - Authorize UserBot (one-time setup)\n"
            "You have full access to create and manage chats.\n"
        )
    elif role == config.ROLE_MANAGER:
        help_text += (
            "[MANAGER ACCESS]\n"
            "You can create chats for your team.\n"
        )
    else:
        help_text += (
            "[MEMBER ACCESS]\n"
            "You can view chats where you are participant.\n"
        )

    await update.message.reply_text(help_text)
