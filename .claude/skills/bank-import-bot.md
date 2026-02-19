# Bank Import Bot (AccountingBot)

> Отдельный Telegram-бот для импорта банковских выписок в единый финансовый журнал.
> Пользователь присылает файл → бот парсит → категоризирует → пишет в Google Sheets.

---

## Когда использовать

- Создаёшь AccountingBot с нуля
- Добавляешь новую команду в существующий бот
- Настраиваешь workflow импорта выписок

---

## Workflow импорта

```
Пользователь отправляет файл выписки
        ↓
Бот определяет банк и формат
        ↓
Парсит транзакции (bank-statement-parser)
        ↓
Категоризирует (transaction-categorizer)
        ↓
┌─────────────────────────────────┐
│  confidence ≥ 0.80?             │
│  ДА → записывает в журнал       │
│  НЕТ → показывает список        │
│        неразмеченных с кнопками │
└─────────────────────────────────┘
        ↓
Итоговый отчёт пользователю:
  ✅ Импортировано: 45 транзакций
  ⚠️ Требует разметки: 8 транзакций
  🔄 Пропущено дублей: 3
```

---

## Структура AccountingBot

```
AccountingBot/
├── bot.py                    # Точка входа
├── config.py                 # Настройки из .env
├── sheets.py                 # Google Sheets менеджер
├── handlers/
│   ├── import_bank.py        # /import_bank — загрузка выписки
│   ├── categorize.py         # Подтверждение категорий
│   ├── report.py             # /report — P&L
│   ├── cashflow.py           # /cashflow — балансы счетов
│   └── uncategorized.py      # /uncategorized — нераспределённые
├── parsers/
│   └── bank_statement_parser.py  # Из скилла bank-statement-parser
└── categorizer.py            # Из скилла transaction-categorizer
```

---

## Конфигурация (.env)

```bash
# Telegram
ACCOUNTING_BOT_TOKEN=...

# Google Sheets
FINANCIAL_JOURNAL_SPREADSHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_PATH=service_account.json

# OpenAI (для GPT категоризации)
OPENAI_API_KEY=...
GPT_CATEGORIZATION_ENABLED=true

# Настройки категоризации
CATEGORY_CONFIDENCE_THRESHOLD=0.80

# Авторизованные пользователи (Telegram IDs через запятую)
ALLOWED_USER_IDS=123456789,987654321

# Сопоставление счетов с юрлицами (JSON)
# Формат: {"номер_счёта": "Название юрлица"}
ACCOUNT_ENTITY_MAP={"40802810570010435344": "ИП Пирожкова Н.В."}
```

---

## Хэндлер импорта выписки

