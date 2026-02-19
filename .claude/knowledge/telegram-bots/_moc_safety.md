---
description: Safety cluster for Telegram bots. Maps the three failure modes that cause silent production bugs: parse_mode errors, double notifications from wide try/except, and notification-before-write race conditions. Read this when debugging unexpected bot behavior.
---

# MOC: Telegram Bot Safety

Three failure modes that don't raise visible exceptions but cause real damage in production.

## The Failure Triangle

The three nodes below interact with each other. Understanding one requires understanding the others:

```
[[parse-mode]] failure
       ↓
caught by wide [[try-except-scope]]
       ↓
triggers second notify → [[notification-ordering]] violated
```

This is why a single Google Drive URL with `_` in it can cause a payment to be reported twice.

## Nodes in This Cluster

**[[parse-mode]]** — The entry point for most "my bot stopped sending messages" bugs.
Markdown v1 is a footgun: it works for static text, breaks silently for anything dynamic.
The fix is a decision tree: static text → Markdown OK; dynamic content → HTML or no parse_mode; clickable dynamic link → InlineKeyboardButton.

**[[try-except-scope]]** — The scoping rule that prevents double notifications.
Narrow try/except covers only the risky I/O operation (upload, API call). Notifications and reply_text live outside the try block. This makes the failure mode explicit instead of silent.

**[[notification-ordering]]** — The sequencing rule: write first, notify second.
Business logic (Sheets write, DB update) completes before any notification leaves. If the write fails, no notification should have gone out.

## How to Debug a Silent Failure

1. Check if the handler uses `parse_mode='Markdown'` with any dynamic string → [[parse-mode]]
2. Check if `await context.bot.send_message(...)` or `notify_owners(...)` is inside a try block that also covers an upload → [[try-except-scope]]
3. Check if any notification fires before `sheets.complete_payment()` or equivalent → [[notification-ordering]]
4. Check if two bot processes are running simultaneously → [[conflict-error]] (in deployment cluster)

## Related

When the safety issue is in a multi-step flow (e.g., the payment receipt upload step), combine with [[conversation-state]] to understand which step the failure happens in and what's in [[user-data-storage]] at that point.
