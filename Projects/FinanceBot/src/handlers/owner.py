"""
Панель владельца: просмотр всех заявок, назначение исполнителей,
отмена заявок, уведомления о новых заявках.

Блоки:
  1 — Просмотр всех заявок (все статусы, пагинация, фильтр)
  2 — Назначение/смена исполнителя через бот
  3 — Отмена любой заявки (без проверки автора)
  6 — Уведомление владельцев при создании новой заявки
"""
import html
import logging
from typing import List, Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src import config
from src.utils.formatters import format_amount, format_currency_symbol

logger = logging.getLogger(__name__)

PAGE_SIZE = 5

# Маппинг кодов фильтров → статусы (None = все)
FILTER_MAP: Dict[str, Optional[str]] = {
    'cr': config.STATUS_CREATED,
    'pd': config.STATUS_PAID,
    'cn': config.STATUS_CANCELLED,
    'al': None,
}

FILTER_LABELS = {
    'cr': 'Создана',
    'pd': 'Оплачена',
    'cn': 'Отменена',
    'al': 'Все',
}


def _esc(value) -> str:
    """HTML-escape значение."""
    return html.escape(str(value or ''))


def _format_list_line(req: Dict) -> str:
    """Краткая строка для кнопки в списке заявок."""
    date = str(req.get('date', ''))[:10]
    amount = req.get('amount', 0)
    currency = req.get('currency', '')
    sym = format_currency_symbol(currency)
    author = req.get('author_fullname') or req.get('author_username') or '—'
    # Обрезаем длинные имена
    if len(author) > 12:
        author = author[:11] + '…'
    status = req.get('status', '')
    emoji = {'Создана': '🔵', 'Оплачена': '✅', 'Отменена': '❌'}.get(status, '❓')
    return f"{emoji} {date} | {format_amount(amount, currency)} {sym} | {author}"


def _build_list_keyboard(
    page_reqs: List[Dict],
    page: int,
    total: int,
    filter_code: str
) -> InlineKeyboardMarkup:
    """Построить клавиатуру для страницы списка заявок."""
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    # Строка фильтров
    filter_row = []
    for k, label in FILTER_LABELS.items():
        btn_label = f"[{label}]" if k == filter_code else label
        filter_row.append(InlineKeyboardButton(btn_label, callback_data=f"all_req_f_{k}"))

    keyboard = [filter_row]

    # Кнопки заявок
    for req in page_reqs:
        req_id = req.get('request_id', '')
        line = _format_list_line(req)
        if len(line) > 55:
            line = line[:52] + '…'
        keyboard.append([InlineKeyboardButton(line, callback_data=f"view_all_req_{req_id}")])

    # Пагинация
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"all_req_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="ow_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"all_req_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    return InlineKeyboardMarkup(keyboard)


def _fetch_requests(sheets, filter_code: str) -> List[Dict]:
    """Получить заявки для выбранного фильтра."""
    status = FILTER_MAP.get(filter_code)
    if status is None:
        return sheets.get_all_requests()
    return sheets.get_requests_by_status(status)


async def _show_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    edit: bool = False
) -> None:
    """Показать текущую страницу списка заявок."""
    sheets = context.bot_data.get('sheets')
    if not sheets:
        return

    filter_code = context.user_data.get('ow_filter', 'cr')
    page = context.user_data.get('ow_page', 0)

    requests = _fetch_requests(sheets, filter_code)
    total = len(requests)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    context.user_data['ow_page'] = page

    start = page * PAGE_SIZE
    page_reqs = requests[start: start + PAGE_SIZE]

    filter_label = FILTER_LABELS.get(filter_code, 'Все')
    text = (
        f"<b>📊 Все заявки — {filter_label}</b>\n"
        f"Всего: {total} | Стр. {page + 1}/{total_pages}"
    )
    if not page_reqs:
        text += "\n\n<i>Заявок нет.</i>"

    markup = _build_list_keyboard(page_reqs, page, total, filter_code)

    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=markup, parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(f"owner._show_list edit failed: {e}")
    else:
        target = (
            update.message
            or (update.callback_query.message if update.callback_query else None)
        )
        if target:
            await target.reply_text(text, reply_markup=markup, parse_mode='HTML')


# ===== BLOCK 1: ПРОСМОТР ВСЕХ ЗАЯВОК =====

