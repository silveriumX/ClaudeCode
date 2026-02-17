# Cursor AI Integration Guide

## Overview

TelegramHub exports chat data in formats optimized for Cursor AI analysis.

---

## Export Types

### 1. Single Chat Export (Markdown)

Best for: Reading and understanding a specific conversation.

```
POST /api/export/chat
{
    "account": "account_1",
    "chat_id": 123456789,
    "limit": 200,
    "format": "markdown"
}
```

**Output:** `context/exports/account_1_ChatName_20260122_1200.md`

```markdown
# Chat Export: John Smith

**Account:** account_1
**Chat ID:** 123456789
**Type:** user
**Exported:** 2026-01-22 12:00
**Messages:** 156

---

## Conversation

### [2026-01-20 14:30] THEM
Hey, I need help with the order...

### [2026-01-20 14:32] ME
Sure, let me check. What's the order number?
```

### 2. Single Chat Export (JSON)

Best for: Statistical analysis, pattern detection.

```
POST /api/export/chat
{
    "account": "account_1",
    "chat_id": 123456789,
    "limit": 200,
    "format": "json"
}
```

**Output includes:**
- Message count statistics
- Average response time
- Message length averages
- Activity by hour
- Full message history

### 3. Multiple Chats Export

Best for: Comparing conversations, finding patterns across chats.

```
POST /api/export/multiple
{
    "chats": [
        {"account": "account_1", "chat_id": 123},
        {"account": "account_1", "chat_id": 456},
        {"account": "account_2", "chat_id": 789}
    ],
    "limit_per_chat": 100
}
```

### 4. Export by Tag

Best for: Analyzing all clients, all suppliers, etc.

```
POST /api/export/by-tag
{
    "tag_id": "client",
    "limit_per_chat": 50
}
```

---

## Using with Cursor

### Step 1: Export Data

**Option A: Via API**
```bash
curl -X POST http://127.0.0.1:8765/api/export/chat \
  -H "Content-Type: application/json" \
  -d '{"account":"account_1","chat_id":123456,"format":"markdown"}'
```

**Option B: Via Dashboard (coming soon)**
- Select chat
- Click "Export for AI"
- Choose format

### Step 2: Reference in Cursor

In Cursor chat, reference the exported file:

```
@TelegramHub/context/exports/account_1_ClientName_20260122.md

Analyze this conversation and tell me:
1. What are the main issues discussed?
2. Are there any unresolved problems?
3. What follow-up actions are needed?
```

### Step 3: Analysis Prompts

**For single chat:**
```
@TelegramHub/context/exports/chat_export.md

Analyze this Telegram conversation:

1. Summarize the main topics
2. Identify any problems or complaints
3. List action items and commitments
4. Suggest responses to open questions
5. Rate the communication quality (1-10)
```

**For multiple chats (pattern analysis):**
```
@TelegramHub/context/exports/multi_export.json

Analyze these customer conversations:

1. What are the most common issues?
2. Which problems appear repeatedly?
3. What's the average response quality?
4. Identify training opportunities
5. Create FAQ from common questions
```

**For team communication analysis:**
```
@TelegramHub/context/exports/team_chats.json

Analyze team communication patterns:

1. How do team members formulate problems?
2. What issues come up most frequently?
3. Are there communication bottlenecks?
4. Who are the most/least responsive?
5. Suggest process improvements
```

---

## Recommended Workflows

### Daily Review
1. Export all chats with "todo" tag
2. Ask Cursor to prioritize action items
3. Address urgent issues first

### Weekly Analysis
1. Export all "client" tagged chats
2. Identify recurring problems
3. Update FAQ or templates

### Team Performance
1. Export employee conversations
2. Analyze response times
3. Identify training needs

---

## Export File Locations

All exports are saved to:
```
TelegramHub/context/exports/
```

**File naming:**
- Markdown: `{account}_{chatname}_{date}_{time}.md`
- JSON: `{account}_{chatname}_{date}_{time}.json`
- Multi: `multi_export_{date}_{time}.json`

---

## API Reference

### List All Exports
```
GET /api/export/list
```

Returns list of all exported files with metadata.

### Export Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/export/chat` | POST | Export single chat |
| `/api/export/multiple` | POST | Export multiple chats |
| `/api/export/by-tag` | POST | Export all chats with tag |
| `/api/export/list` | GET | List exported files |

---

## Best Practices

1. **Export regularly** — Set up weekly exports for key chats
2. **Use tags** — Tag important chats for easy batch export
3. **Limit size** — 200 messages per chat is usually enough
4. **JSON for stats** — Use JSON format when you need metrics
5. **Markdown for reading** — Use markdown for conversation review

---

## Example Analysis Questions

### Customer Service
- "What are the top 5 complaints in these conversations?"
- "Which issues take longest to resolve?"
- "Generate response templates for common questions"

### Team Management
- "How quickly do team members respond?"
- "What tasks are frequently unclear?"
- "Identify miscommunication patterns"

### Business Intelligence
- "What products/services are most discussed?"
- "What features do customers request most?"
- "Track sentiment over time"

---

## Troubleshooting

**Export fails:**
- Check account is connected
- Verify chat_id is correct
- Ensure chat exists in account

**File not found in Cursor:**
- Use full path: `@C:\Users\...\TelegramHub\context\exports\file.md`
- Or relative: `@TelegramHub/context/exports/file.md`

**Analysis incomplete:**
- Increase message limit
- Export as JSON for full data
- Check file encoding (should be UTF-8)
