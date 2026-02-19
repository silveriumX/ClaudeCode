---
description: Handler patterns cluster for Telegram bots. InlineKeyboard design, callback data encoding, edit vs send patterns, pagination. Navigate here when building interactive bot interfaces with buttons and menus.
---

# MOC: Handler Patterns

Covers the interactive layer of Telegram bots — keyboards, callbacks, message editing. For the routing layer, see [[handler-routing]]. For multi-step flows, see [[conversation-state]].

## InlineKeyboard Design

Inline keyboards attach to messages. Each button carries `callback_data` (string, max 64 bytes) that arrives in `update.callback_query.data`.

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Simple keyboard
keyboard = [
    [InlineKeyboardButton("Подтвердить", callback_data="confirm")],
    [InlineKeyboardButton("Отменить", callback_data="cancel")],
]
markup = InlineKeyboardMarkup(keyboard)

# Multi-column (list of rows, each row is a list of buttons)
keyboard = [
    [
        InlineKeyboardButton("USD", callback_data="currency_USD"),
        InlineKeyboardButton("USDT", callback_data="currency_USDT"),
        InlineKeyboardButton("CNY", callback_data="currency_CNY"),
    ],
    [InlineKeyboardButton("Отмена", callback_data="cancel")],
]
```

## Callback Data Encoding

64-byte limit requires compact encoding for IDs. Use structured prefixes:

```python
# Pattern: prefix_id
callback_data=f"executor_{executor_id}"    # "executor_42"
callback_data=f"deal_{deal_id}_confirm"    # "deal_1234_confirm"
callback_data=f"page_{page_num}"           # "page_3"

# Parsing in handler
data = update.callback_query.data
if data.startswith("executor_"):
    executor_id = int(data.split("_")[1])
```

For complex data, store in [[user-data-storage]] and pass only a reference key in callback_data.

## Edit vs Send

After a callback query, choose between editing the existing message or sending a new one:

```python
# Edit the message that had the button (preferred for state transitions)
await update.callback_query.edit_message_text(
    "Выберите сумму:",
    reply_markup=new_keyboard
)

# Edit just the keyboard (keep message text, change buttons)
await update.callback_query.edit_message_reply_markup(reply_markup=new_keyboard)

# Send a new message (when the flow branches significantly)
await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text="Новый этап",
    reply_markup=next_keyboard
)
```

Always call `await update.callback_query.answer()` before editing — prevents the loading spinner:

```python
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()   # acknowledge immediately
    # then do work
    await update.callback_query.edit_message_text(...)
```

## Dynamic Keyboards from Data

Building keyboards from lists (executor selection, currency lists):

```python
async def show_executor_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    executors = context.bot_data.get('executors', {})

    keyboard = []
    for exec_id, exec_data in executors.items():
        keyboard.append([
            InlineKeyboardButton(
                exec_data['name'],
                callback_data=f"executor_{exec_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])

    await update.message.reply_text(
        "Выберите исполнителя:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

## Pagination Pattern

For long lists (>10 items), paginate:

```python
PAGE_SIZE = 5

def build_page_keyboard(items: list, page: int, callback_prefix: str):
    start = page * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]

    keyboard = [
        [InlineKeyboardButton(item['name'], callback_data=f"{callback_prefix}_{item['id']}")]
        for item in page_items
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("← Назад", callback_data=f"page_{page-1}"))
    if start + PAGE_SIZE < len(items):
        nav.append(InlineKeyboardButton("Вперёд →", callback_data=f"page_{page+1}"))
    if nav:
        keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)
```

## ReplyKeyboard vs InlineKeyboard

| | InlineKeyboard | ReplyKeyboard |
|--|----------------|---------------|
| Position | Below message | Bottom of screen |
| Data | callback_data (silent) | Sends text message |
| Removal | edit_message_reply_markup | ReplyKeyboardRemove() |
| Use for | State transitions, actions | Persistent navigation, mode switching |

## Nodes in This Cluster

This MOC covers keyboard patterns. For the broader handler routing mechanism (how updates reach these handlers), see [[handler-routing]]. For multi-step state management that these keyboards drive, see [[conversation-state]].

When keyboard messages contain dynamic URLs (receipt links, Drive links), apply [[parse-mode]] rules — use HTML or InlineKeyboardButton, never Markdown v1 with dynamic hrefs.
