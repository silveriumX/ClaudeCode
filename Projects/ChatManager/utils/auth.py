"""
Утилиты для проверки прав доступа
"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import config


def require_auth(func):
    """
    Декоратор: проверка что пользователь зарегистрирован и активен
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        sheets = context.bot_data.get('sheets')

        if not sheets:
            await update.message.reply_text(
                "[WARNING] System connection error. Try later."
            )
            return

        # Проверяем существование и активность пользователя
        if not sheets.is_user_active(user_id):
            await update.message.reply_text(
                "[ACCESS DENIED] You don't have access to this bot.\n\n"
                "Contact administrator to get access."
            )
            return

        return await func(update, context)

    return wrapper


def require_role(*allowed_roles):
    """
    Декоратор: проверка что у пользователя есть нужная роль

    Использование:
        @require_role(config.ROLE_ADMIN)
        @require_role(config.ROLE_MANAGER, config.ROLE_ADMIN)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            sheets = context.bot_data.get('sheets')

            if not sheets:
                await update.message.reply_text(
                    "[ERROR] System connection error."
                )
                return

            user_role = sheets.get_user_role(user_id)

            if user_role not in allowed_roles:
                await update.message.reply_text(
                    "[ACCESS DENIED] Insufficient permissions for this command."
                )
                return

            return await func(update, context)

        return wrapper
    return decorator


def get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получить информацию о текущем пользователе

    Returns:
        Dict с полями: telegram_id, username, name, role, status
        или None если пользователь не найден
    """
    user_id = update.effective_user.id
    sheets = context.bot_data.get('sheets')

    if not sheets:
        return None

    return sheets.get_user(user_id)


def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверить, является ли пользователь администратором"""
    user_id = update.effective_user.id
    sheets = context.bot_data.get('sheets')

    if not sheets:
        return False

    user_role = sheets.get_user_role(user_id)
    return user_role == config.ROLE_ADMIN


def is_manager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверить, является ли пользователь менеджером"""
    user_id = update.effective_user.id
    sheets = context.bot_data.get('sheets')

    if not sheets:
        return False

    user_role = sheets.get_user_role(user_id)
    return user_role == config.ROLE_MANAGER
