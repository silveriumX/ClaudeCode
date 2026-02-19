---
description: Telegram bot development knowledge graph. Navigate here first when building or debugging python-telegram-bot bots. Covers message safety, state management, deployment, and handler architecture. Five production bots in this workspace use these patterns.
---

# Telegram Bot — Knowledge Graph

Built on python-telegram-bot (PTB) v20+. Production bots in this workspace: FinanceBot, VoiceBot, EnglishTutorBot, MediaDownloaderBot, ChatManager.

## Safety (start here for production issues)

Silent failures are the main risk in Telegram bots — they produce no stack trace, just wrong behavior. Three failure modes cause most of them:

- [[parse-mode]] — Markdown v1 drops messages with `_` `*` `[` in dynamic content (names, amounts, Drive URLs); when to use HTML or buttons instead
- [[try-except-scope]] — a wide exception handler around upload + notify will send the notification twice on any failure; the fix is surgical scoping
- [[notification-ordering]] — notifying owners before writing to Sheets is a race condition that produces "payment confirmed but not recorded" bugs

The three interact: a [[parse-mode]] failure inside a wide [[try-except-scope]] will trigger a [[notification-ordering]] violation. Read [[_moc_safety]] for the full picture.

## State & Conversation Flow

- [[conversation-state]] — ConversationHandler patterns for multi-step flows: WAITING states, entry points, fallbacks, and why `per_message=False` is almost always right
- [[user-data-storage]] — what belongs in `context.user_data` vs `bot_data` vs `chat_data`; how to carry payment data across 4-5 handler steps without losing it

## Handler Architecture

- [[handler-routing]] — how PTB routes updates: command vs callback_query vs message handlers, priority order, and why ConversationHandler must come before MessageHandler
- [[_moc_handlers]] — deeper dive: inline keyboards, callback patterns, error handlers as middleware

## Deployment

- [[conflict-error]] — the Telegram "Conflict: terminated by other getUpdates request" error means two instances are running; deleteWebhook + 25-30s wait is the fix

## Explorations Needed

- How to test async handlers without running a real bot (mock Application)
- Redis-backed state for multi-server deployments (bot_data persistence)
- Rate limiting patterns for bots with many concurrent users
