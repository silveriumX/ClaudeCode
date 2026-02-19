---
description: State storage in python-telegram-bot handlers. user_data for per-user state across conversation steps, bot_data for shared in-memory state, chat_data for group context. How to carry payment and deal data through multi-step flows without losing it.
---

# user_data Storage

PTB provides three storage scopes in `context`. Choosing the right one prevents bugs where data disappears between handler steps.

## Storage Scopes

| Storage | Scope | Persists across | Use for |
|---------|-------|-----------------|---------|
| `context.user_data` | Per user | All handlers in a conversation | Payment flow state, user's current deal |
| `context.chat_data` | Per chat | All handlers in the chat | Group-specific settings, shared counters |
| `context.bot_data` | Global | All users, all chats | Lookup tables, shared cache, config |

**Default behavior:** all three are in-memory dicts, reset on bot restart. For persistence, see PicklePersistence or custom persistence.

## FinanceBot Payment Flow Pattern

A payment involves executor name (step 1) → amount (step 2) → payment details (step 3) → receipt (step 5). Everything must be available at the notification step:

```python
# Step: executor selected
async def handle_executor_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    executor_id = int(update.callback_query.data.split('_')[1])
    context.user_data['executor_id'] = executor_id
    context.user_data['executor_name'] = executors[executor_id]['name']
    await update.callback_query.answer()
    return WAITING_AMOUNT

# Step: amount entered
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = float(update.message.text)
    context.user_data['amount_usdt'] = amount
    context.user_data['deal_id'] = generate_deal_id()
    return WAITING_PAYMENT_DETAILS

# Step: receipt uploaded — all data is available
async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    receipt_url = await upload_receipt(update.message.document)

    # Read everything stored across steps
    deal_id = context.user_data['deal_id']
    amount = context.user_data['amount_usdt']
    executor = context.user_data['executor_name']

    # Write — see notification-ordering.md
    sheets.complete_payment(deal_id, amount, executor, receipt_url)
    await notify_owners(context, receipt_url=receipt_url)
    return ConversationHandler.END
```

## Keys to Always Store

For payment/deal flows, store these at the earliest possible step:

```python
context.user_data['deal_id']          # unique identifier for the deal
context.user_data['amount_usdt']      # amount
context.user_data['currency']         # CNY, USD, USDT etc.
context.user_data['executor_id']      # Telegram user ID
context.user_data['executor_name']    # display name for notifications
context.user_data['payment_request']  # the full payment request dict
context.user_data['initiator_id']     # who initiated (for notify_initiator)
```

## Cleaning Up

After ConversationHandler.END, clean up to avoid stale data on next conversation:

```python
async def handle_completion(update, context):
    # ... do work ...

    # Clean up conversation-specific keys
    for key in ['deal_id', 'amount_usdt', 'executor_id', 'payment_request']:
        context.user_data.pop(key, None)

    return ConversationHandler.END
```

Don't `context.user_data.clear()` — this removes persistent user preferences too.

## bot_data for Shared Lookup Tables

When multiple handlers need the same data (executor list, exchange rates, config):

```python
# In Application initialization or first use
async def load_shared_data(context: ContextTypes.DEFAULT_TYPE):
    context.bot_data['executors'] = sheets.get_executors()
    context.bot_data['exchange_rate'] = api.get_rate('CNY')

# In any handler
executors = context.bot_data.get('executors', {})
```

## Missing Key Pattern

Always use `.get()` with a default for user_data reads — the conversation could have been interrupted:

```python
# WRONG — KeyError if conversation restarted
deal_id = context.user_data['deal_id']

# CORRECT — explicit default with early return
deal_id = context.user_data.get('deal_id')
if not deal_id:
    await update.message.reply_text("Начните заново /start")
    return ConversationHandler.END
```

## Related

- [[conversation-state]] — the ConversationHandler that controls which handler receives updates
- [[notification-ordering]] — why all data must be in user_data before the final step
- [[try-except-scope]] — what happens to user_data if an intermediate step fails
