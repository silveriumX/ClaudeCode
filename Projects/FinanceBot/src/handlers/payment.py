"""
Handler для оплаты заявок (исполнители)

Логика:
1. Owner вручную ставит имя исполнителя в колонку "Исполнитель" в Google Sheets
2. Исполнитель видит ТОЛЬКО назначенные ему заявки (точное совпадение имени)
3. Исполнитель вводит: ID сделки, аккаунт, сумму USDT
4. Исполнитель отмечает оплаченной и прикрепляет чек
5. Owner получает уведомление
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from src.utils.auth import require_auth, require_role
from src.utils.formatters import format_amount, get_currency_symbols_dict
from src.utils.tronscan import parse_tronscan_url, extract_hash_from_url
from src import config

logger = logging.getLogger(__name__)

# Состояния разговора
SHOW_DETAILS, ENTER_DEAL_ID, ENTER_ACCOUNT, ENTER_USDT, CONFIRM_PAYMENT, UPLOAD_RECEIPT = range(6)

# Пагинация
ITEMS_PER_PAGE = 5


def _parse_creation_datetime(request_id: str) -> str:
    """
    Извлечь дату и время создания из ID заявки.

    Формат ID: REQ-YYYYMMDD-HHMMSS-UUID
    Пример: REQ-20260214-122043-7397031E -> 14.02.2026 12:20

    Returns:
        Строка "ДД.ММ.ГГГГ ЧЧ:ММ" или пустая строка
    """
    if not request_id or not request_id.startswith('REQ-'):
        return ''
    try:
        parts = request_id.split('-')
        # parts: ['REQ', 'YYYYMMDD', 'HHMMSS', 'UUID...']
        if len(parts) < 3:
            return ''
        date_part = parts[1]  # YYYYMMDD
        time_part = parts[2]  # HHMMSS

        year = date_part[:4]
        month = date_part[4:6]
        day = date_part[6:8]
        hour = time_part[:2]
        minute = time_part[2:4]

        return f"{day}.{month}.{year} {hour}:{minute}"
    except (IndexError, ValueError):
        return ''


def _short_request_id(request_id: str) -> str:
    """
    Короткий ID для отображения.
    REQ-20260214-122043-7397031E -> REQ-..7397031E
    """
    if not request_id:
        return ''
    if len(request_id) > 20:
        return request_id[:4] + '..' + request_id[-8:]
    return request_id


# ===== PENDING PAYMENTS (assigned to executor) =====

@require_auth
@require_role(config.ROLE_EXECUTOR, config.ROLE_OWNER)
async def pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать заявки на оплату.

    - Для executor: ТОЛЬКО заявки со статусом "Создана", назначенные ему
      (точное совпадение имени в столбце "Исполнитель").
      БЕЗ назначения платежа. НЕ показывает оплаченные/отменённые.
    - Для owner: ВСЕ заявки со статусом "Создана"
    """
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await update.message.reply_text("Ошибка подключения к системе.")
        return

    user = update.effective_user
    user_info = sheets.get_user(user.id)
    if not user_info or not user_info.get('name'):
        await update.message.reply_text(
            "Не удалось определить ваше имя.\n"
            "Убедитесь, что в листе Пользователи заполнено поле Имя."
        )
        return

    user_role = user_info.get('role', '')
    executor_name = user_info['name'].strip()
    is_executor = (user_role == config.ROLE_EXECUTOR)

    if user_role == config.ROLE_OWNER:
        # Owner видит ВСЕ заявки со статусом "Создана"
        requests = sheets.get_requests_by_status(config.STATUS_CREATED)
    else:
        # Executor: ТОЛЬКО "Создана" + точное совпадение имени исполнителя.
        # get_assigned_requests уже фильтрует по STATUS_CREATED и executor_name.
        requests = sheets.get_assigned_requests(executor_name)

    if not requests:
        if user_role == config.ROLE_OWNER:
            await update.message.reply_text("Нет заявок со статусом 'Создана'.")
        else:
            await update.message.reply_text(
                "Нет назначенных заявок на оплату.\n\n"
                "Заявки появятся здесь когда владелец назначит вас исполнителем."
            )
        return

    currency_symbols = get_currency_symbols_dict()

    message = f"*Заявки на оплату ({len(requests)}):*\n\n"
    keyboard = []

    for req in requests:
        req_currency = req.get('currency', config.CURRENCY_RUB)
        currency_symbol = currency_symbols.get(req_currency, '')
        req_id = req.get('request_id', '')

        # ID и дата/время создания
        created_dt = _parse_creation_datetime(req_id)
        short_id = _short_request_id(req_id)

        # Номер заявки + дата создания
        header = f"`{short_id}`"
        if created_dt:
            header += f" | {created_dt}"
        message += header + "\n"

        # Сумма + валюта
        amount_str = format_amount(req['amount'], req_currency)
        message += f"{amount_str} {currency_symbol}"

        # Банк
        bank = req.get('bank', '')
        if bank:
            message += f" | {bank}"

        # Получатель
        recipient = req.get('recipient', '')
        if req_currency == config.CURRENCY_USDT:
            wallet = req.get('card_or_phone', '')
            if wallet:
                message += f" | {wallet[:25]}"
        elif req_currency == config.CURRENCY_CNY:
            pass  # банк уже добавлен выше (Alipay/WeChat)
        else:
            if recipient:
                message += f" | {recipient}"

        message += "\n"

        # Назначение -- только для owner
        if not is_executor:
            purpose = req.get('purpose', '')
            if purpose:
                message += f"Назначение: {purpose}\n"

        message += "\n"

        # Callback: payreq_{request_id}
        callback_data = f"payreq_{req_id}"
        if len(callback_data) > 64:
            callback_data = f"pay_{req['date']}_{req['amount']}_{req_currency}"

        # Кнопка: сумма + валюта + банк + получатель (без "Оплатить")
        # Telegram ограничивает текст кнопки ~64 символами
        btn_text = f"{amount_str} {currency_symbol}"
        if bank:
            btn_text += f" {bank}"
        if recipient:
            # Сокращаем получателя если текст слишком длинный
            remaining = 60 - len(btn_text)
            if remaining > 5:
                short_recipient = recipient[:remaining].strip()
                btn_text += f" {short_recipient}"

        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=callback_data)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ===== PAYMENT FLOW =====

