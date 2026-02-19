---
description: How python-telegram-bot routes updates to handlers. Registration order determines priority. ConversationHandler must come before MessageHandler. CallbackQueryHandler patterns prevent handler collisions. Error handlers as middleware.
---

# Handler Routing

PTB routes each incoming update to the first matching handler in registration order. Understanding this prevents "my handler never fires" and "wrong handler fires" bugs.

## Update Types and Their Handlers

| Update type | Handler class | Triggered by |
|-------------|--------------|--------------|
| `/command` | `CommandHandler("command", fn)` | User sends `/command` |
| Inline button tap | `CallbackQueryHandler(fn, pattern=...)` | User taps InlineKeyboardButton |
| Text message | `MessageHandler(filters.TEXT, fn)` | User sends any text |
| Document/Photo | `MessageHandler(filters.Document.ALL, fn)` | User sends file |
| Any update | `TypeHandler(Update, fn)` | All updates (last resort) |

## Registration Order = Priority

```python
app = Application.builder().token(TOKEN).build()

# 1. ConversationHandler FIRST — it intercepts users mid-flow
app.add_handler(payment_conv_handler)
app.add_handler(onboarding_conv_handler)

# 2. Specific command handlers
app.add_handler(CommandHandler("start", handle_start))
app.add_handler(CommandHandler("help", handle_help))

# 3. Specific callback query handlers (if outside conversations)
app.add_handler(CallbackQueryHandler(handle_menu_action, pattern=r"^menu_"))

# 4. Catch-all handlers LAST
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))
```

If MessageHandler with `filters.TEXT` is registered before ConversationHandler, it will intercept all text messages and the conversation will never see them.

## Handler Groups

PTB supports handler groups (integers) for explicit priority ordering:

```python
# Group 0 (default) — highest priority
app.add_handler(conv_handler, group=0)

# Group 1 — runs if group 0 didn't handle it
app.add_handler(MessageHandler(filters.ALL, log_all_messages), group=1)
```

Default group is 0. Lower group numbers run first.

## CallbackQueryHandler Patterns

Without patterns, the first registered CallbackQueryHandler catches everything:

```python
# WRONG — catches ALL callback queries, other handlers never fire
app.add_handler(CallbackQueryHandler(handle_everything))

# CORRECT — pattern-matched, specific
app.add_handler(CallbackQueryHandler(handle_payment, pattern=r"^pay_\d+$"))
app.add_handler(CallbackQueryHandler(handle_cancel, pattern=r"^cancel$"))
app.add_handler(CallbackQueryHandler(handle_menu, pattern=r"^menu_"))
```

Pattern is matched against `update.callback_query.data` using `re.match()` (anchored at start).

## ConversationHandler Internal Routing

Inside a ConversationHandler, PTB routes based on current state + handler pattern:

```python
states={
    WAITING_AMOUNT: [
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount),
        CommandHandler("skip", skip_amount),
    ],
}
```

Multiple handlers per state are checked in list order. The first match wins.

## Error Handler as Middleware

An error handler catches exceptions from any handler and can send a user-facing message:

```python
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception in handler:", exc_info=context.error)

    # Notify user if possible
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Попробуйте снова или напишите /cancel"
        )

app.add_error_handler(error_handler)
```

Error handlers receive the exception via `context.error` — they don't need try/except themselves.

## Debugging Handler Registration

To see which handlers are registered:

```python
for group_handlers in app.handlers.values():
    for handler in group_handlers:
        print(type(handler).__name__, getattr(handler, 'pattern', ''))
```

## Related

- [[conversation-state]] — the ConversationHandler that must be registered first
- [[_moc_handlers]] — inline keyboard patterns and callback data design
