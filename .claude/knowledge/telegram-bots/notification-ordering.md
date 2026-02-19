---
description: Notification ordering in Telegram bots. Business logic (DB/Sheets writes) must complete before any notification is sent. Notifying before writing creates "confirmed but not recorded" bugs. If notification needs data from multiple steps, collect all data first via user_data.
---

# Notification Ordering

A notification is a commitment. Once an owner receives "payment confirmed", they act on it. If the underlying write hasn't happened yet — or fails afterward — the notification is a lie that's hard to retract.

## The Race Condition

```python
# WRONG — notification before write
await notify_owners(deal_id=deal_id, amount=amount)  # owner acts on this
sheets.complete_payment(deal_id, amount)              # if this fails, data is lost
                                                      # but owner already thinks it's done
```

The window between the notification and the write is where bugs live. Network latency to Sheets, a quota error, a formatting issue in the data — any of these will produce a confirmed-but-not-recorded payment.

## The Rule: Write First, Notify Second

```python
# CORRECT — complete all writes, then notify
sheets.complete_payment(deal_id, amount, receipt_url)  # write first
await notify_owners(deal_id=deal_id, amount=amount)    # notify after
await notify_initiator(deal_id=deal_id)                # all notifications together
```

If the Sheets write fails, the exception propagates before any notification. The owner gets nothing, but that's correct — the error handler can send a failure notification.

## Composite Notifications

When a notification needs data from multiple handler steps (e.g., payment amount from step 2, receipt URL from step 5), collect everything into [[user-data-storage]] and fire the notification only at the final step:

```python
# Step 2 — store payment data
context.user_data['deal_id'] = deal_id
context.user_data['amount_usdt'] = amount
context.user_data['executor_name'] = executor

# Step 5 — receipt uploaded, now write everything and notify
async def handle_receipt_upload(update, context):
    receipt_url = await upload_receipt(...)

    # Write first
    sheets.complete_payment(
        context.user_data['deal_id'],
        context.user_data['amount_usdt'],
        receipt_url
    )

    # Then notify with complete data
    await notify_owners(
        deal_id=context.user_data['deal_id'],
        amount=context.user_data['amount_usdt'],
        executor=context.user_data['executor_name'],
        receipt_url=receipt_url
    )
    await notify_initiator(context.user_data['deal_id'])
```

## Multiple Notification Targets

When multiple parties need notifications (initiator + owners + admins), send them all after the write completes — not scattered across the handler:

```python
# CORRECT — all notifications after write
sheets.complete_payment(...)

# Then all notifications in sequence
await notify_owners(context, receipt_url=receipt_url)
await notify_initiator(context)
# (admin notifications if any)
```

## Exception: Pre-write Status Updates

It's acceptable to send a "processing..." message to the user before a long operation. This is UX, not a business notification:

```python
await message.reply_text("Обрабатываю чек...")   # UX: okay before write

await drive.upload(receipt)
sheets.complete_payment(...)

await notify_owners(...)                           # business notification: after write
await message.reply_text("Готово!")               # final status: after write
```

## Related

- [[try-except-scope]] — how exception handler scoping enforces this ordering
- [[user-data-storage]] — where to collect data across steps for the final notification
- [[_moc_safety]] — the full failure triangle this node belongs to
