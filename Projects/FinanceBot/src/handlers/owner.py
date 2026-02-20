"""
Панель владельца: просмотр всех заявок, назначение исполнителей,
отмена заявок, уведомления о новых заявках.

Блоки:
  1 — Просмотр всех заявок (все статусы, пагинация, фильтр)
  2 — Назначение/смена исполнителя через бот
  3 — Отмена любой заявки (без проверки автора)
  4 — Управление пользователями (список, смена роли, удаление)
  5 — Статистика системы (/stats)
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


def _get_assignable_users(sheets) -> List[Dict]:
    """Пользователи которых можно назначить исполнителем: EXECUTOR + OWNER (без дубликатов)."""
    executors = sheets.get_users_by_role(config.ROLE_EXECUTOR)
    owners = sheets.get_users_by_role(config.ROLE_OWNER)
    seen_ids: set = set()
    result: List[Dict] = []
    for u in executors + owners:
        tid = u.get('telegram_id')
        if tid not in seen_ids:
            seen_ids.add(tid)
            result.append(u)
    return result


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

    executors = _get_assignable_users(sheets)
    if not executors:
        await query.answer("Нет доступных исполнителей.", show_alert=True)
        return

    text = (
        f"<b>👤 Назначить исполнителя</b>\n\n"
        f"Заявка: <code>{_esc(request_id)}</code>\n\n"
        f"Выберите исполнителя из списка:"
    )

    buttons = []
    for idx, ex in enumerate(executors):
        name = ex.get('name') or ex.get('username') or f"Исполнитель {idx + 1}"
        role = ex.get('role', '')
        role_tag = ' 👑' if role == config.ROLE_OWNER else ''
        name_display = f"{name}{role_tag}"
        cb = f"set_exec_{idx}_{request_id}"
        if len(cb.encode()) <= 64:
            buttons.append([InlineKeyboardButton(name_display, callback_data=cb)])

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

    executors = _get_assignable_users(sheets)
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


# ===== BLOCK 4: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ =====

ROLE_DISPLAY: Dict[str, tuple] = {
    config.ROLE_OWNER:    ('👑', 'Владелец'),
    config.ROLE_MANAGER:  ('🟢', 'Менеджер'),
    config.ROLE_EXECUTOR: ('⚡', 'Исполнитель'),
    config.ROLE_REPORT:   ('📊', 'Учёт'),
}

# Русские названия для записи в Sheets (совместимо с get_users_by_role)
ROLE_TO_SHEET: Dict[str, str] = {
    config.ROLE_OWNER:    'Владелец',
    config.ROLE_MANAGER:  'Менеджер',
    config.ROLE_EXECUTOR: 'Исполнитель',
    config.ROLE_REPORT:   'Учёт',
}

ROLE_ORDER = [
    config.ROLE_OWNER,
    config.ROLE_MANAGER,
    config.ROLE_EXECUTOR,
    config.ROLE_REPORT,
]


async def owner_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Точка входа — кнопка «👥 Пользователи»."""
    sheets = context.bot_data.get('sheets')
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not sheets or not msg:
        if msg:
            await msg.reply_text("⚠️ Ошибка подключения к системе.")
        return

    user = update.effective_user
    role = sheets.get_user_role(user.id)
    if role != config.ROLE_OWNER:
        await msg.reply_text("❌ Раздел доступен только владельцам.")
        return

    await _show_users_list(update, context, edit=False)


async def _show_users_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    edit: bool = False
) -> None:
    """Список всех пользователей, сгруппированный по ролям."""
    sheets = context.bot_data.get('sheets')
    if not sheets:
        return

    all_users = sheets.get_all_users()

    by_role: Dict[str, List[Dict]] = {r: [] for r in ROLE_ORDER}
    for u in all_users:
        r = u.get('role', '')
        if r in by_role:
            by_role[r].append(u)

    total = len(all_users)
    lines = [f"<b>👥 Пользователи</b> ({total})"]
    keyboard = []

    for role_key in ROLE_ORDER:
        users_in_role = by_role[role_key]
        if not users_in_role:
            continue
        emoji, label = ROLE_DISPLAY[role_key]
        lines.append(f"\n{emoji} <b>{label}</b> ({len(users_in_role)})")
        for u in users_in_role:
            name = u.get('name') or u.get('username') or u.get('telegram_id', '?')
            tid = str(u.get('telegram_id', '')).strip()
            btn_label = f"{emoji} {name}"
            if len(btn_label) > 55:
                btn_label = btn_label[:52] + '…'
            keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"ow_user_{tid}")])

    if not all_users:
        lines.append("\n<i>Пользователей нет.</i>")

    text = '\n'.join(lines)
    markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            logger.warning(f"_show_users_list edit failed: {e}")
    else:
        target = update.message or (update.callback_query.message if update.callback_query else None)
        if target:
            await target.reply_text(text, reply_markup=markup, parse_mode='HTML')


