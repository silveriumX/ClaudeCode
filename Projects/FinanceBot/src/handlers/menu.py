"""
Постоянное меню бота с кнопками быстрого доступа
"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from src.utils.auth import get_user_info
from src import config


def get_main_menu_keyboard(user_role: str) -> ReplyKeyboardMarkup:
    """
    Получить главное меню в зависимости от роли пользователя

    Args:
        user_role: Роль пользователя (owner/manager/executor)

    Returns:
        ReplyKeyboardMarkup с кнопками меню
    """
    # Нормализуем роль к нижнему регистру (в таблице может быть Manager, OWNER и т.д.)
    role = (user_role or "").strip().lower() or None
    keyboard = []

    # Кнопки для manager и owner
    if role in [config.ROLE_MANAGER, config.ROLE_OWNER]:
        keyboard.append([
            KeyboardButton("📝 Новая заявка"),
            KeyboardButton("📋 Мои заявки")
        ])

    # Кнопки только для owner
    if role == config.ROLE_OWNER:
        keyboard.append([
            KeyboardButton("💳 Оплата заявок")
        ])

    # Кнопки для executor: создание заявок + оплата назначенных
    if role == config.ROLE_EXECUTOR:
        keyboard.append([
            KeyboardButton("📝 Новая заявка"),
            KeyboardButton("📋 Мои заявки")
        ])
        keyboard.append([
            KeyboardButton("💳 Оплата заявок"),
            KeyboardButton("💰 Мои выплаты")
        ])

    # Кнопки для report: заявки + фактические расходы
    if role == config.ROLE_REPORT:
        keyboard.append([
            KeyboardButton("📝 Новая заявка"),
            KeyboardButton("📋 Мои заявки")
        ])
        keyboard.append([
            KeyboardButton("📊 Внести расход")
        ])

    # Общие кнопки для всех
    keyboard.append([
        KeyboardButton("ℹ️ Помощь"),
        KeyboardButton("🔄 Обновить меню")
    ])

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        message: str = None) -> None:
    """
    Показать главное меню пользователю

    Args:
        update: Update объект
        context: Context объект
        message: Опциональное сообщение для отображения
    """
    user = update.effective_user
    sheets = context.bot_data.get('sheets')

    if not sheets:
        await update.message.reply_text("⚠️ Ошибка подключения к системе.")
        return

    # Получаем роль пользователя
    user_role = sheets.get_user_role(user.id)

    if not user_role:
        await update.message.reply_text(
            "❌ У вас нет доступа к боту.\n\n"
            "Обратитесь к администратору для получения прав."
        )
        return

    # Формируем приветственное сообщение
    if not message:
        role_names = {
            config.ROLE_OWNER: "Владелец",
            config.ROLE_MANAGER: "Менеджер",
            config.ROLE_EXECUTOR: "Исполнитель",
            config.ROLE_REPORT: "Учёт"
        }

        message = (
            f"📱 *Главное меню*\n\n"
            f"Ваша роль: {role_names.get(user_role, user_role)}\n\n"
            f"Выберите действие из меню ниже:"
        )

    reply_markup = get_main_menu_keyboard(user_role)

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик нажатий на кнопки меню

    Перенаправляет на соответствующие команды
    """
    text = update.message.text
    user = update.effective_user

    # Импортируем обработчики
    from handlers.start import help_command
    from handlers.request import new_request_start, my_requests
    from handlers.payment import pending_payments, my_payments
    from handlers.fact_expense import new_fact_expense_start

    # Маршрутизация по кнопкам
    if text == "📝 Новая заявка":
        await new_request_start(update, context)

    elif text == "📋 Мои заявки":
        await my_requests(update, context)

    elif text == "💳 Оплата заявок":
        await pending_payments(update, context)

    elif text == "💰 Мои выплаты":
        await my_payments(update, context)

    elif text == "📊 Внести расход":
        await new_fact_expense_start(update, context)

    elif text == "ℹ️ Помощь":
        await help_command(update, context)

    elif text == "🔄 Обновить меню":
        await show_main_menu(update, context, "🔄 Меню обновлено!")


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /menu - показать главное меню
    """
    await show_main_menu(update, context)