async def start_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать детали заявки с КОПИРУЕМЫМИ полями.

    Каждое важное поле (сумма, карта, банк, получатель) выводится
    в <code>...</code>, чтобы при нажатии в Telegram оно копировалось.

    Внизу -- кнопка "Оплачена" для перехода к вводу данных.
    """
    query = update.callback_query
    await query.answer()

    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("Ошибка подключения к системе.")
        return ConversationHandler.END

    # Определяем заявку по callback data
    data = query.data
    request = None

    if data.startswith('payreq_'):
        request_id = data.replace('payreq_', '')
        request = sheets.get_request_by_request_id(request_id)
    elif data.startswith('ow_pay_req_'):
        request_id = data.replace('ow_pay_req_', '')
        # Авто-назначить владельца исполнителем
        user_info_now = sheets.get_user(update.effective_user.id)
        owner_name = user_info_now.get('name', '').strip() if user_info_now else ''
        if owner_name and request_id:
            sheets.assign_executor(request_id, owner_name)
        request = sheets.get_request_by_request_id(request_id)
    elif data.startswith('pay_'):
        parts = data.replace('pay_', '').rsplit('_', 2)
        if len(parts) >= 2:
            date = parts[0]
            try:
                amount = float(parts[1])
            except ValueError:
                await query.edit_message_text("Ошибка формата данных.")
                return ConversationHandler.END
            currency = parts[2] if len(parts) == 3 else config.CURRENCY_RUB
            request = sheets.get_request_by_id(date, amount, currency)

    if not request:
        await query.edit_message_text("Заявка не найдена.")
        return ConversationHandler.END

    # Сохраняем данные заявки в context
    context.user_data['payment_request'] = request
    context.user_data['payment_request_id'] = request.get('request_id', '')
    context.user_data['payment_date'] = request.get('date', '')
    context.user_data['payment_amount'] = request.get('amount', 0)
    context.user_data['payment_currency'] = request.get('currency', config.CURRENCY_RUB)

    currency = request.get('currency', config.CURRENCY_RUB)

    # Определяем роль
    user_info = sheets.get_user(update.effective_user.id)
    is_executor = (user_info.get('role', '') == config.ROLE_EXECUTOR) if user_info else False

    # Формируем детали с КОПИРУЕМЫМИ полями (HTML parse_mode)
    # <code>...</code> -- одиночное поле (копируется при нажатии)
    # <pre>...</pre> -- блок (весь текст копируется разом)
    req_id = request.get('request_id', '')
    created_dt = _parse_creation_datetime(req_id)

    details = "<b>Детали заявки</b>\n\n"

    # ID и дата/время создания
    if req_id:
        details += f"ID: <code>{req_id}</code>\n"
    if created_dt:
        details += f"Создана: {created_dt}\n"
    details += "\n"

    # Собираем все реквизиты в один блок для копирования целиком
    raw_amount = request.get('amount', 0)
    if isinstance(raw_amount, float) and raw_amount == int(raw_amount):
        amount_str = str(int(raw_amount))
    else:
        amount_str = str(raw_amount)

    # Формируем копируемый блок (все реквизиты разом)
    copy_lines = []
    copy_lines.append(amount_str)

    if currency == config.CURRENCY_USDT:
        wallet = request.get('card_or_phone', '')
        if wallet:
            copy_lines.append(wallet)
    elif currency == config.CURRENCY_CNY:
        bank = request.get('bank', '')
        card = request.get('card_or_phone', '')
        if bank:
            copy_lines.append(bank)
        if card:
            copy_lines.append(card)
    else:
        # RUB/BYN/KZT
        card_or_phone = request.get('card_or_phone', '')
        bank = request.get('bank', '')
        recipient = request.get('recipient', '')
        if card_or_phone:
            copy_lines.append(card_or_phone)
        if bank:
            copy_lines.append(bank)
        if recipient:
            copy_lines.append(recipient)

    # Один <pre> блок -- нажал = скопировал ВСЕ
    copy_block = "\n".join(copy_lines)
    details += f"<pre>{copy_block}</pre>\n"

    # QR-код для CNY (ссылка, не копируемый блок)
    if currency == config.CURRENCY_CNY and request.get('qr_code_link'):
        details += f"QR: {request['qr_code_link']}\n"

    details += "\n<i>Нажмите на блок чтобы скопировать все</i>\n"

    # Назначение -- только для owner
    if not is_executor:
        purpose = request.get('purpose', '')
        if purpose:
            details += f"\nНазначение: {purpose}\n"

    keyboard = [
        [InlineKeyboardButton("Оплачена", callback_data="mark_paid")],
        [InlineKeyboardButton("Назад", callback_data="cancel_pay")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(details, parse_mode='HTML', reply_markup=reply_markup)
    return SHOW_DETAILS


async def mark_paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка 'Оплачена' нажата -- переходим к вводу ID сделки"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_pay":
        await query.edit_message_text("Отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    # mark_paid -> запрашиваем ID сделки
    currency = context.user_data.get('payment_currency', '')
    if currency == config.CURRENCY_USDT:
        await query.edit_message_text(
            "Вставьте ссылку на транзакцию — бот всё заполнит автоматически:\n\n"
            "<code>https://tronscan.org/#/transaction/abc123...</code>\n\n"
            "Или введите любой текст вручную (TX ID, номер сделки и т.п.) — "
            "тогда аккаунт и детали введёте сами.",
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            "Введите ID сделки:\n\n"
            "Например: #UD823470 или отправьте - (пропустить)"
        )
    return ENTER_DEAL_ID


async def enter_deal_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод ID сделки / Tronscan-ссылки для USDT"""
    text = update.message.text.strip()
    currency = context.user_data.get('payment_currency', '')

    # --- USDT: пробуем распознать как Tronscan-ссылку/хеш ---
    if currency == config.CURRENCY_USDT:

        # Если пользователь уже выбрал ручной ввод — не трогаем Tronscan
        if context.user_data.pop('usdt_manual', False):
            context.user_data['deal_id'] = text if text != '-' else ''
            await update.message.reply_text(
                "Введите название аккаунта (откуда платили):\n\n"
                "Например: Business Account или отправьте - (пропустить):"
            )
            return ENTER_ACCOUNT

        tx_hash_check = extract_hash_from_url(text)

        if tx_hash_check:
            # Это ссылка или хеш — запускаем автоматическую верификацию
            request = context.user_data.get('payment_request', {})
            expected_wallet = request.get('card_or_phone', '').strip()
            expected_amount = float(request.get('amount', 0))

            await update.message.reply_text("Проверяю транзакцию...")
            tx = parse_tronscan_url(text)

            manual_btn = [[InlineKeyboardButton("Ввести вручную", callback_data="usdt_enter_manual")]]

            if tx is None:
                await update.message.reply_text(
                    "Не удалось получить данные транзакции.\n"
                    "Проверьте ссылку или попробуйте позже.\n\n"
                    "Вставьте другую ссылку или нажмите кнопку:",
                    reply_markup=InlineKeyboardMarkup(manual_btn)
                )
                return ENTER_DEAL_ID

            # Сверяем кошелёк получателя и сумму
            wallet_ok = tx.recipient.lower() == expected_wallet.lower()
            amount_ok = abs(tx.amount - expected_amount) <= 0.01

            if not wallet_ok or not amount_ok:
                errors = []
                if not wallet_ok:
                    errors.append(
                        f"Кошелёк получателя не совпадает:\n"
                        f"  В заявке: <code>{expected_wallet}</code>\n"
                        f"  В транзакции: <code>{tx.recipient}</code>"
                    )
                if not amount_ok:
                    errors.append(
                        f"Сумма не совпадает:\n"
                        f"  В заявке: {expected_amount} USDT\n"
                        f"  В транзакции: {tx.amount} {tx.token}"
                    )
                await update.message.reply_text(
                    "Транзакция не прошла проверку:\n\n" + "\n\n".join(errors) + "\n\n"
                    "Вставьте другую ссылку или нажмите кнопку:",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(manual_btn)
                )
                return ENTER_DEAL_ID

            # Всё совпало — заполняем все поля автоматически и идём в подтверждение
            context.user_data['deal_id'] = tx.tx_hash
            context.user_data['account_name'] = tx.sender
            context.user_data['amount_usdt'] = tx.amount

            await update.message.reply_text(
                f"Транзакция верифицирована:\n\n"
                f"Hash: <code>{tx.tx_hash[:16]}...{tx.tx_hash[-8:]}</code>\n"
                f"Отправитель: <code>{tx.sender}</code>\n"
                f"Получатель: <code>{tx.recipient}</code>\n"
                f"Сумма: {tx.amount} {tx.token}",
                parse_mode='HTML'
            )
            return await show_payment_confirmation_message(update, context)

        # Не похоже на Tronscan — ручной режим, спрашиваем аккаунт
        context.user_data['deal_id'] = text if text != '-' else ''
        await update.message.reply_text(
            "Введите название аккаунта (откуда платили):\n\n"
            "Например: Business Account или отправьте - (пропустить):"
        )
        return ENTER_ACCOUNT

    # --- Не USDT: обычный ввод ID сделки ---
    deal_id = text
    if deal_id == '-':
        deal_id = ''

    context.user_data['deal_id'] = deal_id

    await update.message.reply_text(
        "Введите название аккаунта (откуда платили):\n\n"
        "Например: Business Account или отправьте - (пропустить):"
    )
    return ENTER_ACCOUNT


