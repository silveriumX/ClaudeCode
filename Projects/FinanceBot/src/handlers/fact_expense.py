"""
Обработчики для внесения фактических расходов (без заявок)
Роль: report
Только наличные RUB
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from src import config
from src.utils.auth import require_auth, require_role

logger = logging.getLogger(__name__)

# Состояния ConversationHandler
(
    FACT_AMOUNT,
    FACT_RECIPIENT,
    FACT_PURPOSE,
    FACT_CONFIRM
) = range(4)


@require_auth
@require_role(config.ROLE_REPORT, config.ROLE_OWNER)
async def new_fact_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало внесения фактического расхода"""

    # Сразу RUB наличные
    context.user_data['fact_currency'] = 'RUB'

    await update.message.reply_text(
        "📊 *Внесение расхода (наличные)*\n\n"
        "Введите сумму в рублях:\n\n"
        "Или отправьте /cancel для отмены.",
        parse_mode='Markdown'
    )

    return FACT_AMOUNT


async def fact_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода суммы"""
    text = update.message.text.strip()

    # Парсим сумму
    try:
        amount_str = text.replace(' ', '').replace(',', '.')
        amount = float(amount_str)

        if amount <= 0:
            await update.message.reply_text(
                "❌ Сумма должна быть больше нуля.\n"
                "Введите корректную сумму:"
            )
            return FACT_AMOUNT

    except ValueError:
        await update.message.reply_text(
            "❌ Некорректная сумма.\n"
            "Введите число (например: 1500 или 1500.50):"
        )
        return FACT_AMOUNT

    context.user_data['fact_amount'] = amount

    await update.message.reply_text(
        "👤 *Кому выплачено?*\n\n"
        "Введите получателя (ФИО или название):\n\n"
        "Или отправьте /cancel для отмены.",
        parse_mode='Markdown'
    )

    return FACT_RECIPIENT


async def fact_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода получателя"""
    recipient = update.message.text.strip()

    if len(recipient) < 2:
        await update.message.reply_text(
            "❌ Имя получателя слишком короткое.\n"
            "Введите ФИО или название:"
        )
        return FACT_RECIPIENT

    if len(recipient) > config.MAX_RECIPIENT_LEN:
        await update.message.reply_text(
            f"❌ Слишком длинное (максимум {config.MAX_RECIPIENT_LEN} символов).\n"
            "Сократите:"
        )
        return FACT_RECIPIENT

    context.user_data['fact_recipient'] = recipient

    await update.message.reply_text(
        "📝 *За что выплачено?*\n\n"
        "Введите назначение платежа:\n\n"
        "Или отправьте /cancel для отмены.",
        parse_mode='Markdown'
    )

    return FACT_PURPOSE


async def fact_purpose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода назначения"""
    purpose = update.message.text.strip()

    if len(purpose) < 3:
        await update.message.reply_text(
            "❌ Описание слишком короткое.\n"
            "Введите более подробное описание:"
        )
        return FACT_PURPOSE

    if len(purpose) > config.MAX_PURPOSE_LEN:
        await update.message.reply_text(
            f"❌ Описание слишком длинное (максимум {config.MAX_PURPOSE_LEN} символов).\n"
            "Сократите описание:"
        )
        return FACT_PURPOSE

    context.user_data['fact_purpose'] = purpose

    # Показываем подтверждение
    amount = context.user_data.get('fact_amount', 0)
    recipient = context.user_data.get('fact_recipient', '')

    keyboard = [
        [
            InlineKeyboardButton("Сохранить", callback_data="fact_save"),
            InlineKeyboardButton("Отмена", callback_data="fact_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📊 *Проверьте данные:*\n\n"
        f"💰 Сумма: {amount:,.2f} ₽\n"
        f"👤 Получатель: {recipient}\n"
        f"📝 Назначение: {purpose}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
        f"💵 Тип: Наличные\n\n"
        f"Всё верно?",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

    return FACT_CONFIRM


async def fact_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение и сохранение"""
    query = update.callback_query
    await query.answer()

    if query.data == "fact_cancel":
        await query.edit_message_text("❌ Отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "fact_save":
        sheets = context.bot_data.get('sheets')

        if not sheets:
            await query.edit_message_text("⚠️ Ошибка подключения к системе.")
            return ConversationHandler.END

        user = update.effective_user
        amount = context.user_data.get('fact_amount', 0)
        recipient = context.user_data.get('fact_recipient', '')
        purpose = context.user_data.get('fact_purpose', '')

        # Сохраняем в таблицу
        try:
            expense_id = sheets.create_fact_expense(
                amount=amount,
                recipient=recipient,
                purpose=purpose,
                author_id=str(user.id),
                author_username=user.username or '',
                author_fullname=user.full_name or ''
            )

            if expense_id:
                await query.edit_message_text(
                    f"✅ *Расход сохранен!*\n\n"
                    f"🆔 ID: `{expense_id}`\n"
                    f"💰 Сумма: {amount:,.2f} ₽\n"
                    f"👤 Получатель: {recipient}\n"
                    f"📝 Назначение: {purpose}\n"
                    f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ Ошибка при сохранении. Попробуйте позже."
                )

        except Exception as e:
            logger.error(f"Ошибка сохранения фактического расхода: {e}")
            await query.edit_message_text(
                "❌ Ошибка при сохранении. Попробуйте позже."
            )

        context.user_data.clear()
        return ConversationHandler.END

    return FACT_CONFIRM


async def fact_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена через команду /cancel"""
    context.user_data.clear()
    await update.message.reply_text("❌ Внесение расхода отменено.")
    return ConversationHandler.END


# ConversationHandler для внесения фактических расходов
fact_expense_handler = ConversationHandler(
    entry_points=[
        CommandHandler('fact', new_fact_expense_start),
        MessageHandler(filters.Regex(r'^📊 Внести расход$'), new_fact_expense_start)
    ],
    states={
        FACT_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, fact_amount)
        ],
        FACT_RECIPIENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, fact_recipient)
        ],
        FACT_PURPOSE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, fact_purpose)
        ],
        FACT_CONFIRM: [
            CallbackQueryHandler(fact_confirm_callback, pattern=r'^fact_')
        ]
    },
    fallbacks=[
        CommandHandler('cancel', fact_cancel)
    ],
    name="fact_expense_conversation",
    persistent=False,
    allow_reentry=True
)