```python
"""
handlers/import_bank.py — Импорт банковской выписки
"""
import json
import logging
from pathlib import Path
import tempfile
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, CallbackQueryHandler, filters
)

from parsers.bank_statement_parser import parse_statement, detect_bank_and_format
from categorizer import (
    categorize_transaction, needs_confirmation,
    update_inn_cache, CategoryResult
)
from src import config

logger = logging.getLogger(__name__)

# States
WAITING_FILE = 1
CONFIRMING_ENTITY = 2
REVIEWING_CATEGORIES = 3


async def cmd_import_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /import_bank — начало импорта выписки."""
    user_id = update.effective_user.id
    if user_id not in config.ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🏦 <b>Импорт банковской выписки</b>\n\n"
        "Отправьте файл выписки. Поддерживаемые форматы:\n"
        "• <b>Модульбанк:</b> .txt (1C), .html, .xlsx\n"
        "• <b>Другие банки:</b> будут добавлены позже\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML"
    )
    return WAITING_FILE


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить файл выписки и начать обработку."""
    document = update.message.document
    if not document:
        await update.message.reply_text("Отправьте файл, не фото.")
        return WAITING_FILE

    # Скачиваем файл
    file_name = document.file_name
    status_msg = await update.message.reply_text(
        f"⏳ Обрабатываю: <b>{file_name}</b>...",
        parse_mode="HTML"
    )

    with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tg_file = await document.get_file()
        await tg_file.download_to_drive(tmp_path)

    try:
        # Определяем банк
        bank, fmt = detect_bank_and_format(tmp_path)

        if bank == "Неизвестный":
            await status_msg.edit_text(
                f"❌ Не удалось определить банк по файлу <b>{file_name}</b>\n\n"
                "Поддерживаемые форматы: .txt (1C Модульбанк), .html, .xlsx",
                parse_mode="HTML"
            )
            return WAITING_FILE

        # Проверяем есть ли юрлицо для этого счёта
        account_meta, transactions = parse_statement(tmp_path)
        account_number = account_meta.get("account_number", "")

        # Определяем юрлицо
        entity = config.ACCOUNT_ENTITY_MAP.get(account_number)

        if not entity:
            # Счёт незнакомый — просим указать юрлицо
            context.user_data["pending_import"] = {
                "account_meta": account_meta,
                "transactions": transactions,
                "file_name": file_name,
            }

            keyboard = [
                [InlineKeyboardButton(name, callback_data=f"entity:{entity_id}")]
                for entity_id, name in config.KNOWN_ENTITIES.items()
            ]
            keyboard.append([InlineKeyboardButton("➕ Другое (ввести вручную)", callback_data="entity:custom")])

            await status_msg.edit_text(
                f"🏦 Банк: <b>{bank}</b>\n"
                f"📋 Счёт: <code>{account_number}</code>\n"
                f"📊 Транзакций: <b>{len(transactions)}</b>\n\n"
                "Какому юрлицу принадлежит этот счёт?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return CONFIRMING_ENTITY

        # Юрлицо известно — сразу к категоризации
        context.user_data["pending_import"] = {
            "account_meta": account_meta,
            "transactions": transactions,
            "entity": entity,
            "file_name": file_name,
        }

        await status_msg.edit_text(
            f"🏦 <b>{bank}</b> | {entity}\n"
            f"📋 Счёт: <code>{account_number}</code>\n"
            f"📊 Транзакций: <b>{len(transactions)}</b>\n\n"
            "⏳ Категоризирую...",
            parse_mode="HTML"
        )
        return await _run_categorization(update, context, status_msg)

    except NotImplementedError as e:
        await status_msg.edit_text(f"❌ {e}", parse_mode="HTML")
        return WAITING_FILE
    except Exception as e:
        logger.exception(f"Ошибка при парсинге {file_name}: {e}")
        await status_msg.edit_text(
            f"❌ Ошибка при обработке файла:\n<code>{e}</code>",
            parse_mode="HTML"
        )
        return WAITING_FILE
    finally:
        tmp_path.unlink(missing_ok=True)


async def handle_entity_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать выбор юрлица."""
    query = update.callback_query
    await query.answer()

    entity_id = query.data.replace("entity:", "")
    if entity_id == "custom":
        await query.edit_message_text(
            "Введите название юрлица (например: ООО Ромашка или ИП Иванов):"
        )
        # Следующий шаг: получить текст
        context.user_data["waiting_for_entity_name"] = True
        return CONFIRMING_ENTITY

    entity = config.KNOWN_ENTITIES.get(entity_id, entity_id)
    context.user_data["pending_import"]["entity"] = entity

    await query.edit_message_text(
        f"✅ Юрлицо: <b>{entity}</b>\n\n⏳ Категоризирую...",
        parse_mode="HTML"
    )
    return await _run_categorization(update, context, query.message)


async def _run_categorization(update, context, status_msg):
    """Запустить категоризацию и записать результаты."""
    data = context.user_data["pending_import"]
    transactions = data["transactions"]
    entity = data["entity"]

    sheets = context.bot_data["sheets"]
    openai_client = context.bot_data.get("openai_client")
    inn_cache = sheets.get_inn_category_cache()

    confirmed = []      # (tx, category_result) — уверенность ≥ 0.80
    to_review = []      # (tx, category_result) — нужно подтверждение

    for tx in transactions:
        cat_result = await categorize_transaction(
            purpose=tx.purpose,
            counterparty_name=tx.counterparty_name,
            counterparty_inn=tx.counterparty_inn,
            amount=tx.amount,
            direction=tx.direction,
            inn_cache=inn_cache,
            openai_client=openai_client,
        )

        if needs_confirmation(cat_result):
            to_review.append((tx, cat_result))
        else:
            confirmed.append((tx, cat_result))

    # Записываем подтверждённые
    written, skipped = sheets.write_transactions(
        transactions=[tx for tx, _ in confirmed],
        categories=[cat for _, cat in confirmed],
        entity_name=entity,
    )

    # Сохраняем нераспределённые для следующего шага
    context.user_data["to_review"] = to_review
    context.user_data["review_index"] = 0

    summary = (
        f"✅ <b>Импорт завершён:</b> {data['file_name']}\n\n"
        f"📥 Записано: <b>{written}</b> транзакций\n"
        f"🔄 Пропущено дублей: <b>{skipped}</b>\n"
    )

    if to_review:
        summary += f"⚠️ Требует разметки: <b>{len(to_review)}</b> транзакций\n\n"
        summary += "Перейдём к разметке?"
        keyboard = [[
            InlineKeyboardButton("▶️ Начать разметку", callback_data="review:start"),
            InlineKeyboardButton("⏭ Пропустить", callback_data="review:skip"),
        ]]
        await status_msg.edit_text(
            summary, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return REVIEWING_CATEGORIES
    else:
        await status_msg.edit_text(summary, parse_mode="HTML")
        return ConversationHandler.END


async def handle_review_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать пошаговую разметку неразмеченных транзакций."""
    query = update.callback_query
    await query.answer()

    if query.data == "review:skip":
        await query.edit_message_text(
            "⏭ Разметка отложена. Используйте /uncategorized позже."
        )
        return ConversationHandler.END

    return await _show_next_for_review(update, context, query.message)


async def _show_next_for_review(update, context, message):
    """Показать следующую транзакцию для разметки."""
    to_review = context.user_data.get("to_review", [])
    idx = context.user_data.get("review_index", 0)

    if idx >= len(to_review):
        await message.edit_text("✅ Разметка завершена!")
        return ConversationHandler.END

    tx, cat_result = to_review[idx]
    total = len(to_review)

    # Кнопки с категориями
    categories = list(CATEGORIES.keys())
    buttons = []
    row = []
    for i, cat in enumerate(categories):
        # Помечаем предложение AI
        label = f"{'🤖 ' if cat == cat_result.category else ''}{cat}"
        row.append(InlineKeyboardButton(label, callback_data=f"cat:{idx}:{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    text = (
        f"🏷 <b>Разметка {idx + 1}/{total}</b>\n\n"
        f"📅 {tx.date.strftime('%d.%m.%Y')} | {'📥' if tx.direction == 'IN' else '📤'} "
        f"<b>{tx.amount:,.2f} {tx.currency}</b>\n"
        f"🏢 <b>{tx.counterparty_name}</b>\n"
        f"📝 {tx.purpose[:100]}\n\n"
        f"🤖 AI предлагает: <i>{cat_result.category}</i> "
        f"(уверенность: {cat_result.confidence:.0%})\n"
        f"Причина: {cat_result.reason}"
    )

    await message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return REVIEWING_CATEGORIES


async def handle_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать выбор категории пользователем."""
    query = update.callback_query
    await query.answer()

    _, idx_str, category = query.data.split(":", 2)
    idx = int(idx_str)
    to_review = context.user_data["to_review"]
    tx, _ = to_review[idx]

    # Записываем подтверждённую транзакцию
    sheets = context.bot_data["sheets"]
    entity = context.user_data["pending_import"]["entity"]
    confirmed_cat = CategoryResult(
        category=category,
        confidence=1.0,
        method="user_confirmed",
        reason="Подтверждено пользователем",
    )
    sheets.write_transactions([tx], [confirmed_cat], entity_name=entity)

    # Обучаем AI — сохраняем ИНН→категория
    if tx.counterparty_inn:
        update_inn_cache(sheets, tx.counterparty_inn, tx.counterparty_name, category)

    # Переходим к следующей
    context.user_data["review_index"] = idx + 1
    return await _show_next_for_review(update, context, query.message)


# ConversationHandler для регистрации в боте
def get_import_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("import_bank", cmd_import_bank)],
        states={
            WAITING_FILE: [
                MessageHandler(filters.Document.ALL, handle_file)
            ],
            CONFIRMING_ENTITY: [
                CallbackQueryHandler(handle_entity_selection, pattern="^entity:"),
            ],
            REVIEWING_CATEGORIES: [
                CallbackQueryHandler(handle_review_start, pattern="^review:"),
                CallbackQueryHandler(handle_category_confirm, pattern="^cat:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_message=False,
    )
```

