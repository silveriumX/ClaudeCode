---
description: try/except scoping in Telegram bot handlers. Wide exception handlers around upload + notify cause double notifications. The fix: narrow try/except covers only the I/O operation; notifications live outside. Critical for payment and receipt flows.
---

# try/except Scope

The scoping of exception handlers is a structural decision that determines whether bot failures are silent and damaging or explicit and safe. A wide try/except that covers both an I/O operation and a notification call will send the notification twice on any I/O failure.

## The Double-Notification Bug

```python
# WRONG — one parse_mode error in reply_text triggers second notify_owners
try:
    url = await drive.upload(file)
    await sheets.save(url)
    await notify_owners(url=url)          # first notification
    await message.reply_text(url)         # if this raises (parse_mode bug)...
except Exception as e:
    await notify_owners(error=True)       # ...second notification fires
    await message.reply_text("Ошибка")
```

The user gets "payment confirmed" followed immediately by "payment failed". The data is saved, but owner sees two contradictory messages.

This is how a [[parse-mode]] bug in `reply_text` can cause a [[notification-ordering]] violation even when the data write was successful.

## The Fix: Surgical Scoping

```python
# CORRECT — try/except covers only the upload; notifications are unconditional
upload_url = None
try:
    file_bytes = await document.get_file()
    upload_url = await drive_client.upload(file_bytes, filename)
except Exception as e:
    logger.error(f"Upload failed: {e}")

# Notifications and replies are OUTSIDE the try block
if upload_url:
    await sheets.save(upload_url)
    await notify_owners(url=upload_url)
    await message.reply_text(f"Загружено")   # no parse_mode with dynamic URL
else:
    await notify_owners(error=True)
    await message.reply_text("Ошибка загрузки")
```

Now if `reply_text` fails, no second notification fires — the try block is already closed.

## Scope Rules

**Inside try/except (risky I/O):**
- File downloads from Telegram
- Uploads to Google Drive
- External API calls (payment processors, etc.)
- Database writes that might fail

**Outside try/except (always runs):**
- `notify_owners()` calls
- `await message.reply_text()` to user
- `await context.bot.send_message()` to any chat
- Logging the outcome

## When Multiple Steps Can Fail

For flows with several risky operations, use separate try blocks:

```python
# Each risky operation gets its own try block
receipt_url = None
try:
    file_bytes = await receipt_file.get_file()
    raw = await file_bytes.download_as_bytearray()
    receipt_url = await drive_client.upload(raw, f"receipt_{deal_id}.jpg")
except Exception as e:
    logger.error(f"Receipt upload failed for deal {deal_id}: {e}")

payment_saved = False
try:
    sheets.complete_payment(deal_id, amount, receipt_url)
    payment_saved = True
except Exception as e:
    logger.error(f"Sheets write failed for deal {deal_id}: {e}")

# Single notification point with full state
if payment_saved:
    await notify_owners(deal_id=deal_id, amount=amount, receipt_url=receipt_url)
    await message.reply_text("Платёж подтверждён")
else:
    await notify_owners(error=True, deal_id=deal_id)
    await message.reply_text("Ошибка при записи платежа")
```

## FinanceBot Context

In FinanceBot's payment flow, the receipt upload and Sheets write are separate risky operations. The notify_initiator and notify_owners calls must come after both succeed. State between steps lives in [[user-data-storage]].

## Related

- [[parse-mode]] — the most common trigger for the double-notification bug
- [[notification-ordering]] — the sequencing rule that this scoping pattern enforces
- [[user-data-storage]] — how to carry `receipt_url` and `deal_id` to the notification step