async def owner_all_requests(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Точка входа — кнопка меню «📊 Все заявки» или /owner_requests."""
    sheets = context.bot_data.get('sheets')
    if not sheets:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text("⚠️ Ошибка подключения к системе.")
        return

    user = update.effective_user
    role = sheets.get_user_role(user.id)
    if role != config.ROLE_OWNER:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text("❌ Раздел доступен только владельцам.")
        return

    context.user_data['ow_filter'] = 'cr'
    context.user_data['ow_page'] = 0
    await _show_list(update, context, edit=False)


async def all_req_filter_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик all_req_f_XX — смена фильтра статуса."""
    query = update.callback_query
    await query.answer()

    filter_code = query.data.replace('all_req_f_', '')
    if filter_code not in FILTER_MAP:
        return

    context.user_data['ow_filter'] = filter_code
    context.user_data['ow_page'] = 0
    await _show_list(update, context, edit=True)


async def all_req_page_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик all_req_page_N — пагинация."""
    query = update.callback_query
    await query.answer()

    try:
        page = int(query.data.replace('all_req_page_', ''))
    except ValueError:
        return

    context.user_data['ow_page'] = page
    await _show_list(update, context, edit=True)


async def view_all_req_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик view_all_req_REQID — детальный просмотр заявки."""
    query = update.callback_query
    await query.answer()

    request_id = query.data.replace('view_all_req_', '')
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    req = sheets.get_request_by_request_id(request_id)
    if not req:
        await query.edit_message_text("❌ Заявка не найдена.")
        return

    currency = req.get('currency', '')
    sym = format_currency_symbol(currency)
    amount = req.get('amount', 0)
    status = req.get('status', '')
    status_emoji = {'Создана': '🔵', 'Оплачена': '✅', 'Отменена': '❌'}.get(status, '❓')

    lines = [
        f"<b>📋 Заявка</b> <code>{_esc(request_id)}</code>",
        f"Дата: {_esc(req.get('date', ''))}",
        f"Сумма: {format_amount(amount, currency)} {_esc(sym)}",
    ]
    if req.get('recipient'):
        lines.append(f"Получатель: {_esc(req['recipient'])}")
    if req.get('card_or_phone'):
        lines.append(f"Реквизиты: {_esc(req['card_or_phone'])}")
    if req.get('bank'):
        lines.append(f"Банк/способ: {_esc(req['bank'])}")
    if req.get('purpose'):
        lines.append(f"Назначение: {_esc(req['purpose'])}")
    if req.get('category'):
        lines.append(f"Категория: {_esc(req['category'])}")

    lines.append(f"Статус: {status_emoji} {_esc(status)}")

    executor = req.get('executor', '')
    lines.append(f"Исполнитель: {_esc(executor) if executor else '—'}")

    author = req.get('author_fullname') or req.get('author_username') or '—'
    lines.append(f"Инициатор: {_esc(author)}")

    if req.get('deal_id'):
        lines.append(f"ID сделки: {_esc(req['deal_id'])}")
    if req.get('receipt_link'):
        lines.append(f"Чек: {_esc(req['receipt_link'])}")

    text = '\n'.join(lines)

    buttons = []
    if status == config.STATUS_CREATED:
        buttons.append([
            InlineKeyboardButton(
                "👤 Назначить исполнителя",
                callback_data=f"assign_exec_{request_id}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                "❌ Отменить заявку",
                callback_data=f"own_cancel_req_{request_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_all_req")
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )


async def back_to_all_req_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик back_to_all_req — возврат к списку."""
    query = update.callback_query
    await query.answer()
    await _show_list(update, context, edit=True)


async def ow_noop_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик ow_noop — кнопка-счётчик страниц (ничего не делает)."""
    await update.callback_query.answer()


# ===== BLOCK 2: НАЗНАЧЕНИЕ ИСПОЛНИТЕЛЯ =====

async def assign_exec_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик assign_exec_REQID — показать список исполнителей."""
    query = update.callback_query
    await query.answer()

    request_id = query.data.replace('assign_exec_', '')
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    executors = sheets.get_users_by_role(config.ROLE_EXECUTOR)
    if not executors:
        await query.answer("Исполнители не найдены в системе.", show_alert=True)
        return

    text = (
        f"<b>👤 Назначить исполнителя</b>\n\n"
        f"Заявка: <code>{_esc(request_id)}</code>\n\n"
        f"Выберите исполнителя из списка:"
    )

    buttons = []
    for idx, ex in enumerate(executors):
        name = ex.get('name') or ex.get('username') or f"Исполнитель {idx + 1}"
        cb = f"set_exec_{idx}_{request_id}"
        if len(cb.encode()) <= 64:
            buttons.append([InlineKeyboardButton(name, callback_data=cb)])

    buttons.append([
        InlineKeyboardButton("⬅️ Назад", callback_data=f"view_all_req_{request_id}")
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )


async def set_exec_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик set_exec_IDX_REQID — подтвердить назначение исполнителя."""
    query = update.callback_query
    await query.answer()

    # Формат: set_exec_0_REQ-20240115-143022-001
    # split('_', 3) → ['set', 'exec', '0', 'REQ-...']
    parts = query.data.split('_', 3)
    if len(parts) < 4:
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    try:
        exec_idx = int(parts[2])
    except ValueError:
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    request_id = parts[3]
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    executors = sheets.get_users_by_role(config.ROLE_EXECUTOR)
    if exec_idx >= len(executors):
        await query.edit_message_text("❌ Исполнитель не найден.")
        return

    executor = executors[exec_idx]
    executor_name = executor.get('name') or executor.get('username') or ''
    executor_tid = executor.get('telegram_id', '')

    success = sheets.assign_executor(request_id, executor_name)
    if not success:
        await query.edit_message_text("❌ Ошибка при назначении исполнителя. Попробуйте позже.")
        return

    # Уведомить исполнителя
    if executor_tid:
        try:
            req = sheets.get_request_by_request_id(request_id)
            if req:
                currency = req.get('currency', '')
                sym = format_currency_symbol(currency)
                notif = (
                    f"📋 <b>Вам назначена заявка</b>\n\n"
                    f"ID: <code>{_esc(request_id)}</code>\n"
                    f"Сумма: {format_amount(req.get('amount', 0), currency)} {_esc(sym)}\n"
                    f"Назначение: {_esc(req.get('purpose', ''))}\n\n"
                    f"Перейдите в раздел «💳 Оплата заявок» для обработки."
                )
                await context.bot.send_message(
                    chat_id=int(executor_tid),
                    text=notif,
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.warning(f"set_exec: не удалось уведомить исполнителя {executor_tid}: {e}")

    await query.edit_message_text(
        f"✅ <b>Исполнитель назначен</b>\n\n"
        f"Заявка: <code>{_esc(request_id)}</code>\n"
        f"Исполнитель: {_esc(executor_name)}",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_all_req")
        ]])
    )