---

## Хэндлер /uncategorized

```python
"""
handlers/uncategorized.py — Просмотр и разметка нераспределённых транзакций
"""
async def cmd_uncategorized(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать транзакции без категории из журнала."""
    sheets = context.bot_data["sheets"]
    uncategorized = sheets.get_uncategorized_transactions(limit=10)

    if not uncategorized:
        await update.message.reply_text("✅ Все транзакции разобраны!")
        return

    text = f"⚠️ <b>Нераспределённых: {len(uncategorized)}</b>\n\n"
    for tx in uncategorized[:5]:
        text += (
            f"📅 {tx['date']} | {tx['direction']} {tx['amount']:,.0f}₽\n"
            f"🏢 {tx['counterparty']}\n"
            f"📝 {tx['purpose'][:60]}...\n\n"
        )

    keyboard = [[
        InlineKeyboardButton("▶️ Разметить", callback_data="uncategorized:start"),
    ]]
    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

---

## Хэндлер /report (P&L)

```python
"""
handlers/report.py — P&L отчёт
"""
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """P&L за текущий месяц."""
    sheets = context.bot_data["sheets"]
    from datetime import date
    month = date.today().strftime("%Y-%m")

    stats = sheets.get_monthly_stats(month)

    text = (
        f"📊 <b>P&L за {month}</b>\n\n"
        f"📥 Выручка: <b>{stats['income']:,.0f} ₽</b>\n\n"
        f"📤 Расходы: <b>{stats['total_expense']:,.0f} ₽</b>\n"
    )

    for cat, amount in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        if amount > 0:
            text += f"  └ {cat}: {amount:,.0f} ₽\n"

    profit = stats['income'] - stats['total_expense']
    emoji = "🟢" if profit > 0 else "🔴"
    text += f"\n{emoji} <b>Прибыль: {profit:,.0f} ₽</b>"

    await update.message.reply_text(text, parse_mode="HTML")
```

---

## Команды бота

| Команда | Описание | Роль |
|---------|----------|------|
| `/import_bank` | Загрузить выписку | owner |
| `/report` | P&L за текущий месяц | owner |
| `/cashflow` | Балансы счетов | owner |
| `/uncategorized` | Нераспределённые транзакции | owner |
| `/help` | Справка | все |

---

## Деплой на Linux VPS

```bash
# 1. Клонировать репозиторий
git clone ... AccountingBot/
cd AccountingBot/

# 2. Установить зависимости
pip install python-telegram-bot gspread google-auth-oauthlib \
            beautifulsoup4 lxml openpyxl openai python-dotenv

# 3. Создать .env
cp .env.example .env
# Заполнить токены

# 4. Запустить через systemd
sudo systemctl start accounting_bot
```

---

## Связанные скиллы

- `/bank-statement-parser` — Парсинг файлов (основной инструмент)
- `/transaction-categorizer` — Категоризация транзакций
- `/financial-journal-schema` — Куда пишутся данные
- `/financial-dashboard` — Отчётность поверх журнала
- `/deploy-linux-vps` — Деплой бота на VPS