async def ow_user_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Карточка пользователя. Паттерн: ow_user_TID"""
    query = update.callback_query
    await query.answer()

    tid_str = query.data[len('ow_user_'):]
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        tid = int(float(tid_str))
    except (ValueError, TypeError):
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    user_data = sheets.get_user(tid)
    if not user_data:
        await query.edit_message_text(
            "❌ Пользователь не найден.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="ow_users_back")
            ]])
        )
        return

    role = user_data.get('role', '')
    emoji, role_label = ROLE_DISPLAY.get(role, ('❓', role or 'Неизвестно'))
    name = _esc(user_data.get('name') or '—')
    username = user_data.get('username') or ''
    username_line = f"@{_esc(username.lstrip('@'))}" if username else '—'

    text = (
        f"<b>👤 Пользователь</b>\n\n"
        f"Имя: {name}\n"
        f"Username: {username_line}\n"
        f"Telegram ID: <code>{_esc(tid_str)}</code>\n"
        f"Роль: {emoji} {_esc(role_label)}"
    )
    buttons = [
        [InlineKeyboardButton("🔄 Сменить роль", callback_data=f"ow_chgrole_{tid_str}")],
        [InlineKeyboardButton("🚫 Заблокировать (убрать роль)", callback_data=f"ow_rmuser_{tid_str}")],
        [InlineKeyboardButton("⬅️ Назад к списку", callback_data="ow_users_back")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')


async def ow_chgrole_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Выбор новой роли. Паттерн: ow_chgrole_TID"""
    query = update.callback_query
    await query.answer()

    tid_str = query.data[len('ow_chgrole_'):]
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        tid = int(float(tid_str))
    except (ValueError, TypeError):
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    user_data = sheets.get_user(tid)
    name = _esc((user_data.get('name') or tid_str) if user_data else tid_str)

    text = (
        f"<b>🔄 Смена роли</b>\n\n"
        f"Пользователь: {name}\n\n"
        f"Выберите новую роль:"
    )
    buttons = [
        [InlineKeyboardButton(
            f"{ROLE_DISPLAY[r][0]} {ROLE_DISPLAY[r][1]}",
            callback_data=f"ow_setrole_{tid_str}_{r}"
        )]
        for r in ROLE_ORDER
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"ow_user_{tid_str}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')


async def ow_setrole_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Применить смену роли. Паттерн: ow_setrole_TID_ROLE"""
    query = update.callback_query
    await query.answer()

    # ow_setrole_1234567890_executor → отрезаем префикс, rsplit по последнему _
    data = query.data[len('ow_setrole_'):]
    try:
        tid_str, role_key = data.rsplit('_', 1)
    except ValueError:
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    if role_key not in ROLE_DISPLAY:
        await query.edit_message_text("❌ Неизвестная роль.")
        return

    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        tid = int(float(tid_str))
    except (ValueError, TypeError):
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    sheet_role = ROLE_TO_SHEET[role_key]
    success = sheets.update_user_role(tid, sheet_role)
    emoji, role_label = ROLE_DISPLAY[role_key]

    if success:
        user_data = sheets.get_user(tid)
        name = _esc((user_data.get('name') or tid_str) if user_data else tid_str)
        await query.edit_message_text(
            f"✅ <b>Роль изменена</b>\n\n"
            f"Пользователь: {name}\n"
            f"Новая роль: {emoji} {_esc(role_label)}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ К списку пользователей", callback_data="ow_users_back")
            ]])
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при смене роли. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="ow_users_back")
            ]])
        )


async def ow_rmuser_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Подтверждение удаления. Паттерн: ow_rmuser_TID"""
    query = update.callback_query
    await query.answer()

    tid_str = query.data[len('ow_rmuser_'):]
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        tid = int(float(tid_str))
    except (ValueError, TypeError):
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    user_data = sheets.get_user(tid)
    name = _esc((user_data.get('name') or tid_str) if user_data else tid_str)

    text = (
        f"⚠️ <b>Заблокировать пользователя?</b>\n\n"
        f"{name}\n\n"
        f"Роль будет очищена — пользователь потеряет доступ к боту.\n"
        f"Запись в таблице сохранится."
    )
    buttons = [
        [InlineKeyboardButton("✅ Да, заблокировать", callback_data=f"ow_confirmrm_{tid_str}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"ow_user_{tid_str}")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')


async def ow_confirmrm_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Выполнить удаление. Паттерн: ow_confirmrm_TID"""
    query = update.callback_query
    await query.answer()

    tid_str = query.data[len('ow_confirmrm_'):]
    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        tid = int(float(tid_str))
    except (ValueError, TypeError):
        await query.edit_message_text("❌ Ошибка формата данных.")
        return

    user_data = sheets.get_user(tid)
    name = _esc((user_data.get('name') or tid_str) if user_data else tid_str)

    success = sheets.deactivate_user(tid)

    if success:
        await query.edit_message_text(
            f"✅ <b>Пользователь заблокирован</b>\n\n"
            f"{name} больше не имеет доступа к боту.\n"
            f"Запись в таблице сохранена.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ К списку пользователей", callback_data="ow_users_back")
            ]])
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при блокировке. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data=f"ow_user_{tid_str}")
            ]])
        )


async def ow_users_back_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Вернуться к списку пользователей. Паттерн: ow_users_back"""
    query = update.callback_query
    await query.answer()
    await _show_users_list(update, context, edit=True)


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

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "👤 Назначить исполнителя",
            callback_data=f"assign_exec_{request_id}"
        )],
        [InlineKeyboardButton(
            "💳 Оплатить самостоятельно",
            callback_data=f"ow_pay_req_{request_id}"
        )],
        [InlineKeyboardButton(
            "❌ Отменить заявку",
            callback_data=f"own_cancel_req_{request_id}"
        )],
    ])

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


