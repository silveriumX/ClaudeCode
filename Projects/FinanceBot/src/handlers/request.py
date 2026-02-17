"""
Handler для создания заявок (менеджеры и владелец)
С выбором валюты: RUB, BYN, KZT, USDT, CNY
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
from src.utils.auth import require_auth, require_role, get_user_info
from src.utils.categories import determine_category
from src.utils.formatters import format_amount, get_currency_symbols_dict
from datetime import datetime
from src import config
import re
import logging

logger = logging.getLogger(__name__)


def _escape_md(text: str) -> str:
    """Экранировать спецсимволы Markdown V1 в пользовательском тексте"""
    if not text:
        return text
    for char in ('_', '*', '`', '[', ']', '(', ')'):
        text = text.replace(char, f'\\{char}')
    return text


# Состояния разговора - С ВЫБОРОМ ВАЛЮТЫ И ПОДДЕРЖКОЙ CNY
(CURRENCY, AMOUNT, CNY_PAYMENT_METHOD, QR_CODE_OR_REQUISITES,
 CARD_OR_PHONE, RECIPIENT, BANK, PURPOSE, CONFIRM) = range(9)


def convert_to_direct_download(drive_link: str) -> str:
    """
    Конвертировать ссылку Google Drive в прямую ссылку для скачивания.

    Принимает:
    - https://drive.google.com/file/d/FILE_ID/view
    - https://drive.google.com/open?id=FILE_ID

    Возвращает:
    - https://drive.google.com/uc?export=download&id=FILE_ID
    """
    if not drive_link or not isinstance(drive_link, str):
        return drive_link

    # Паттерны для разных форматов ссылок Google Drive
    patterns = [
        r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
        r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, drive_link)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Если не нашли паттерн Google Drive - возвращаем оригинальную ссылку
    return drive_link


@require_auth
@require_role(config.ROLE_MANAGER, config.ROLE_OWNER, config.ROLE_EXECUTOR, config.ROLE_REPORT)
async def new_request_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания заявки - выбор валюты"""
    keyboard = [
        [InlineKeyboardButton("🇷🇺 RUB (Россия)", callback_data="curr_RUB")],
        [InlineKeyboardButton("🇧🇾 BYN (Беларусь)", callback_data="curr_BYN")],
        [InlineKeyboardButton("🇰🇿 KZT (Казахстан)", callback_data="curr_KZT")],
        [InlineKeyboardButton("🇨🇳 CNY (Китай)", callback_data="curr_CNY")],
        [InlineKeyboardButton("💰 USDT (Крипто)", callback_data="curr_USDT")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📝 *Создание новой заявки*\n\n"
        "🌍 Выберите валюту:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return CURRENCY


async def request_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора валюты"""
    query = update.callback_query
    await query.answer()

    currency = query.data.replace('curr_', '')
    context.user_data['currency'] = currency

    # Лист для записи определяется при создании заявки по валюте (в sheets.create_request)
    if currency == config.CURRENCY_RUB:
        currency_name = "рублях (RUB)"
    elif currency == config.CURRENCY_BYN:
        currency_name = "белорусских рублях (BYN)"
    elif currency == config.CURRENCY_KZT:
        currency_name = "тенге (KZT)"
    elif currency == config.CURRENCY_CNY:
        currency_name = "юанях (CNY)"
    else:  # USDT
        currency_name = "USDT"

    await query.edit_message_text(
        f"✅ Валюта: {currency_name}\n\n"
        f"💰 Укажите сумму:\n\n"
        f"Например: 15000 или 15000.50",
        parse_mode='Markdown'
    )
    return AMOUNT


# Текст кнопки меню — при нажатии в середине создания заявки перезапускаем с выбора валюты
MENU_BUTTON_NEW_REQUEST = "📝 Новая заявка"


async def _restart_if_new_request_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Если пользователь нажал «Новая заявка» в середине создания — перезапустить с выбора валюты."""
    if update.message and update.message.text and update.message.text.strip() == MENU_BUTTON_NEW_REQUEST:
        await new_request_start(update, context)
        return True
    return False


async def request_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сумма"""
    if await _restart_if_new_request_button(update, context):
        return CURRENCY
    try:
        text = update.message.text.replace(',', '.').replace(' ', '').strip()
        amount = float(text)
        if amount <= 0:
            raise ValueError

        context.user_data['amount'] = amount
        # Для USDT сохраняем как ввёл пользователь — без потери знаков при отображении
        currency = context.user_data.get('currency', config.CURRENCY_RUB)
        if currency == config.CURRENCY_USDT:
            context.user_data['amount_display'] = text
        else:
            context.user_data['amount_display'] = None

        # Для CNY - выбор способа оплаты (Alipay, WeChat, банковская карта)
        if currency == config.CURRENCY_CNY:
            keyboard = [
                [InlineKeyboardButton("💳 Alipay", callback_data="cny_alipay")],
                [InlineKeyboardButton("💬 WeChat Pay", callback_data="cny_wechat")],
                [InlineKeyboardButton("🏦 Китайская банковская карта", callback_data="cny_bank_card")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "🇨🇳 Выберите способ оплаты:",
                reply_markup=reply_markup
            )
            return CNY_PAYMENT_METHOD

        # Для USDT - сразу к кошельку (без карты/телефона)
        elif currency == config.CURRENCY_USDT:
            await update.message.reply_text(
                "💳 Введите адрес кошелька:\n\n"
                "Например: TXjKu8...mNpQ2"
            )
            return CARD_OR_PHONE  # Используем то же состояние
        else:
            # Для RUB/BYN/KZT - карта или телефон
            await update.message.reply_text(
                "💳 Введите номер карты или телефон:\n\n"
                "Примеры:\n"
                "• 2202 2006 1234 5678\n"
                "• 79001234567"
            )
            return CARD_OR_PHONE

    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат суммы. Введите число (например: 15000 или 15000.50):"
        )
        return AMOUNT


async def request_cny_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора способа оплаты для CNY"""
    query = update.callback_query
    await query.answer()

    payment_method = query.data.replace('cny_', '')
    context.user_data['cny_payment_method'] = payment_method

    # Определяем название метода
    method_names = {
        'alipay': 'Alipay',
        'wechat': 'WeChat Pay',
        'bank_card': 'Китайская банковская карта'
    }
    method_name = method_names.get(payment_method, 'Неизвестный метод')

    # Для Alipay и WeChat - просим QR-код
    if payment_method in ['alipay', 'wechat']:
        await query.edit_message_text(
            f"✅ Способ оплаты: {method_name}\n\n"
            f"📸 Отправьте QR-код для оплаты (изображение)\n\n"
            f"Или введите текстовые реквизиты, если они есть:",
            parse_mode='Markdown'
        )
    else:
        # Для банковской карты - просим реквизиты
        await query.edit_message_text(
            f"✅ Способ оплаты: {method_name}\n\n"
            f"💳 Введите реквизиты банковской карты:\n\n"
            f"Например: номер карты, имя держателя и т.д.",
            parse_mode='Markdown'
        )

    return QR_CODE_OR_REQUISITES


async def request_qr_code_or_requisites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка QR-кода (фото) или текстовых реквизитов для CNY"""

    # Проверяем, получено ли фото (QR-код)
    if update.message.photo:
        await update.message.reply_text("⏳ Загружаю QR-код в Google Drive...")

        try:
            # Получаем файл с самым высоким разрешением
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            # Скачиваем байты файла
            file_bytes = await file.download_as_bytearray()

            # Загружаем в Google Drive
            from drive_manager import DriveManager
            drive = DriveManager()

            # Генерируем имя файла
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            user_id = update.effective_user.id
            payment_method = context.user_data.get('cny_payment_method', 'unknown')
            filename = f"QR_{payment_method}_{user_id}_{timestamp}.jpg"

            # Загружаем в Drive
            qr_link = drive.upload_file_from_bytes(
                file_bytes=bytes(file_bytes),
                filename=filename,
                mime_type='image/jpeg'
            )

            if qr_link:
                context.user_data['qr_code_link'] = qr_link
                context.user_data['card_or_phone'] = ''  # Пока пусто, спросим позже
                context.user_data['recipient'] = ''  # Нет получателя для CNY
                context.user_data['bank'] = payment_method.upper()  # Alipay/WeChat как "банк"

                # Предлагаем добавить текстовые реквизиты (опционально)
                keyboard = [
                    [InlineKeyboardButton("✅ Добавить реквизиты (номер карты, имя и т.д.)", callback_data="cny_add_text_requisites")],
                    [InlineKeyboardButton("⏭️ Пропустить, перейти к назначению платежа", callback_data="cny_skip_text_requisites")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"✅ QR-код успешно загружен в Google Drive!\n\n"
                    f"📸 Ссылка: {qr_link[:50]}...\n\n"
                    f"Хотите добавить текстовые реквизиты для дублирования?\n"
                    f"(Номер карты, имя получателя, название банка)",
                    reply_markup=reply_markup
                )
                return QR_CODE_OR_REQUISITES  # Остаёмся на этом этапе
            else:
                await update.message.reply_text(
                    "❌ Ошибка загрузки QR-кода. Попробуйте ещё раз или введите текстовые реквизиты:"
                )
                return QR_CODE_OR_REQUISITES

        except Exception as e:
            logger.error(f"Ошибка обработки QR-кода: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                "❌ Ошибка обработки изображения. Попробуйте ещё раз или введите текстовые реквизиты:"
            )
            return QR_CODE_OR_REQUISITES

    # Если получен текст - это текстовые реквизиты
    elif update.message.text:
        if await _restart_if_new_request_button(update, context):
            return CURRENCY

        requisites = update.message.text.strip()
        payment_method = context.user_data.get('cny_payment_method', 'unknown')

        # Если QR уже загружен, добавляем реквизиты к существующим данным
        if context.user_data.get('qr_uploaded'):
            context.user_data['card_or_phone'] = requisites
            # QR-код link уже есть в context.user_data['qr_code_link']

            await update.message.reply_text(
                f"✅ Текстовые реквизиты добавлены!\n\n"
                f"У вас теперь есть:\n"
                f"📸 QR-код (ссылка в Google Drive)\n"
                f"💳 Текстовые реквизиты\n\n"
                f"📝 Введите назначение платежа:\n\n"
                f"Например: Оплата услуг по контракту №123"
            )
            return PURPOSE
        else:
            # QR не загружен, только текстовые реквизиты
            context.user_data['card_or_phone'] = requisites
            context.user_data['qr_code_link'] = ''  # Нет QR-кода
            context.user_data['recipient'] = ''  # Нет получателя для CNY
            context.user_data['bank'] = payment_method.upper()  # Alipay/WeChat/Bank_card как "банк"

            await update.message.reply_text(
                f"✅ Реквизиты сохранены\n\n"
                f"📝 Теперь введите назначение платежа:\n\n"
                f"Например: Оплата услуг по контракту №123"
            )
            return PURPOSE

    else:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте изображение QR-кода или введите текстовые реквизиты."
        )
        return QR_CODE_OR_REQUISITES


async def request_cny_add_text_requisites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь хочет добавить текстовые реквизиты после QR-кода"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 Введите текстовые реквизиты для дублирования:\n\n"
        "Например:\n"
        "6217 1234 5678 9012\n"
        "Zhang Wei\n"
        "China Construction Bank"
    )

    # Помечаем что QR уже загружен
    context.user_data['qr_uploaded'] = True

    return QR_CODE_OR_REQUISITES


async def request_cny_skip_text_requisites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь пропускает добавление текстовых реквизитов"""
    query = update.callback_query
    await query.answer()

    # Если реквизиты не указаны, оставляем пустыми
    if not context.user_data.get('card_or_phone'):
        context.user_data['card_or_phone'] = ''

    await query.edit_message_text(
        "📝 Введите назначение платежа:\n\n"
        "Например: Оплата услуг по контракту №123"
    )

    return PURPOSE


async def request_card_or_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Номер карты/телефона или кошелек"""
    if await _restart_if_new_request_button(update, context):
        return CURRENCY
    card_or_phone = update.message.text.strip()
    context.user_data['card_or_phone'] = card_or_phone

    currency = context.user_data.get('currency', config.CURRENCY_RUB)

    # Для USDT - пропускаем получателя и банк, сразу к назначению
    if currency == config.CURRENCY_USDT:
        context.user_data['recipient'] = ''  # Нет получателя для USDT
        context.user_data['bank'] = ''  # Нет банка для USDT

        await update.message.reply_text(
            "📝 Введите назначение платежа:\n\n"
            "Например: Оплата за разработку"
        )
        return PURPOSE
    else:
        # Для RUB/BYN - запрашиваем получателя
        await update.message.reply_text(
            "👤 Введите ФИО получателя:"
        )
        return RECIPIENT


async def request_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ФИО получателя"""
    if await _restart_if_new_request_button(update, context):
        return CURRENCY
    recipient = update.message.text.strip()
    context.user_data['recipient'] = recipient

    await update.message.reply_text(
        "🏦 Введите название банка:"
    )
    return BANK


async def request_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Банк получателя"""
    if await _restart_if_new_request_button(update, context):
        return CURRENCY
    bank = update.message.text.strip()
    context.user_data['bank'] = bank

    await update.message.reply_text(
        "📝 Введите назначение платежа:\n\n"
        "Например: Оплата за разработку сайта"
    )
    return PURPOSE


async def request_purpose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение платежа"""
    if await _restart_if_new_request_button(update, context):
        return CURRENCY
    purpose = update.message.text.strip()
    context.user_data['purpose'] = purpose

    # Автоматически определяем категорию
    category = determine_category(purpose)
    context.user_data['category'] = category

    # Показываем подтверждение
    return await show_confirmation(update, context)


async def show_confirmation(update, context):
    """Показать подтверждение"""
    amount = context.user_data['amount']
    currency = context.user_data.get('currency', config.CURRENCY_RUB)
    card_or_phone = _escape_md(context.user_data['card_or_phone'])
    purpose = _escape_md(context.user_data['purpose'])
    category = _escape_md(context.user_data['category'])

    # Формируем сводку в зависимости от валюты
    if currency == config.CURRENCY_USDT:
        amount_show = context.user_data.get('amount_display') or format_amount(amount, config.CURRENCY_USDT)
        summary = (
            "📋 *Проверьте данные заявки:*\n\n"
            f"💵 Сумма: {amount_show} USDT\n"
            f"💳 Кошелёк: {card_or_phone}\n"
            f"📝 Назначение: {purpose}\n"
            f"🏷 Категория: {category} _(авто)_\n\n"
            "Всё верно?"
        )
    elif currency == config.CURRENCY_CNY:
        payment_method = context.user_data.get('cny_payment_method', 'unknown')
        qr_code_link = context.user_data.get('qr_code_link', '')

        method_names = {
            'alipay': 'Alipay',
            'wechat': 'WeChat Pay',
            'bank_card': 'Китайская банковская карта'
        }
        method_display = method_names.get(payment_method, payment_method)

        summary = (
            "📋 *Проверьте данные заявки:*\n\n"
            f"💵 Сумма: {format_amount(amount)} ¥ (CNY)\n"
            f"💳 Способ оплаты: {method_display}\n"
        )

        if qr_code_link:
            summary += f"📸 QR-код: загружен ✅\n"
        else:
            summary += f"💳 Реквизиты: {card_or_phone[:50]}...\n"

        summary += (
            f"📝 Назначение: {purpose}\n"
            f"🏷 Категория: {category} _(авто)_\n\n"
            "Всё верно?"
        )
    else:
        recipient = _escape_md(context.user_data['recipient'])
        bank = _escape_md(context.user_data['bank'])
        currency_symbol = {'BYN': 'BYN', 'KZT': '₸'}.get(currency, '₽')

        summary = (
            "📋 *Проверьте данные заявки:*\n\n"
            f"💵 Сумма: {format_amount(amount)} {currency_symbol}\n"
            f"👤 Получатель: {recipient}\n"
            f"💳 Номер карты/телефон: {card_or_phone}\n"
            f"🏦 Банк: {bank}\n"
            f"📝 Назначение: {purpose}\n"
            f"🏷 Категория: {category} _(авто)_\n\n"
            "Всё верно?"
        )

    keyboard = [
        [InlineKeyboardButton("✅ Создать заявку", callback_data="confirm_create")],
        [InlineKeyboardButton("❌ Отменить", callback_data="confirm_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        summary,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return CONFIRM


async def request_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания заявки"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_cancel":
        await query.edit_message_text("❌ Создание заявки отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    # Создаем заявку
    user = update.effective_user
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return ConversationHandler.END

    # Роль уже проверена декоратором @require_role на входе в new_request_start.
    # Повторная проверка убрана — она вызывала лишний запрос к Sheets API
    # и при квоте 429 возвращала "нет прав" ложно.

    # Лист выбирается в sheets.create_request по валюте + категории (Основные/Разные/USDT/USDT Зарплаты/CNY)
    currency = context.user_data.get('currency', config.CURRENCY_RUB)

    # Для CNY добавляем QR-код ссылку
    qr_code_link = context.user_data.get('qr_code_link', '') if currency == config.CURRENCY_CNY else None

    request_id = sheets.create_request(
        recipient=context.user_data.get('recipient', ''),
        amount=context.user_data['amount'],
        card_or_phone=context.user_data['card_or_phone'],
        bank=context.user_data.get('bank', ''),
        purpose=context.user_data['purpose'],
        category=context.user_data['category'],
        sheet_name=None,  # авто: по категории «Зарплата» / не зарплата и валюте
        currency=currency,
        author_id=str(user.id),
        author_username=user.username or '',
        author_fullname=user.full_name or '',
        qr_code_link=qr_code_link  # Новый параметр для CNY
    )

    if request_id:
        currency_display = {
            config.CURRENCY_RUB: '₽',
            config.CURRENCY_BYN: 'BYN',
            config.CURRENCY_KZT: '₸',
            config.CURRENCY_USDT: 'USDT',
            config.CURRENCY_CNY: '¥'
        }.get(currency, '₽')

        # Для USDT показываем сумму как ввёл пользователь (без округления)
        if currency == config.CURRENCY_USDT and context.user_data.get('amount_display'):
            amount_show = context.user_data['amount_display']
        else:
            amount_show = format_amount(context.user_data['amount'], currency)
        await query.edit_message_text(
            f"✅ *Заявка создана!*\n\n"
            f"ID: `{request_id}`\n"
            f"Сумма: {amount_show} {currency_display}\n"
            f"Статус: Создана\n\n"
            f"Используйте кнопки меню для быстрого доступа.",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при создании заявки. Попробуйте позже."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def request_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания заявки"""
    await update.message.reply_text("❌ Создание заявки отменено.")
    context.user_data.clear()
    return ConversationHandler.END


# ========== МОИ ЗАЯВКИ ==========

def parse_date(date_str):
    """Парсить дату из формата ДД.ММ.ГГГГ в datetime"""
    try:
        return datetime.strptime(date_str, '%d.%m.%Y')
    except:
        return datetime.min


@require_auth
async def my_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр своих заявок"""
    user = update.effective_user
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await update.message.reply_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        # Получаем все заявки со статусом "Создана" и "Оплачена" ТОЛЬКО текущего пользователя
        created_requests = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=str(user.id))
        paid_requests = sheets.get_requests_by_status(config.STATUS_PAID, author_id=str(user.id))

        all_requests = created_requests + paid_requests

        # Сортируем по дате (новые → старые)
        all_requests.sort(key=lambda x: parse_date(x['date']), reverse=True)

        # Получаем номер страницы из context (по умолчанию 1)
        page = context.user_data.get('my_requests_page', 1)
        items_per_page = 10

        # Вычисляем диапазон
        total_items = len(all_requests)
        total_pages = (total_items + items_per_page - 1) // items_per_page  # ceil
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        # Отображаем только текущую страницу
        page_requests = all_requests[start_idx:end_idx]

        if not page_requests:
            await update.message.reply_text("📋 У вас пока нет заявок.")
            return

        # Формируем сообщение
        message = f"📋 *Ваши заявки:* {total_items}\n\n"
        if total_pages > 1:
            message += f"━━━━━━━━━━━━━━━━━━━━\n"
            message += f"Страница {page} из {total_pages}\n"
            message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        keyboard = []

        # Символы валют для отображения
        currency_symbols = get_currency_symbols_dict()

        # Эмоджи для статусов
        status_emojis = {
            config.STATUS_CREATED: '⏳',  # Ожидает оплаты
            config.STATUS_PAID: '✅'      # Оплачена
        }

        # Добавляем кнопки заявок
        for req in page_requests:
            currency_symbol = currency_symbols.get(req.get('currency', config.CURRENCY_RUB), '₽')
            status_emoji = status_emojis.get(req.get('status', ''), '📋')

            req_currency = req.get('currency')
            if req_currency == config.CURRENCY_USDT:
                # Для USDT: статус - дата - сумма - кошелек (сумма без округления)
                wallet_short = req['card_or_phone'][:10] + '...' if len(req['card_or_phone']) > 10 else req['card_or_phone']
                button_text = f"{status_emoji} - {req['date']} - {format_amount(req['amount'], req_currency)} {currency_symbol} - {wallet_short}"
            elif req_currency == config.CURRENCY_CNY:
                # Для CNY: статус - дата - сумма - способ оплаты
                payment_method = req.get('bank', '')[:15]  # Alipay/WeChat/Bank_card
                button_text = f"{status_emoji} - {req['date']} - {format_amount(req['amount'], req_currency)} {currency_symbol} - {payment_method}"
            else:
                # Для RUB/BYN/KZT: статус - дата - сумма - получатель
                recipient_short = req['recipient'][:20] if len(req['recipient']) > 20 else req['recipient']
                button_text = f"{status_emoji} - {req['date']} - {format_amount(req['amount'], req_currency)} {currency_symbol} - {recipient_short}"

            # Используем request_id для уникальной идентификации заявки
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"view_req_{req['request_id']}_{page}"
            )])

        # Добавляем кнопки навигации если страниц > 1
        if total_pages > 1:
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"my_req_page_{page-1}"))

            nav_buttons.append(InlineKeyboardButton(f"• {page}/{total_pages} •", callback_data="my_req_page_current"))

            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"my_req_page_{page+1}"))

            keyboard.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await update.message.reply_text("❌ Ошибка при получении списка заявок.")


async def my_requests_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Навигация по страницам моих заявок"""
    query = update.callback_query
    await query.answer()

    # Игнорируем нажатие на текущую страницу
    if query.data == "my_req_page_current":
        return

    # Парсим номер страницы
    page = int(query.data.replace('my_req_page_', ''))

    # Сохраняем в context
    context.user_data['my_requests_page'] = page

    # Получаем данные
    user = update.effective_user
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        # Получаем заявки
        created_requests = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=str(user.id))
        paid_requests = sheets.get_requests_by_status(config.STATUS_PAID, author_id=str(user.id))

        all_requests = created_requests + paid_requests

        # Сортируем
        all_requests.sort(key=lambda x: parse_date(x['date']), reverse=True)

        # Пагинация
        items_per_page = 10
        total_items = len(all_requests)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_requests = all_requests[start_idx:end_idx]

        if not page_requests:
            await query.edit_message_text("📋 У вас пока нет заявок.")
            return

        # Формируем сообщение
        message = f"📋 *Ваши заявки:* {total_items}\n\n"
        if total_pages > 1:
            message += f"━━━━━━━━━━━━━━━━━━━━\n"
            message += f"Страница {page} из {total_pages}\n"
            message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        keyboard = []
        currency_symbols = {
            config.CURRENCY_RUB: '₽',
            config.CURRENCY_BYN: 'BYN',
            config.CURRENCY_KZT: '₸',
            config.CURRENCY_USDT: 'USDT',
            config.CURRENCY_CNY: '¥'
        }

        # Кнопки заявок
        for req in page_requests:
            currency_symbol = currency_symbols.get(req.get('currency', config.CURRENCY_RUB), '₽')

            req_currency = req.get('currency')
            if req_currency == config.CURRENCY_USDT:
                wallet_short = req['card_or_phone'][:10] + '...' if len(req['card_or_phone']) > 10 else req['card_or_phone']
                button_text = f"{req['date']} • {format_amount(req['amount'], req_currency)} {currency_symbol} • {wallet_short}"
            elif req_currency == config.CURRENCY_CNY:
                payment_method = req.get('bank', '')[:10]  # Alipay/WeChat/Bank_card
                button_text = f"{req['date']} • {format_amount(req['amount'], req_currency)} {currency_symbol} • {payment_method}"
            else:
                recipient_short = req['recipient'][:20] if len(req['recipient']) > 20 else req['recipient']
                button_text = f"{req['date']} • {format_amount(req['amount'], req_currency)} {currency_symbol} • {recipient_short}"

            # Используем request_id для уникальной идентификации заявки
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"view_req_{req['request_id']}_{page}"
            )])

        # Кнопки навигации
        if total_pages > 1:
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"my_req_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton(f"• {page}/{total_pages} •", callback_data="my_req_page_current"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"my_req_page_{page+1}"))
            keyboard.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await query.edit_message_text("❌ Ошибка при получении списка заявок.")


async def view_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр детализации заявки"""
    query = update.callback_query
    await query.answer()

    # Парсим callback: view_req_<request_id>_<page>
    parts = query.data.replace('view_req_', '').rsplit('_', 1)
    if len(parts) < 1:
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    request_id = parts[0]
    page = int(parts[1]) if len(parts) == 2 else 1

    # Сохраняем страницу для возврата
    context.user_data['return_to_page'] = page

    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    # Получаем заявку по уникальному request_id
    request = sheets.get_request_by_request_id(request_id)

    if not request:
        await query.edit_message_text("❌ Заявка не найдена.")
        return

    # Формируем детализацию
    status_emoji = '🕐' if request['status'] == config.STATUS_CREATED else '💚'

    # Символы валют
    currency_symbols = {
        config.CURRENCY_RUB: '₽',
        config.CURRENCY_BYN: 'BYN',
        config.CURRENCY_KZT: '₸',
        config.CURRENCY_USDT: 'USDT',
        config.CURRENCY_CNY: '¥'
    }
    req_currency = request.get('currency', config.CURRENCY_RUB)
    currency_symbol = currency_symbols.get(req_currency, '₽')

    details_text = (
        f"📋 *Заявка от {request['date']}*\n\n"
        f"Статус: {status_emoji} *{request['status']}*\n\n"
        f"💵 Сумма: {format_amount(request['amount'], req_currency)} {currency_symbol}\n"
    )

    # Для CNY - показываем способ оплаты, реквизиты и QR-код
    if request.get('currency') == config.CURRENCY_CNY:
        payment_method = request.get('bank', '')  # В CNY bank = способ оплаты
        method_names = {
            'ALIPAY': '💳 Alipay',
            'WECHAT': '💬 WeChat Pay',
            'BANK_CARD': '🏦 Китайская банковская карта'
        }
        method_display = method_names.get(payment_method.upper(), payment_method)

        details_text += f"🇨🇳 Способ оплаты: {method_display}\n"

        # Реквизиты
        if request.get('card_or_phone'):
            details_text += f"💳 Реквизиты: {request['card_or_phone']}\n"

        # QR-код (если есть) - будет показан как фото с caption
        # Строку "загружен (см. выше)" не добавляем - она удалится позже

        details_text += f"📝 Назначение: {request['purpose']}\n"

        # Категория и инициатор - только для owner/executor, менеджеру не показываем
        user_role = sheets.get_user_role(update.effective_user.id) or ''
        if user_role != config.ROLE_MANAGER:
            details_text += f"🏷 Категория: {request['category']}\n"

            # Инициатор заявки
            if request.get('author_fullname'):
                details_text += f"👤 Инициатор: {request['author_fullname']}\n"

            # ID сделки и аккаунт (если есть)
            if request.get('deal_id'):
                details_text += f"🔖 ID сделки: {request['deal_id']}\n"
            if request.get('account_name'):
                details_text += f"🏦 Аккаунт: {request['account_name']}\n"
    # Для USDT - другая структура
    elif request.get('currency') == config.CURRENCY_USDT:
        details_text += (
            f"💳 Кошелёк: {request['card_or_phone']}\n"
            f"📝 Назначение: {request['purpose']}\n"
            f"🏷 Категория: {request['category']}\n"
        )
    else:
        details_text += (
            f"👤 Получатель: {request['recipient']}\n"
            f"💳 Номер/телефон: {request['card_or_phone']}\n"
            f"🏦 Банк: {request['bank']}\n"
            f"📝 Назначение: {request['purpose']}\n"
            f"🏷 Категория: {request['category']}\n"
        )

    # Если оплачена — доп. инфо (Исполнитель, ID сделки) только для owner/executor; менеджеру не показываем
    user_role = sheets.get_user_role(update.effective_user.id) or ''
    show_executor_info = request['status'] == config.STATUS_PAID and user_role != config.ROLE_MANAGER
    if show_executor_info:
        if request.get('executor'):
            details_text += f"\n👤 Исполнитель: {request['executor']}"
        if request.get('deal_id'):
            details_text += f"\n🔖 ID сделки: {request['deal_id']}"

    # Ссылка на чек (для оплаченных заявок, показываем всем)
    if request['status'] == config.STATUS_PAID:
        receipt_link = request.get('receipt_link', '').strip()
        if receipt_link:
            # Конвертируем в прямую ссылку для скачивания
            direct_link = convert_to_direct_download(receipt_link)
            # Экранируем специальные символы Markdown в URL
            escaped_link = direct_link.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]').replace('(', r'\(').replace(')', r'\)')
            details_text += f"\n\n📎 Чек: {escaped_link}"

    # Кнопки
    keyboard = []
    if request['status'] == config.STATUS_CREATED:
        keyboard.append([
            InlineKeyboardButton("✏️ Редактировать",
                               callback_data=f"edit_menu_{request_id}_{page}")
        ])
        keyboard.append([
            InlineKeyboardButton("❌ Отменить заявку",
                               callback_data=f"cancel_req_{request_id}")
        ])

    keyboard.append([
        InlineKeyboardButton("« Назад к списку", callback_data=f"back_to_list_{page}")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Для CNY с QR-кодом - редактируем сообщение с медиа (или отправляем новое если это первый показ)
    qr_link = request.get('qr_code_link', '').strip() if request.get('currency') == config.CURRENCY_CNY else None

    if qr_link:
        # Убираем строку "загружен (см. выше)" из текста - она не нужна
        details_text = details_text.replace("📸 QR-код: загружен (см. выше)\n", "")

        try:
            # Конвертируем в прямую ссылку для скачивания
            direct_link = convert_to_direct_download(qr_link)

            # Проверяем, есть ли в текущем сообщении фото
            if query.message.photo:
                # Если сообщение уже содержит фото - редактируем медиа
                from telegram import InputMediaPhoto
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=direct_link,
                        caption=details_text,
                        parse_mode='Markdown'
                    ),
                    reply_markup=reply_markup
                )
            else:
                # Если это текстовое сообщение (первый показ CNY с QR) - удаляем и отправляем новое с фото
                await query.message.delete()
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=direct_link,
                    caption=details_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Ошибка отправки QR-кода: {e}")
            # Если не удалось отправить фото - отправляем просто текст со ссылкой
            escaped_qr = direct_link.replace('_', r'\_').replace('*', r'\*') if 'direct_link' in locals() else qr_link
            details_text += f"\n📸 QR-код: {escaped_qr}\n"
            try:
                await query.edit_message_text(
                    details_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except:
                # Если текстовое сообщение тоже не редактируется - отправляем новое
                await query.message.delete()
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=details_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
    else:
        # Для всех остальных валют (или CNY без QR) - просто редактируем текст
        await query.edit_message_text(
            details_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


async def edit_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования заявки"""
    query = update.callback_query
    await query.answer()

    # Парсим: edit_menu_<request_id>_<page>
    parts = query.data.replace('edit_menu_', '').rsplit('_', 1)
    if len(parts) < 1:
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    request_id = parts[0]
    page = int(parts[1]) if len(parts) == 2 else 1

    # Получаем заявку чтобы сохранить её данные
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    request = sheets.get_request_by_request_id(request_id)
    if not request:
        await query.edit_message_text("❌ Заявка не найдена.")
        return

    # Сохраняем данные для использования в других функциях
    context.user_data['edit_request_id'] = request_id
    context.user_data['edit_date'] = request['date']
    context.user_data['edit_amount'] = request['amount']
    context.user_data['edit_currency'] = request['currency']
    context.user_data['edit_page'] = page

    # Формируем кнопки в зависимости от валюты
    keyboard = [[InlineKeyboardButton("💵 Сумма", callback_data=f"edit_amount")]]

    if request['currency'] == config.CURRENCY_CNY:
        # Для CNY можем редактировать реквизиты и назначение
        keyboard.append([InlineKeyboardButton("💳 Реквизиты", callback_data=f"edit_card")])
        keyboard.append([InlineKeyboardButton("📝 Назначение", callback_data=f"edit_purpose")])
        keyboard.append([InlineKeyboardButton("📸 Обновить QR-код", callback_data=f"edit_qr_cny")])
    elif request['currency'] == config.CURRENCY_USDT:
        # Для USDT можем редактировать кошелек и назначение
        keyboard.append([InlineKeyboardButton("💳 Кошелёк", callback_data=f"edit_card")])
        keyboard.append([InlineKeyboardButton("📝 Назначение", callback_data=f"edit_purpose")])
    else:
        # Для RUB/BYN/KZT стандартное меню
        keyboard.append([InlineKeyboardButton("💳 Номер карты/телефон", callback_data=f"edit_card")])
        keyboard.append([InlineKeyboardButton("🏦 Банк", callback_data=f"edit_bank")])
        keyboard.append([InlineKeyboardButton("📝 Назначение", callback_data=f"edit_purpose")])

    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"view_req_{request_id}_{page}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Для CNY с QR-кодом сообщение содержит фото - удаляем и отправляем текстовое
    if request['currency'] == config.CURRENCY_CNY and request.get('qr_code_link'):
        try:
            # Удаляем сообщение с фото
            await query.message.delete()
            # Отправляем новое текстовое сообщение с меню редактирования
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✏️ *Что хотите изменить?*",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка отправки меню редактирования: {e}")
            await query.answer("❌ Ошибка открытия меню редактирования", show_alert=True)
    else:
        # Для остальных валют - обычное текстовое сообщение, редактируем
        await query.edit_message_text(
            "✏️ *Что хотите изменить?*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


async def back_to_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к списку заявок"""
    query = update.callback_query
    await query.answer()

    # Парсим номер страницы из callback_data
    page = 1
    if '_' in query.data:
        try:
            page = int(query.data.split('_')[-1])
        except (ValueError, IndexError):
            page = context.user_data.get('return_to_page', 1)

    context.user_data['my_requests_page'] = page

    # Получаем данные
    user = update.effective_user
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        # Получаем заявки
        created_requests = sheets.get_requests_by_status(config.STATUS_CREATED, author_id=str(user.id))
        paid_requests = sheets.get_requests_by_status(config.STATUS_PAID, author_id=str(user.id))

        all_requests = created_requests + paid_requests

        # Сортируем
        all_requests.sort(key=lambda x: parse_date(x['date']), reverse=True)

        # Пагинация
        items_per_page = 10
        total_items = len(all_requests)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_requests = all_requests[start_idx:end_idx]

        if not page_requests:
            await query.edit_message_text("📋 У вас пока нет заявок.")
            return

        # Формируем сообщение
        message = f"📋 *Ваши заявки:* {total_items}\n\n"
        if total_pages > 1:
            message += f"━━━━━━━━━━━━━━━━━━━━\n"
            message += f"Страница {page} из {total_pages}\n"
            message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        keyboard = []
        currency_symbols = get_currency_symbols_dict()

        # Эмоджи для статусов
        status_emojis = {
            config.STATUS_CREATED: '⏳',
            config.STATUS_PAID: '✅'
        }

        # Кнопки заявок
        for req in page_requests:
            req_currency = req.get('currency', config.CURRENCY_RUB)
            currency_symbol = currency_symbols.get(req_currency, '₽')
            status_emoji = status_emojis.get(req.get('status', ''), '📋')

            if req_currency == config.CURRENCY_USDT:
                wallet_short = req['card_or_phone'][:10] + '...' if len(req['card_or_phone']) > 10 else req['card_or_phone']
                button_text = f"{status_emoji} - {req['date']} - {format_amount(req['amount'], req_currency)} {currency_symbol} - {wallet_short}"
            else:
                recipient_short = req['recipient'][:20] if len(req['recipient']) > 20 else req['recipient']
                button_text = f"{status_emoji} - {req['date']} - {format_amount(req['amount'], req_currency)} {currency_symbol} - {recipient_short}"

            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"view_req_{req['request_id']}_{page}"
            )])

        # Кнопки навигации
        if total_pages > 1:
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"my_req_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton(f"• {page}/{total_pages} •", callback_data="my_req_page_current"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"my_req_page_{page+1}"))
            keyboard.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await query.edit_message_text("❌ Ошибка при получении списка заявок.")



async def cancel_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заявки (изменение статуса на 'Отменена')"""
    query = update.callback_query
    await query.answer()

    # Парсим: cancel_req_<request_id>
    request_id = query.data.replace('cancel_req_', '')
    if not request_id:
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    # Получаем заявку для проверки прав
    request = sheets.get_request_by_request_id(request_id)
    if not request:
        await query.edit_message_text("❌ Заявка не найдена.")
        return

    # Проверяем что это заявка текущего пользователя
    user = update.effective_user
    if str(request.get('author_id')) != str(user.id):
        await query.edit_message_text("❌ Вы можете отменять только свои заявки.")
        return

    # Отменяем заявку (используем новую функцию с request_id)
    success = sheets.update_request_status_by_id(
        request_id,
        config.STATUS_CANCELLED
    )

    if success:
        # Символы валют
        currency_symbols = {
            config.CURRENCY_RUB: '₽',
            config.CURRENCY_BYN: 'BYN',
            config.CURRENCY_KZT: '₸',
            config.CURRENCY_USDT: 'USDT',
            config.CURRENCY_CNY: '¥'
        }
        currency_symbol = currency_symbols.get(request['currency'], '₽')

        await query.edit_message_text(
            f"✅ *Заявка отменена*\n\n"
            f"Дата: {request['date']}\n"
            f"Сумма: {format_amount(request['amount'], request.get('currency'))} {currency_symbol}\n\n"
            f"Статус изменён на: Отменена",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Ошибка при отмене заявки. Попробуйте позже.")


async def edit_qr_cny_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление QR-кода для CNY заявки"""
    query = update.callback_query
    await query.answer()

    # Получаем request_id из context
    request_id = context.user_data.get('edit_request_id')
    if not request_id:
        await query.edit_message_text("❌ Ошибка: заявка не найдена.")
        return

    await query.edit_message_text(
        "📸 *Загрузите новый QR-код*\n\n"
        "Отправьте изображение QR-кода для Alipay или WeChat Pay.",
        parse_mode='Markdown'
    )

    # Сохраняем режим обновления QR
    context.user_data['updating_qr'] = True


async def handle_qr_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загрузки нового QR-кода"""
    if not context.user_data.get('updating_qr'):
        return

    request_id = context.user_data.get('edit_request_id')
    page = context.user_data.get('edit_page', 1)

    if not request_id:
        await update.message.reply_text("❌ Ошибка: заявка не найдена.")
        return

    sheets = context.bot_data.get('sheets')
    drive_manager = context.bot_data.get('drive_manager')

    if not sheets or not drive_manager:
        await update.message.reply_text("⚠️ Ошибка подключения к системе.")
        return

    # Загружаем новый QR-код
    await update.message.reply_text("⏳ Загружаю новый QR-код в Google Drive...")

    try:
        photo = update.message.photo[-1]  # Берём самое большое разрешение
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()

        # Загружаем в Google Drive
        qr_code_link = drive_manager.upload_file_from_bytes(
            file_bytes,
            filename=f"cny_qr_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            mime_type="image/jpeg"
        )

        if qr_code_link:
            # Обновляем ссылку в таблице
            request = sheets.get_request_by_request_id(request_id)
            if request:
                sheets.update_request_qr_code(request_id, qr_code_link)

                context.user_data.pop('updating_qr', None)

                await update.message.reply_text(
                    "✅ QR-код успешно обновлён!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Вернуться к заявке", callback_data=f"view_req_{request_id}_{page}")
                    ]])
                )
            else:
                await update.message.reply_text("❌ Заявка не найдена.")
        else:
            await update.message.reply_text("❌ Ошибка загрузки QR-кода. Попробуйте ещё раз.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении QR-кода: {e}")
        await update.message.reply_text("❌ Ошибка загрузки QR-кода. Попробуйте ещё раз.")


# ========== CONVERSATION HANDLER ==========

def get_request_conversation_handler():
    """Создание ConversationHandler для заявок"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('new_request', new_request_start),
            MessageHandler(filters.Regex('^📝 Новая заявка$'), new_request_start)
        ],
        states={
            CURRENCY: [CallbackQueryHandler(request_currency, pattern='^curr_')],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_amount)],
            CNY_PAYMENT_METHOD: [CallbackQueryHandler(request_cny_payment_method, pattern='^cny_')],
            QR_CODE_OR_REQUISITES: [
                MessageHandler(filters.PHOTO, request_qr_code_or_requisites),
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_qr_code_or_requisites),
                CallbackQueryHandler(request_cny_add_text_requisites_callback, pattern='^cny_add_text_requisites$'),
                CallbackQueryHandler(request_cny_skip_text_requisites_callback, pattern='^cny_skip_text_requisites$')
            ],
            CARD_OR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_card_or_phone)],
            RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_recipient)],
            BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_bank)],
            PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_purpose)],
            CONFIRM: [CallbackQueryHandler(request_confirm, pattern='^confirm_(create|cancel)$')]
        },
        fallbacks=[CommandHandler('cancel', request_cancel)],
        per_message=False,
        allow_reentry=True
    )