async def usdt_enter_manual_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка 'Ввести вручную' после ошибки Tronscan — переключаем в ручной режим"""
    query = update.callback_query
    await query.answer()
    context.user_data['usdt_manual'] = True
    await query.edit_message_text(
        "Введите TX ID транзакции или любой номер сделки\n"
        "(или отправьте - чтобы пропустить):"
    )
    return ENTER_DEAL_ID


async def enter_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия аккаунта"""
    account_name = update.message.text.strip()

    if account_name == '-':
        account_name = ''

    context.user_data['account_name'] = account_name

    # Для USDT-заявок amount_usdt = payment_amount, пропускаем вопрос
    currency = context.user_data.get('payment_currency', '')
    if currency == config.CURRENCY_USDT:
        context.user_data['amount_usdt'] = context.user_data.get('payment_amount', 0)
        return await show_payment_confirmation_message(update, context)

    # Спрашиваем про USDT (только для не-USDT заявок)
    keyboard = [
        [InlineKeyboardButton("Да, была оплата в USDT", callback_data="usdt_yes")],
        [InlineKeyboardButton("Нет, только фиат", callback_data="usdt_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Была ли оплата в USDT (крипте)?",
        reply_markup=reply_markup
    )
    return ENTER_USDT


async def enter_usdt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора USDT"""
    query = update.callback_query
    await query.answer()

    if query.data == "usdt_no":
        context.user_data['amount_usdt'] = None
        return await show_payment_confirmation(query, context)

    await query.edit_message_text(
        "Введите сумму в USDT:\n\n"
        "Например: 357.14"
    )
    return ENTER_USDT


async def enter_usdt_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод суммы USDT"""
    try:
        amount_usdt = float(update.message.text.replace(',', '.').replace(' ', ''))
        if amount_usdt <= 0:
            raise ValueError

        context.user_data['amount_usdt'] = amount_usdt
        return await show_payment_confirmation_message(update, context)

    except ValueError:
        await update.message.reply_text(
            "Неверный формат. Введите число (например: 357.14):"
        )
        return ENTER_USDT


async def show_payment_confirmation(query, context):
    """Показать подтверждение оплаты (для callback)"""
    request = context.user_data.get('payment_request', {})
    currency = context.user_data.get('payment_currency', config.CURRENCY_RUB)
    deal_id = context.user_data.get('deal_id', '')
    account_name = context.user_data.get('account_name', '')
    amount_usdt = context.user_data.get('amount_usdt')

    currency_symbols = get_currency_symbols_dict()
    currency_symbol = currency_symbols.get(currency, '')

    confirmation = (
        f"*Подтверждение оплаты*\n\n"
        f"Дата: {request.get('date', '')}\n"
        f"Сумма: {format_amount(request.get('amount', 0), currency)} {currency_symbol}\n"
    )

    if currency == config.CURRENCY_USDT:
        confirmation += f"Кошелек: {request.get('card_or_phone', '')}\n"
    else:
        confirmation += f"Получатель: {request.get('recipient', '')}\n"

    if deal_id:
        confirmation += f"ID сделки: {deal_id}\n"
    if account_name:
        confirmation += f"Аккаунт: {account_name}\n"
    if amount_usdt:
        confirmation += f"Сумма USDT: {amount_usdt}\n"
        req_amount = request.get('amount', 0)
        if req_amount and amount_usdt:
            rate = req_amount / amount_usdt
            confirmation += f"Курс: {rate:.2f} {currency_symbol}/USDT\n"

    confirmation += "\nПодтвердите оплату:"

    keyboard = [
        [
            InlineKeyboardButton("Подтвердить", callback_data="confirm_pay"),
            InlineKeyboardButton("Отменить", callback_data="cancel_pay")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        confirmation,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return CONFIRM_PAYMENT


async def show_payment_confirmation_message(update, context):
    """Показать подтверждение оплаты (для текстового сообщения)"""
    request = context.user_data.get('payment_request', {})
    currency = context.user_data.get('payment_currency', config.CURRENCY_RUB)
    deal_id = context.user_data.get('deal_id', '')
    account_name = context.user_data.get('account_name', '')
    amount_usdt = context.user_data.get('amount_usdt')

    currency_symbols = get_currency_symbols_dict()
    currency_symbol = currency_symbols.get(currency, '')

    confirmation = (
        f"*Подтверждение оплаты*\n\n"
        f"Дата: {request.get('date', '')}\n"
        f"Сумма: {format_amount(request.get('amount', 0), currency)} {currency_symbol}\n"
    )

    if currency == config.CURRENCY_USDT:
        confirmation += f"Кошелек: {request.get('card_or_phone', '')}\n"
    else:
        confirmation += f"Получатель: {request.get('recipient', '')}\n"

    if deal_id:
        confirmation += f"ID сделки: {deal_id}\n"
    if account_name:
        confirmation += f"Аккаунт: {account_name}\n"
    if amount_usdt:
        confirmation += f"Сумма USDT: {amount_usdt}\n"
        req_amount = request.get('amount', 0)
        if req_amount and amount_usdt:
            rate = req_amount / amount_usdt
            confirmation += f"Курс: {rate:.2f} {currency_symbol}/USDT\n"

    confirmation += "\nПодтвердите оплату:"

    keyboard = [
        [
            InlineKeyboardButton("Подтвердить", callback_data="confirm_pay"),
            InlineKeyboardButton("Отменить", callback_data="cancel_pay")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        confirmation,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return CONFIRM_PAYMENT


async def confirm_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение оплаты -> запись в таблицу -> предложение загрузить чек"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_pay":
        await query.edit_message_text("Оплата отменена.")
        context.user_data.clear()
        return ConversationHandler.END

    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("Ошибка подключения к системе.")
        return ConversationHandler.END

    request = context.user_data.get('payment_request', {})
    date = context.user_data.get('payment_date', '')
    amount = context.user_data.get('payment_amount', 0)
    currency = context.user_data.get('payment_currency', config.CURRENCY_RUB)
    deal_id = context.user_data.get('deal_id', '')
    account_name = context.user_data.get('account_name', '')
    amount_usdt = context.user_data.get('amount_usdt')
    # request_id -- из отдельного поля (надежнее) или из request dict
    request_id = context.user_data.get('payment_request_id', '') or request.get('request_id', '')

    # Защита: если данные потеряны (бот перезапускался)
    if not request_id and not date:
        await query.edit_message_text(
            "Данные заявки потеряны (бот был перезапущен).\n"
            "Пожалуйста, начните оплату заново через меню."
        )
        context.user_data.clear()
        return ConversationHandler.END

    user = update.effective_user
    user_info = sheets.get_user(user.id)
    executor_name = user_info.get('name', f"ID{user.id}") if user_info else f"ID{user.id}"
    context.user_data['executor_name'] = executor_name

    # Если владелец платит заявку без исполнителя — ставим его исполнителем
    user_role = user_info.get('role', '') if user_info else ''
    if user_role == config.ROLE_OWNER and request_id:
        current_executor = request.get('executor', '').strip()
        if not current_executor:
            sheets.assign_executor(request_id, executor_name)

    # Завершаем оплату (поиск по request_id приоритетнее date+amount)
    success = sheets.complete_payment(
        date=date,
        amount=amount,
        executor_name=executor_name,
        deal_id=deal_id,
        account_name=account_name,
        amount_usdt=amount_usdt,
        currency=currency,
        request_id=request_id
    )

    if not success:
        await query.edit_message_text(
            "Ошибка при завершении оплаты. Попробуйте позже."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Уведомление owner откладывается до после загрузки чека

    currency_symbols = get_currency_symbols_dict()
    currency_symbol = currency_symbols.get(currency, '')

    done_text = (
        f"*Оплата завершена!*\n\n"
        f"Дата: {date}\n"
        f"Сумма: {format_amount(amount, currency)} {currency_symbol}\n"
    )

    if amount_usdt:
        rate = amount / amount_usdt if amount_usdt else 0
        done_text += f"Сумма USDT: {amount_usdt}\n"
        done_text += f"Курс: {rate:.2f} {currency_symbol}/USDT\n"

    done_text += "\nДанные записаны в таблицу.\n\n"
    if currency == config.CURRENCY_USDT:
        done_text += "Хотите прикрепить чек (ссылка TronScan или фото)?"
    else:
        done_text += "Хотите загрузить чек (фото или PDF)?"

    keyboard = [
        [
            InlineKeyboardButton("Загрузить чек", callback_data="receipt_yes"),
            InlineKeyboardButton("Пропустить", callback_data="receipt_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(done_text, parse_mode='Markdown', reply_markup=reply_markup)
    return UPLOAD_RECEIPT


# ===== RECEIPT UPLOAD =====

async def receipt_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора загрузки чека"""
    query = update.callback_query
    await query.answer()

    if query.data == "receipt_no":
        await query.edit_message_text("Оплата завершена. Чек не загружен.")
        await _notify_owners_about_payment(context)
        await _notify_initiator_about_payment(context)
        context.user_data.clear()
        return ConversationHandler.END

    # receipt_yes
    currency = context.user_data.get('payment_currency', '')
    if currency == config.CURRENCY_USDT:
        await query.edit_message_text(
            "Отправьте ссылку TronScan или фото скриншота:"
        )
    else:
        await query.edit_message_text(
            "Отправьте чек (фото или PDF файл):"
        )
    return UPLOAD_RECEIPT


async def handle_receipt_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать загрузку чека (фото, документ или ссылка TronScan)"""
    sheets = context.bot_data.get('sheets')
    drive = context.bot_data.get('drive_manager')

    date = context.user_data.get('payment_date', '')
    amount = context.user_data.get('payment_amount', 0)
    currency = context.user_data.get('payment_currency', config.CURRENCY_RUB)
    req_id = (
        context.user_data.get('payment_request_id', '')
        or context.user_data.get('payment_request', {}).get('request_id', '')
    )

    # Обработка текстовой ссылки (TronScan URL для USDT)
    if update.message.text:
        url = update.message.text.strip()
        if not url.startswith('http'):
            await update.message.reply_text(
                "Ссылка должна начинаться с https://\n"
                "Отправьте ссылку TronScan, фото или /cancel для отмены."
            )
            return UPLOAD_RECEIPT
        if sheets:
            sheets.update_receipt_url(date, amount, currency, url, request_id=req_id)
        await _notify_owners_about_payment(context, receipt_url=url)
        await _notify_initiator_about_payment(context, receipt_url=url)
        await update.message.reply_text(
            f"Чек (ссылка) сохранён!\n\nСсылка: {url}\n\nОплата полностью завершена."
        )
        context.user_data.clear()
        return ConversationHandler.END

    if not drive:
        await update.message.reply_text(
            "Google Drive недоступен. Чек не загружен.\n"
            "Оплата уже записана в таблицу."
        )
        await _notify_owners_about_payment(context, receipt_error=True)
        await _notify_initiator_about_payment(context, receipt_error=True)
        context.user_data.clear()
        return ConversationHandler.END

    # Определяем тип файла
    file = None
    filename = ""
    mime_type = "image/jpeg"

    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        filename = f"receipt_{date}_{amount}_{currency}.jpg"
        mime_type = "image/jpeg"
    elif update.message.document:
        doc = update.message.document
        file = await doc.get_file()
        filename = doc.file_name or f"receipt_{date}_{amount}_{currency}"
        if doc.mime_type:
            mime_type = doc.mime_type
        elif filename.lower().endswith('.pdf'):
            mime_type = "application/pdf"
        elif filename.lower().endswith('.png'):
            mime_type = "image/png"
    else:
        await update.message.reply_text(
            "Неподдерживаемый формат. Отправьте фото, PDF или ссылку TronScan.\n"
            "Или отправьте /cancel для отмены."
        )
        return UPLOAD_RECEIPT

    # Отдельный try/except только для загрузки файла
    receipt_url = None
    upload_error = False
    try:
        file_bytes = await file.download_as_bytearray()
        receipt_url = drive.upload_receipt(
            file_bytes=bytes(file_bytes),
            filename=filename,
            mime_type=mime_type
        )
    except Exception as e:
        logger.error(f"Receipt upload error: {e}")
        upload_error = True

    # Уведомления и ответ исполнителю — вне try/except загрузки
    if receipt_url and sheets:
        req_id = context.user_data.get('payment_request_id', '') or context.user_data.get('payment_request', {}).get('request_id', '')
        sheets.update_receipt_url(date, amount, currency, receipt_url, request_id=req_id)
        await _notify_owners_about_payment(context, receipt_url=receipt_url)
        await _notify_initiator_about_payment(context, receipt_url=receipt_url)
        await update.message.reply_text(
            f"Чек загружен!\n\nСсылка: {receipt_url}\n\nОплата полностью завершена."
        )
    else:
        await _notify_owners_about_payment(context, receipt_error=True)
        await _notify_initiator_about_payment(context, receipt_error=True)
        await update.message.reply_text(
            "Ошибка загрузки чека в Google Drive.\n"
            "Оплата записана, но чек не сохранен."
        )

    context.user_data.clear()
    return ConversationHandler.END


# ===== MY PAYMENTS (history) =====

@require_auth
@require_role(config.ROLE_EXECUTOR, config.ROLE_OWNER)
async def my_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать историю выплат текущего исполнителя"""
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await update.message.reply_text("Ошибка подключения к системе.")
        return

    user = update.effective_user
    user_info = sheets.get_user(user.id)
    if not user_info or not user_info.get('name'):
        await update.message.reply_text("Не удалось определить ваше имя.")
        return

    executor_name = user_info['name'].strip()
    payments = sheets.get_payments_by_executor(executor_name)

    if not payments:
        await update.message.reply_text("У вас пока нет завершенных выплат.")
        return

    # Пагинация
    page = context.user_data.get('my_payments_page', 0)
    total_pages = max(1, (len(payments) - 1) // ITEMS_PER_PAGE + 1)

    if page >= total_pages:
        page = 0

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = payments[start:end]

    currency_symbols = get_currency_symbols_dict()

    text = f"*Мои выплаты* (стр. {page + 1}/{total_pages})\n\n"

    for p in page_items:
        p_currency = p.get('currency', config.CURRENCY_RUB)
        symbol = currency_symbols.get(p_currency, '')
        text += (
            f"--- {p.get('date', '')} | {format_amount(p.get('amount', 0), p_currency)} {symbol}\n"
        )
        if p.get('deal_id'):
            text += f"ID сделки: {p['deal_id']}\n"
        if p.get('account_name'):
            text += f"Аккаунт: {p['account_name']}\n"
        if p.get('receipt_url'):
            text += f"Чек: {p['receipt_url']}\n"
        text += "\n"

    # Статистика
    total_count = len(payments)
    text += f"---\nВсего выплат: {total_count}\n"

    # Кнопки пагинации
    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("<< Назад", callback_data=f"mypay_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперед >>", callback_data=f"mypay_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def my_payments_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Навигация по страницам моих выплат"""
    query = update.callback_query
    await query.answer()

    page = int(query.data.replace('mypay_page_', ''))
    context.user_data['my_payments_page'] = page

    sheets = context.bot_data.get('sheets')
    if not sheets:
        return

    user = update.effective_user
    user_info = sheets.get_user(user.id)
    if not user_info or not user_info.get('name'):
        return

    executor_name = user_info['name'].strip()
    payments = sheets.get_payments_by_executor(executor_name)

    if not payments:
        await query.edit_message_text("У вас пока нет завершенных выплат.")
        return

    total_pages = max(1, (len(payments) - 1) // ITEMS_PER_PAGE + 1)
    if page >= total_pages:
        page = 0

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = payments[start:end]

    currency_symbols = get_currency_symbols_dict()

    text = f"*Мои выплаты* (стр. {page + 1}/{total_pages})\n\n"

    for p in page_items:
        p_currency = p.get('currency', config.CURRENCY_RUB)
        symbol = currency_symbols.get(p_currency, '')
        text += (
            f"--- {p.get('date', '')} | {format_amount(p.get('amount', 0), p_currency)} {symbol}\n"
        )
        if p.get('deal_id'):
            text += f"ID сделки: {p['deal_id']}\n"
        if p.get('account_name'):
            text += f"Аккаунт: {p['account_name']}\n"
        if p.get('receipt_url'):
            text += f"Чек: {p['receipt_url']}\n"
        text += "\n"

    total_count = len(payments)
    text += f"---\nВсего выплат: {total_count}\n"

    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("<< Назад", callback_data=f"mypay_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперед >>", callback_data=f"mypay_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ===== NOTIFICATIONS =====

async def _notify_owners_about_payment(
    context: ContextTypes.DEFAULT_TYPE,
    receipt_url: str = None,
    receipt_error: bool = False,
):
    """Отправить уведомление всем owner о завершении оплаты (с результатом загрузки чека)"""
    sheets = context.bot_data.get('sheets')
    if not sheets:
        return

    owners = sheets.get_users_by_role(config.ROLE_OWNER)
    if not owners:
        return

    request = context.user_data.get('payment_request', {})
    currency = context.user_data.get('payment_currency', config.CURRENCY_RUB)
    amount = context.user_data.get('payment_amount', 0)
    date = context.user_data.get('payment_date', '')
    executor_name = context.user_data.get('executor_name', '')
    deal_id = context.user_data.get('deal_id', '')
    amount_usdt = context.user_data.get('amount_usdt')

    currency_symbols = get_currency_symbols_dict()
    currency_symbol = currency_symbols.get(currency, '')

    text = (
        f"<b>Заявка оплачена</b>\n\n"
        f"Дата: {date}\n"
        f"Сумма: {format_amount(amount, currency)} {currency_symbol}\n"
    )

    if currency == config.CURRENCY_USDT:
        wallet = request.get('card_or_phone', '')
        if wallet:
            text += f"Кошелёк: {wallet}\n"
    else:
        if request.get('recipient'):
            text += f"Получатель: {request['recipient']}\n"
        if request.get('bank'):
            text += f"Банк: {request['bank']}\n"
        if amount_usdt:
            text += f"Сумма USDT: {amount_usdt}\n"

    purpose = request.get('purpose', '')
    if purpose:
        text += f"Назначение: {purpose}\n"

    text += f"Исполнитель: {executor_name}\n"

    if deal_id:
        text += f"ID сделки: {deal_id}\n"

    if receipt_url:
        text += f'\n<a href="{receipt_url}">Открыть чек</a>'
    elif receipt_error:
        text += f"\nЧек: ошибка загрузки"

    for owner in owners:
        try:
            owner_id = owner.get('telegram_id', '')
            if owner_id:
                await context.bot.send_message(
                    chat_id=int(float(owner_id)),
                    text=text,
                    parse_mode='HTML'
                )
                logger.info(f"Payment notification sent to owner {owner_id}")
        except Exception as e:
            logger.error(f"Failed to notify owner {owner.get('telegram_id')}: {e}")


async def _notify_initiator_about_payment(
    context: ContextTypes.DEFAULT_TYPE,
    receipt_url: str = None,
    receipt_error: bool = False,
):
    """Уведомить инициатора заявки о завершении оплаты (без исполнителя/deal_id/USDT)"""
    request = context.user_data.get('payment_request', {})
    author_id = request.get('author_id', '')
    if not author_id:
        return

    currency = context.user_data.get('payment_currency', config.CURRENCY_RUB)
    amount = context.user_data.get('payment_amount', 0)
    date = context.user_data.get('payment_date', '')

    currency_symbols = get_currency_symbols_dict()
    currency_symbol = currency_symbols.get(currency, '')

    text = (
        f"<b>Заявка оплачена</b>\n\n"
        f"Дата: {date}\n"
        f"Сумма: {format_amount(amount, currency)} {currency_symbol}\n"
    )

    if currency == config.CURRENCY_USDT:
        wallet = request.get('card_or_phone', '')
        if wallet:
            text += f"Кошелёк: {wallet}\n"
    else:
        if request.get('recipient'):
            text += f"Получатель: {request['recipient']}\n"
        if request.get('bank'):
            text += f"Банк: {request['bank']}\n"

    purpose = request.get('purpose', '')
    if purpose:
        text += f"Назначение: {purpose}\n"

    if receipt_url:
        text += f'\n<a href="{receipt_url}">Открыть чек</a>'
    elif receipt_error:
        text += f"\nЧек: ошибка загрузки"

    try:
        await context.bot.send_message(
            chat_id=int(float(author_id)),
            text=text,
            parse_mode='HTML'
        )
        logger.info(f"Payment notification sent to initiator {author_id}")
    except Exception as e:
        logger.error(f"Failed to notify initiator {author_id}: {e}")


# ===== CANCEL =====

async def payment_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена процесса оплаты"""
    await update.message.reply_text("Оплата отменена.")
    context.user_data.clear()
    return ConversationHandler.END


# ===== CONVERSATION HANDLER =====

def get_payment_conversation_handler():
    """Получить ConversationHandler для оплаты заявок"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_payment_callback, pattern=r'^(pay(req)?_|ow_pay_req_)'),
        ],
        states={
            SHOW_DETAILS: [
                CallbackQueryHandler(mark_paid_callback, pattern='^(mark_paid|cancel_pay)$'),
            ],
            ENTER_DEAL_ID: [
                CallbackQueryHandler(usdt_enter_manual_callback, pattern='^usdt_enter_manual$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_deal_id),
            ],
            ENTER_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_account)
            ],
            ENTER_USDT: [
                CallbackQueryHandler(enter_usdt_callback, pattern='^usdt_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_usdt_amount)
            ],
            CONFIRM_PAYMENT: [
                CallbackQueryHandler(confirm_payment_callback, pattern='^(confirm|cancel)_pay$')
            ],
            UPLOAD_RECEIPT: [
                CallbackQueryHandler(receipt_choice_callback, pattern='^receipt_(yes|no)$'),
                MessageHandler(filters.PHOTO, handle_receipt_upload),
                MessageHandler(filters.Document.ALL, handle_receipt_upload),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_receipt_upload),
            ],
        },
        fallbacks=[CommandHandler('cancel', payment_cancel)],
        name="payment_conversation",
        persistent=False,
        allow_reentry=True
    )
