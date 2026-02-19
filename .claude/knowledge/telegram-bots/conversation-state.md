---
description: ConversationHandler in python-telegram-bot. Multi-step conversation flows with WAITING states, entry_points, fallbacks. How PTB routes updates through conversation states. When to use per_message=True vs False.
---

# Conversation State

ConversationHandler is PTB's mechanism for multi-step flows. It tracks which "state" a user is in and routes updates to the corresponding handler function.

## Structure

```python
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# State constants (integers or strings — integers preferred)
WAITING_AMOUNT, WAITING_DETAILS, WAITING_RECEIPT = range(3)

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("pay", start_payment)],
    states={
        WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        WAITING_DETAILS: [
            CallbackQueryHandler(handle_bank_selected, pattern=r"^bank_\d+$"),
            CallbackQueryHandler(handle_wallet_selected, pattern=r"^wallet_"),
        ],
        WAITING_RECEIPT: [MessageHandler(filters.Document.ALL | filters.PHOTO, handle_receipt)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_payment),
        MessageHandler(filters.COMMAND, unexpected_command),
    ],
    per_message=False,    # almost always False
    allow_reentry=True,   # allows /pay again if stuck
)
```

## per_message: Almost Always False

`per_message=True` tracks state per individual message (needed only for InlineQueryHandlers). For all conversation flows with callback queries from inline keyboards, use `per_message=False` (the default).

With `per_message=True`, callback_query handlers won't match because each callback comes from a different "message" context. This is the most common ConversationHandler misconfiguration.

## Entry Points and Re-entry

`entry_points` list is checked first regardless of current state. If a user is mid-conversation and hits `/pay` again, they'll restart only if `allow_reentry=True`. Without it, `/pay` mid-conversation does nothing.

For FinanceBot payment flows: `allow_reentry=True` is essential because users sometimes abandon flows and need to restart.

## Fallbacks

Fallbacks run when no state handler matches:

```python
fallbacks=[
    CommandHandler("cancel", cancel),
    CommandHandler("start", restart_flow),
    # Catch anything unexpected
    MessageHandler(filters.ALL, handle_unexpected),
]
```

The `handle_unexpected` fallback prevents the bot from being stuck silently:

```python
async def handle_unexpected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используйте кнопки для навигации или /cancel для отмены"
    )
    return  # stays in current state (returns None = no state change)
```

## State Return Values

Handler functions signal state transitions by their return value:

```python
return WAITING_RECEIPT        # move to next state
return ConversationHandler.END  # end the conversation
return None                   # stay in current state (no transition)
```

Returning nothing (implicit `return None`) keeps the user in the current state. This is correct for "invalid input, please try again" scenarios.

## Callback Query Patterns

In states with multiple callback sources (bank selection AND wallet selection on the same step), use pattern matching:

```python
WAITING_DETAILS: [
    CallbackQueryHandler(handle_bank, pattern=r"^bank_\d+$"),
    CallbackQueryHandler(handle_wallet, pattern=r"^wallet_(BTC|ETH|USDT)$"),
    CallbackQueryHandler(handle_back, pattern=r"^back$"),
],
```

Always call `await update.callback_query.answer()` at the start of callback handlers — Telegram will show a loading indicator otherwise:

```python
async def handle_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    # ... rest of handler
```

## Registering in Application

ConversationHandler must be registered before catch-all MessageHandlers:

```python
app = Application.builder().token(TOKEN).build()

# Conversation handler first
app.add_handler(conv_handler)

# Generic handlers after
app.add_handler(MessageHandler(filters.TEXT, handle_generic_message))
```

See [[handler-routing]] for why registration order matters.

## State in user_data

The current state drives WHAT handlers run; [[user-data-storage]] holds the actual DATA (amounts, IDs, names) accumulated across steps. They're complementary — state is PTB's routing table, user_data is the application's working memory.

## Related

- [[user-data-storage]] — how to carry data across the states defined here
- [[handler-routing]] — how PTB dispatches updates and why ConversationHandler priority matters
- [[_moc_handlers]] — inline keyboard patterns used in conversation states