# ===== BLOCK 5: СТАТИСТИКА =====

def _parse_month_year(date_str: str):
    """Извлечь (month, year) из строки даты. Поддерживает DD.MM.YYYY и YYYY-MM-DD."""
    from datetime import datetime
    if not date_str:
        return None, None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d.%m.%y'):
        try:
            d = datetime.strptime(str(date_str).strip()[:10], fmt)
            return d.month, d.year
        except ValueError:
            continue
    return None, None


def _build_stats_text(all_requests: List[Dict]) -> str:
    """Сформировать текст статистики из списка заявок."""
    from collections import Counter, defaultdict
    from datetime import datetime

    now = datetime.now()
    cur_month, cur_year = now.month, now.year

    month_names = {
        1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель',
        5: 'май', 6: 'июнь', 7: 'июль', 8: 'август',
        9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь',
    }

    # Разбиваем по статусам
    created = [r for r in all_requests if r.get('status') == config.STATUS_CREATED]
    paid = [r for r in all_requests if r.get('status') == config.STATUS_PAID]
    cancelled = [r for r in all_requests if r.get('status') == config.STATUS_CANCELLED]

    # Оплаченные в текущем месяце
    paid_month = [
        r for r in paid
        if _parse_month_year(r.get('date', '')) == (cur_month, cur_year)
    ]

    # Суммы по валюте
    def sums_by_currency(reqs: List[Dict]) -> dict:
        totals: Dict[str, float] = defaultdict(float)
        for r in reqs:
            totals[r.get('currency', config.CURRENCY_RUB)] += float(r.get('amount', 0) or 0)
        return dict(totals)

    active_sums = sums_by_currency(created)
    month_sums = sums_by_currency(paid_month)

    # Топ исполнителей по числу оплат
    executor_counts = Counter(
        r.get('executor', '').strip()
        for r in paid
        if r.get('executor', '').strip()
    )
    top_exec = executor_counts.most_common(5)

    lines = [f"<b>📈 Статистика системы</b>", ""]

    # --- Общие счётчики ---
    lines.append("<b>Всего заявок</b>")
    lines.append(f"🔵 Создана:  {len(created)}")
    lines.append(f"✅ Оплачена: {len(paid)}")
    lines.append(f"❌ Отменена: {len(cancelled)}")
    lines.append(f"Итого: {len(all_requests)}")
    lines.append("")

    # --- Активные (на оплату) ---
    lines.append("<b>На оплату (активные)</b>")
    if active_sums:
        for currency in sorted(active_sums):
            sym = format_currency_symbol(currency)
            lines.append(f"  {format_amount(active_sums[currency], currency)} {sym}")
    else:
        lines.append("  Нет активных заявок")
    lines.append("")

    # --- Оплачено в текущем месяце ---
    month_label = f"{month_names.get(cur_month, '')} {cur_year}"
    lines.append(f"<b>Оплачено в {month_label}</b>")
    if month_sums:
        for currency in sorted(month_sums):
            sym = format_currency_symbol(currency)
            lines.append(f"  {format_amount(month_sums[currency], currency)} {sym}")
        lines.append(f"  ({len(paid_month)} выплат)")
    else:
        lines.append("  Нет выплат в этом месяце")
    lines.append("")

    # --- Топ исполнителей ---
    if top_exec:
        lines.append("<b>Топ исполнителей (всего оплат)</b>")
        medals = ['🥇', '🥈', '🥉', '4.', '5.']
        for i, (name, count) in enumerate(top_exec):
            medal = medals[i] if i < len(medals) else f"{i + 1}."
            lines.append(f"  {medal} {_esc(name)}: {count}")
    else:
        lines.append("<b>Топ исполнителей</b>\n  Нет данных")

    return '\n'.join(lines)


