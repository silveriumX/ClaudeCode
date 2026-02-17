"""
Handler для создания запросов на чаты
ConversationHandler: название чата -> описание -> подтверждение
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from utils.auth import require_auth, require_role, get_user_info
import config
import logging

logger = logging.getLogger(__name__)

# Состояния разговора
TITLE, DESCRIPTION, CONFIRM = range(3)


@require_auth
@require_role(config.ROLE_ADMIN, config.ROLE_MANAGER)
async def new_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания запроса на чат"""
    await update.message.reply_text(
        "[NEW CHAT REQUEST]\n\n"
        "Enter chat title (max 255 characters):\n\n"
        "Send /cancel to abort."
    )
    return TITLE


async def chat_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия чата"""
    title = update.message.text.strip()

    if len(title) > config.MAX_CHAT_TITLE_LEN:
        await update.message.reply_text(
            f"[ERROR] Title too long (max {config.MAX_CHAT_TITLE_LEN} chars).\n"
            f"Try again:"
        )
        return TITLE

    if len(title) < 3:
        await update.message.reply_text(
            "[ERROR] Title too short (min 3 chars).\n"
            "Try again:"
        )
        return TITLE

    # Сохраняем название
    context.user_data['chat_title'] = title

    await update.message.reply_text(
        f"Chat title: {title}\n\n"
        f"Enter description (optional, max {config.MAX_CHAT_DESCRIPTION_LEN} chars):\n\n"
        f"Send '-' to skip or /cancel to abort."
    )
    return DESCRIPTION


async def chat_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания чата"""
    description = update.message.text.strip()

    # Если пользователь пропустил
    if description == '-':
        description = ''
    elif len(description) > config.MAX_CHAT_DESCRIPTION_LEN:
        await update.message.reply_text(
            f"[ERROR] Description too long (max {config.MAX_CHAT_DESCRIPTION_LEN} chars).\n"
            f"Try again or send '-' to skip:"
        )
        return DESCRIPTION

    # Сохраняем описание
    context.user_data['chat_description'] = description

    # Показываем подтверждение
    title = context.user_data['chat_title']

    keyboard = [
        [
            InlineKeyboardButton("[CONFIRM] Create", callback_data="confirm_create"),
            InlineKeyboardButton("[CANCEL]", callback_data="cancel_create")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    confirm_text = (
        "[CONFIRM CHAT REQUEST]\n\n"
        f"Title: {title}\n"
    )

    if description:
        confirm_text += f"Description: {description}\n"

    confirm_text += "\nCreate this chat?"

    await update.message.reply_text(
        confirm_text,
        reply_markup=reply_markup
    )
    return CONFIRM


async def confirm_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания чата"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_create":
        await query.edit_message_text(
            "[CANCELLED] Chat request cancelled."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Получаем данные
    title = context.user_data.get('chat_title', '')
    description = context.user_data.get('chat_description', '')
    user_id = update.effective_user.id

    # Создаем запрос в Google Sheets
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await query.edit_message_text(
            "[ERROR] System connection error. Try later."
        )
        return ConversationHandler.END

    request_id = sheets.create_chat_request(user_id, title, description)

    if not request_id:
        await query.edit_message_text(
            "[ERROR] Failed to create chat request. Try later."
        )
        return ConversationHandler.END

    logger.info(f"Created chat request {request_id} by user {user_id}")

    await query.edit_message_text(
        f"[SUCCESS] Chat request created!\n\n"
        f"Request ID: {request_id}\n"
        f"Title: {title}\n\n"
        f"UserBot is creating your chat...\n"
        f"You will receive invite link soon (usually takes 10-30 seconds).\n\n"
        f"Use /my_chats to check status."
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания чата"""
    await update.message.reply_text(
        "[CANCELLED] Chat request cancelled."
    )
    context.user_data.clear()
    return ConversationHandler.END


@require_auth
async def my_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список чатов пользователя"""
    user_id = update.effective_user.id
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await update.message.reply_text(
            "[ERROR] System connection error."
        )
        return

    chats = sheets.get_user_chats(user_id)

    if not chats:
        await update.message.reply_text(
            "[NO CHATS]\n\n"
            "You haven't created any chats yet.\n"
            "Use /new_chat to create one."
        )
        return

    # Формируем список
    response = f"[YOUR CHATS] Total: {len(chats)}\n\n"

    for chat in chats:
        status = chat['status']
        title = chat['title']
        date = chat['date']
        invite_link = chat.get('invite_link', '')

        response += f"--- {title} ---\n"
        response += f"Created: {date}\n"
        response += f"Status: {status}\n"

        if status == config.CHAT_STATUS_CREATED and invite_link:
            response += f"Link: {invite_link}\n"
        elif status == config.CHAT_STATUS_PENDING:
            response += f"[PENDING] Creating...\n"
        elif status == config.CHAT_STATUS_FAILED:
            response += f"[FAILED] Creation failed\n"

        response += "\n"

    await update.message.reply_text(response)


def get_chat_request_conversation_handler():
    """
    Создать ConversationHandler для запроса чата

    Returns:
        ConversationHandler
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler('new_chat', new_chat_start),
            MessageHandler(filters.Regex('^New Chat$'), new_chat_start)
        ],
        states={
            TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat_title)
            ],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat_description)
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_chat, pattern='^(confirm_create|cancel_create)$')
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_chat)
        ]
    )