# ===== BLOCK 3: ОТМЕНА ЛЮБОЙ ЗАЯВКИ (OWNER) =====

async def owner_cancel_req_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработчик own_cancel_req_REQID — владелец отменяет любую заявку."""
    query = update.callback_query
    await query.answer()

    request_id = query.data.replace('own_cancel_req_', '')
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    req = sheets.get_request_by_request_id(request_id)
    if not req:
        await query.edit_message_text("❌ Заявка не найдена.")
        return

    if req.get('status') == config.STATUS_CANCELLED:
        await query.edit_message_text(
            "ℹ️ Заявка уже отменена.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_all_req")
            ]])
        )
        return

    success = sheets.update_request_status_by_id(request_id, config.STATUS_CANCELLED)
    if not success:
        await query.edit_message_text("❌ Ошибка при отмене заявки. Попробуйте позже.")
        return

    # Уведомить инициатора
    author_id = req.get('author_id', '')
    if author_id:
        try:
            currency = req.get('currency', '')
            sym = format_currency_symbol(currency)
            notif = (
                f"❌ <b>Ваша заявка отменена</b>\n\n"
                f"ID: <code>{_esc(request_id)}</code>\n"
                f"Сумма: {format_amount(req.get('amount', 0), currency)} {_esc(sym)}\n"
                f"Назначение: {_esc(req.get('purpose', ''))}\n\n"
                f"Заявка отменена владельцем."
            )
            await context.bot.send_message(
                chat_id=int(author_id),
                text=notif,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(f"owner_cancel: не удалось уведомить инициатора {author_id}: {e}")

    currency = req.get('currency', '')
    sym = format_currency_symbol(currency)
    await query.edit_message_text(
        f"✅ <b>Заявка отменена</b>\n\n"
        f"ID: <code>{_esc(request_id)}</code>\n"
        f"Сумма: {format_amount(req.get('amount', 0), currency)} {_esc(sym)}\n\n"
        f"Инициатор уведомлён.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_all_req")
        ]])
    )


# ===== BLOCK 6: УВЕДОМЛЕНИЕ ВЛАДЕЛЬЦЕВ О НОВОЙ ЗАЯВКЕ =====

async def notify_owners_new_request(
    context: ContextTypes.DEFAULT_TYPE,
    request_id: str,
    amount: float,
    currency: str,
    author_name: str,
    purpose: str,
    recipient: str = ''
) -> None:
    """
    Уведомить всех владельцев о создании новой заявки.

    Вызывается из handlers/request.py после успешного create_request().
    """
    sheets = context.bot_data.get('sheets')
    if not sheets:
        return

    owners = sheets.get_users_by_role(config.ROLE_OWNER)
    if not owners:
        return

    sym = format_currency_symbol(currency)
    amount_str = f"{format_amount(amount, currency)} {sym}"

    text = (
        f"🆕 <b>Новая заявка</b>\n\n"
        f"ID: <code>{_esc(request_id)}</code>\n"
        f"Сумма: {_esc(amount_str)}\n"
        f"Назначение: {_esc(purpose)}\n"
    )
    if recipient:
        text += f"Получатель: {_esc(recipient)}\n"
    text += f"Инициатор: {_esc(author_name)}"

    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "👤 Назначить исполнителя",
            callback_data=f"assign_exec_{request_id}"
        )
    ]])

    for owner in owners:
        tid = owner.get('telegram_id', '')
        if not tid:
            continue
        try:
            await context.bot.send_message(
                chat_id=int(tid),
                text=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(f"notify_owners: не удалось уведомить владельца {tid}: {e}")