async def owner_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Точка входа — кнопка «📈 Статистика» или /stats."""
    sheets = context.bot_data.get('sheets')
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not sheets or not msg:
        if msg:
            await msg.reply_text("⚠️ Ошибка подключения к системе.")
        return

    user = update.effective_user
    role = sheets.get_user_role(user.id)
    if role != config.ROLE_OWNER:
        await msg.reply_text("❌ Раздел доступен только владельцам.")
        return

    loading = await msg.reply_text("⏳ Собираю статистику…")

    try:
        all_requests = sheets.get_all_requests()
        text = _build_stats_text(all_requests)
    except Exception as e:
        logger.error(f"owner_stats error: {e}")
        await loading.edit_text("❌ Ошибка при сборе статистики. Попробуйте позже.")
        return

    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Обновить", callback_data="ow_stats_refresh"),
        InlineKeyboardButton("📊 Все заявки", callback_data="ow_go_all_req"),
    ]])
    await loading.edit_text(text, parse_mode='HTML', reply_markup=markup)


async def owner_stats_refresh_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обновить статистику по кнопке «🔄 Обновить»."""
    query = update.callback_query
    await query.answer("Обновляю…")

    sheets = context.bot_data.get('sheets')
    if not sheets:
        await query.edit_message_text("⚠️ Ошибка подключения к системе.")
        return

    try:
        all_requests = sheets.get_all_requests()
        text = _build_stats_text(all_requests)
    except Exception as e:
        logger.error(f"owner_stats_refresh error: {e}")
        await query.answer("Ошибка при обновлении.", show_alert=True)
        return

    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Обновить", callback_data="ow_stats_refresh"),
        InlineKeyboardButton("📊 Все заявки", callback_data="ow_go_all_req"),
    ]])
    try:
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=markup)
    except Exception:
        pass  # Текст не изменился — Telegram вернёт ошибку, это нормально


async def ow_go_all_req_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Переход к списку всех заявок из экрана статистики."""
    query = update.callback_query
    await query.answer()
    context.user_data['ow_filter'] = 'cr'
    context.user_data['ow_page'] = 0
    await _show_list(update, context, edit=True)
