"""
Обработчики редактирования заявок
ОБНОВЛЕНО под новую структуру с update_request_fields
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from src.utils.categories import determine_category
from src.utils.formatters import format_amount
from src import config


# Состояния для редактирования
EDIT_AMOUNT, EDIT_CARD, EDIT_BANK, EDIT_PURPOSE = range(4)


async def edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования поля"""
    query = update.callback_query
    await query.answer()

    field = query.data.replace('edit_', '')

    # Сохраняем что редактируем
    context.user_data['editing_field'] = field

    prompts = {
        'amount': "💵 Введите новую сумму:\n\nНапример: 25000 или 25000,50",
        'card': "💳 Введите новый номер карты или телефон:\n\nНапример: 2202 2006 1234 5678",
        'bank': "🏦 Введите новый банк:\n\nНапример: Сбербанк",
        'purpose': "📝 Введите новое назначение платежа:"
    }

    prompt = prompts.get(field, "Введите новое значение:")

    # Определяем следующее состояние
    next_state = {
        'amount': EDIT_AMOUNT,
        'card': EDIT_CARD,
        'bank': EDIT_BANK,
        'purpose': EDIT_PURPOSE
    }.get(field)

    await query.edit_message_text(
        prompt + "\n\n"
        "Или отправьте /cancel для отмены."
    )

    return next_state


async def save_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить новую сумму"""
    try:
        new_amount = float(update.message.text.replace(',', '.').replace(' ', ''))
        if new_amount <= 0:
            raise ValueError

        return await save_field(update, context, new_amount=new_amount)

    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Введите число (например: 25000 или 25000,50):"
        )
        return EDIT_AMOUNT


async def save_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить новый номер карты/телефон"""
    new_card = update.message.text.strip()
    return await save_field(update, context, card_or_phone=new_card)


async def save_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить новый банк"""
    new_bank = update.message.text.strip()
    return await save_field(update, context, bank=new_bank)


async def save_purpose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить новое назначение"""
    new_purpose = update.message.text.strip()
    return await save_field(update, context, purpose=new_purpose)


async def save_field(update: Update, context: ContextTypes.DEFAULT_TYPE, **kwargs):
    """Общая функция сохранения поля через update_request_fields"""
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await update.message.reply_text("⚠️ Ошибка подключения к системе.")
        return ConversationHandler.END

    date = context.user_data.get('edit_date')
    amount = context.user_data.get('edit_amount')
    currency = context.user_data.get('edit_currency')  # Валюта обязательна!
    field = context.user_data.get('editing_field')

    if not date or not amount:
        await update.message.reply_text("❌ Ошибка: данные заявки не найдены.")
        return ConversationHandler.END

    # Вызываем НОВЫЙ API update_request_fields с валютой
    success = sheets.update_request_fields(
        date=date,
        amount=amount,
        currency=currency,
        **kwargs
    )

    if success:
        field_names = {
            'amount': 'Сумма',
            'card': 'Номер карты/телефон',
            'bank': 'Банк',
            'purpose': 'Назначение'
        }

        # Формируем сообщение о новом значении
        new_value = kwargs.get('new_amount') or kwargs.get('card_or_phone') or kwargs.get('bank') or kwargs.get('purpose')

        # Символы валют
        currency_symbols = {
            config.CURRENCY_RUB: '₽',
            config.CURRENCY_BYN: 'BYN',
            config.CURRENCY_KZT: '₸',
            config.CURRENCY_USDT: 'USDT',
            config.CURRENCY_CNY: '¥'
        }
        currency_symbol = currency_symbols.get(currency, '₽')

        # Формируем сообщение и кнопку возврата к заявке
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        request_id = context.user_data.get('edit_request_id', '')
        page = context.user_data.get('edit_page', 1)

        keyboard = [[
            InlineKeyboardButton(
                "« Вернуться к заявке",
                callback_data=f"view_req_{request_id}_{page}"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ *Поле обновлено!*\n\n"
            f"Поле: {field_names.get(field, field)}\n"
            f"Новое значение: {new_value}\n\n"
            f"_Реквизиты обновятся автоматически!_",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Ошибка при сохранении. Попробуйте позже.")
        return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена редактирования"""
    await update.message.reply_text("❌ Редактирование отменено.")
    context.user_data.clear()
    return ConversationHandler.END


async def edit_usdt_type_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать меню выбора типа USDT-перевода для редактирования.

    Side effects:
        - Редактирует текущее сообщение с двумя кнопками выбора.
        - Не меняет таблицу.

    Invariants:
        - context.user_data не изменяется.
    """
    query = update.callback_query
    await query.answer()

    request_id = context.user_data.get('edit_request_id', '')
    page = context.user_data.get('edit_page', 1)

    keyboard = [
        [InlineKeyboardButton("💸 Конечный получатель", callback_data="set_usdt_type_expense")],
        [InlineKeyboardButton("🔄 Пополнение площадки / Транзит", callback_data="set_usdt_type_internal")],
        [InlineKeyboardButton("« Назад", callback_data=f"edit_menu_{request_id}_{page}")]
    ]

    await query.edit_message_text(
        "🔄 *Тип перевода USDT*\n\n"
        "Выберите тип операции:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def set_usdt_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохранить выбранный тип USDT-перевода в Sheets.

    Side effects:
        - Вызывает sheets.update_request_fields(category=...) — обновляет col F (Категория) в листе USDT.
        - При успехе очищает context.user_data.

    Invariants:
        - Остальные колонки (сумма, кошелёк, назначение, статус) НЕ меняются.
        - При False (ошибка) — сообщение об ошибке, user_data не очищается.
    """
    query = update.callback_query
    await query.answer()

    is_internal = query.data == "set_usdt_type_internal"

    if is_internal:
        new_category = config.CATEGORY_INTERNAL_TRANSFER
    else:
        purpose = context.user_data.get('edit_purpose', '')
        new_category = determine_category(purpose)

    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    date = context.user_data.get('edit_date')
    amount = context.user_data.get('edit_amount')
    request_id = context.user_data.get('edit_request_id', '')
    page = context.user_data.get('edit_page', 1)

    if not date or not amount:
        await query.edit_message_text("❌ Ошибка: данные заявки не найдены.")
        return

    success = sheets.update_request_fields(
        date=date,
        amount=amount,
        currency=config.CURRENCY_USDT,
        category=new_category
    )

    type_label = "🔄 Пополнение / Транзит" if is_internal else "💸 Конечный получатель"

    keyboard = [[InlineKeyboardButton("« Вернуться к заявке", callback_data=f"view_req_{request_id}_{page}")]]

    if success:
        await query.edit_message_text(
            f"✅ *Тип перевода обновлён!*\n\n"
            f"Тип: {type_label}\n"
            f"Категория: {new_category}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data.clear()
    else:
        await query.edit_message_text(
            "❌ Ошибка при сохранении. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ConversationHandler для редактирования
def get_edit_conversation_handler():
    """Получить ConversationHandler для редактирования"""
    from telegram.ext import CallbackQueryHandler, CommandHandler

    return ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_field_callback, pattern='^edit_(amount|card|bank|purpose)$')],
        states={
            EDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_amount)],
            EDIT_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_card)],
            EDIT_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_bank)],
            EDIT_PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_purpose)]
        },
        fallbacks=[CommandHandler('cancel', edit_cancel)],
        name="edit_conversation",
        persistent=False
    )
