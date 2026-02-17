"""
Утилиты для проверки прав доступа
"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from src import config


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
                "⚠️ Ошибка подключения к системе. Попробуйте позже."
            )
            return

        # Проверяем существование и активность пользователя
        if not sheets.is_user_active(user_id):
            await update.message.reply_text(
                "🚫 У вас нет доступа к боту.\n\n"
                "Обратитесь к администратору для получения доступа."
            )
            return

        return await func(update, context)

    return wrapper


def require_role(*allowed_roles):
    """
    Декоратор: проверка что у пользователя есть нужная роль

    Использование:
        @require_role(config.ROLE_OWNER)
        @require_role(config.ROLE_MANAGER, config.ROLE_OWNER)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            sheets = context.bot_data.get('sheets')

            if not sheets:
                await update.message.reply_text(
                    "⚠️ Ошибка подключения к системе."
                )
                return

            user_role = sheets.get_user_role(user_id)

            if user_role not in allowed_roles:
                await update.message.reply_text(
                    "🚫 Недостаточно прав для выполнения этой команды."
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


def is_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверить, является ли пользователь владельцем"""
    user_id = update.effective_user.id
    sheets = context.bot_data.get('sheets')

    if not sheets:
        return False

    user_role = sheets.get_user_role(user_id)
    return user_role == config.ROLE_OWNER


def is_manager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверить, является ли пользователь менеджером"""
    user_id = update.effective_user.id
    sheets = context.bot_data.get('sheets')

    if not sheets:
        return False

    user_role = sheets.get_user_role(user_id)
    return user_role == config.ROLE_MANAGER


def is_executor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверить, является ли пользователь исполнителем"""
    user_id = update.effective_user.id
    sheets = context.bot_data.get('sheets')

    if not sheets:
        return False

    user_role = sheets.get_user_role(user_id)
    return user_role == config.ROLE_EXECUTOR
