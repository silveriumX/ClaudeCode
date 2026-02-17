#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UserBot Authorization Handler - авторизация через Telegram бота
Позволяет админу авторизовать UserBot прямо из Telegram
"""
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)
from utils.auth import require_role
from config import ROLE_ADMIN
from pyrogram import Client
from config import USERBOT_API_ID, USERBOT_API_HASH, USERBOT_SESSION

logger = logging.getLogger(__name__)

# Состояния диалога
PHONE, CODE = range(2)

@require_role(ROLE_ADMIN)
async def authorize_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса авторизации UserBot"""
    user = update.effective_user

    logger.info(f"User {user.id} started UserBot authorization")

    # Проверяем, уже авторизован ли UserBot
    try:
        app = Client(
            name=USERBOT_SESSION,
            api_id=USERBOT_API_ID,
            api_hash=USERBOT_API_HASH,
            workdir="."
        )

        # Пытаемся подключиться с существующей сессией
        await app.start()
        me = await app.get_me()
        await app.stop()

        await update.message.reply_text(
            f"✅ UserBot уже авторизован!\n\n"
            f"Аккаунт: {me.first_name}\n"
            f"Username: @{me.username}\n"
            f"ID: {me.id}\n\n"
            f"Если хочешь переавторизовать, отправь /reauthorize"
        )
        return ConversationHandler.END

    except Exception:
        # UserBot не авторизован, начинаем процесс
        pass

    await update.message.reply_text(
        "🔐 **Авторизация UserBot**\n\n"
        "UserBot нужен для создания групповых чатов от имени аккаунта-администратора.\n\n"
        "**Что произойдёт:**\n"
        "1. Ты отправишь номер телефона аккаунта-администратора\n"
        "2. Telegram отправит код в 'Избранное' этого аккаунта\n"
        "3. Ты введёшь код здесь\n"
        "4. Авторизация завершится автоматически\n\n"
        "**Безопасность:** Авторизация происходит напрямую через Telegram API, "
        "данные не сохраняются нигде кроме session файла.\n\n"
        "Отправь номер телефона с кодом страны (например: +79001234567):\n"
        "Или /cancel для отмены.",
        parse_mode='Markdown'
    )

    return PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение номера телефона"""
    user = update.effective_user

    # Получаем номер из текста
    phone = update.message.text.strip()

    if not phone.startswith('+'):
        await update.message.reply_text(
            "❌ Номер должен начинаться с '+' и кода страны.\n"
            "Например: +79001234567\n\n"
            "Попробуй ещё раз или /cancel для отмены."
        )
        return PHONE

    logger.info(f"User {user.id} provided phone: {phone[:4]}***")

    # Сохраняем номер в context
    context.user_data['phone'] = phone

    await update.message.reply_text(
        "⏳ Отправляю код... Подожди немного.",
        parse_mode='Markdown'
    )

    try:
        logger.info(f"Creating Pyrogram client for phone {phone[:4]}***")

        # Создаём Pyrogram клиента и отправляем код
        app = Client(
            name=USERBOT_SESSION,
            api_id=int(USERBOT_API_ID),
            api_hash=USERBOT_API_HASH,
            workdir="."
        )

        logger.info("Connecting to Telegram...")
        await app.connect()
        logger.info("Connected successfully")

        # Отправляем код
        logger.info(f"Sending code to {phone[:4]}***")
        sent_code = await app.send_code(phone)
        logger.info(f"Code sent, hash: {sent_code.phone_code_hash[:20]}***")

        context.user_data['phone_code_hash'] = sent_code.phone_code_hash
        context.user_data['app'] = app  # Сохраняем клиента

        await update.message.reply_text(
            f"✅ Код отправлен на номер {phone}\n\n"
            f"📱 Проверь **'Избранное'** в Telegram на этом аккаунте.\n\n"
            f"Отправь код сюда (только цифры) или /cancel для отмены:",
            parse_mode='Markdown'
        )

        return CODE

    except Exception as e:
        logger.error(f"Error in receive_phone: {type(e).__name__}: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Ошибка отправки кода: {type(e).__name__}\n"
            f"Детали: {str(e)[:200]}\n\n"
            f"Проверь правильность номера и попробуй ещё раз.\n"
            f"Отправь /authorize для повтора."
        )
        return ConversationHandler.END

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение кода подтверждения"""
    user = update.effective_user
    code = update.message.text.strip().replace('-', '').replace(' ', '')

    if not code.isdigit():
        await update.message.reply_text(
            "❌ Код должен содержать только цифры.\n"
            "Попробуй ещё раз:"
        )
        return CODE

    logger.info(f"User {user.id} provided verification code")

    try:
        app = context.user_data.get('app')
        phone = context.user_data.get('phone')
        phone_code_hash = context.user_data.get('phone_code_hash')

        if not all([app, phone, phone_code_hash]):
            await update.message.reply_text(
                "❌ Сессия истекла. Начни сначала: /authorize"
            )
            return ConversationHandler.END

        # Завершаем авторизацию
        await app.sign_in(phone, phone_code_hash, code)

        # Получаем информацию об аккаунте
        me = await app.get_me()

        await app.stop()

        # Очищаем временные данные
        context.user_data.clear()

        logger.info(f"UserBot authorized successfully: {me.id} (@{me.username})")

        await update.message.reply_text(
            "✅ **Авторизация успешна!**\n\n"
            f"Аккаунт: {me.first_name} {me.last_name or ''}\n"
            f"Username: @{me.username}\n"
            f"ID: {me.id}\n\n"
            "UserBot теперь готов к созданию чатов!\n"
            "Используй /new_chat для создания нового чата.",
            parse_mode='Markdown'
        )

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Authorization error: {e}")

        error_msg = str(e)

        # Обработка специфичных ошибок
        if "PHONE_CODE_INVALID" in error_msg:
            await update.message.reply_text(
                "❌ Неверный код. Попробуй ещё раз:"
            )
            return CODE
        elif "PHONE_CODE_EXPIRED" in error_msg:
            await update.message.reply_text(
                "❌ Код истёк. Начни авторизацию заново: /authorize"
            )
            return ConversationHandler.END
        elif "SESSION_PASSWORD_NEEDED" in error_msg:
            # Требуется 2FA пароль
            await update.message.reply_text(
                "🔐 На аккаунте включена двухфакторная аутентификация.\n"
                "Отправь пароль от аккаунта:"
            )
            context.user_data['needs_2fa'] = True
            return CODE
        else:
            await update.message.reply_text(
                f"❌ Ошибка авторизации: {e}\n\n"
                "Попробуй ещё раз: /authorize"
            )
            return ConversationHandler.END

async def cancel_authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена авторизации"""
    # Закрываем Pyrogram клиент если был открыт
    app = context.user_data.get('app')
    if app:
        try:
            await app.stop()
        except:
            pass

    context.user_data.clear()

    await update.message.reply_text("Авторизация отменена.")

    return ConversationHandler.END

# ConversationHandler
authorize_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('authorize', authorize_start)],
    states={
        PHONE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)
        ],
        CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)
        ]
    },
    fallbacks=[CommandHandler('cancel', cancel_authorize)],
    name="authorize_userbot",
    persistent=False
)
