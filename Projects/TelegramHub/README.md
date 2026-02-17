# TelegramHub CRM

**Unified CRM for managing multiple Telegram accounts**

Multi-account Telegram management system with CRM features, tags, templates, and Cursor AI integration.

---

## Features

### Core
- **Multi-account support** — connect unlimited Telegram accounts
- **Unified inbox** — all chats from all accounts in one panel
- **Send/receive messages** — full messaging support
- **Real-time sync** — auto-refresh every 30 seconds

### CRM
- **Tags** — categorize chats (Client, Supplier, Important, etc.)
- **Custom tags** — create your own tags with colors
- **Notes** — add notes to any chat
- **Status tracking** — New / Active / Pending / Closed
- **Pin chats** — keep important chats at top
- **Search** — find chats by name
- **Filter by tag** — view only tagged chats

### Productivity
- **Quick replies (Templates)** — one-click common responses
- **Filter by account** — view specific account's chats
- **Context sync** — export data for Cursor AI

---

## Project Structure

```
TelegramHub/
├── server/                 # Backend
│   ├── main.py            # FastAPI server + Web UI
│   ├── telegram_manager.py # Telegram API wrapper
│   ├── crm_data.py        # CRM data management
│   ├── auth_web.py        # Account authorization UI
│   ├── cursor_integration.py # Cursor AI helpers
│   ├── config.py          # Configuration
│   └── requirements.txt   # Dependencies
├── accounts/
│   └── sessions/          # Telegram session files
├── data/
│   ├── crm_chats.json     # Tags, notes, statuses
│   └── templates.json     # Quick reply templates
├── context/               # Cursor AI context files
│   ├── active_chats/      # All chats JSON
│   ├── pending_replies/   # Unread chats
│   └── summaries/         # Markdown summaries
├── drafts/
│   └── outbox.json        # AI-generated drafts
└── README.md
```

---

## Installation

### 1. Install dependencies

```bash
cd TelegramHub/server
pip install -r requirements.txt
```

### 2. Authorize accounts

```bash
python auth_web.py
```

Open http://127.0.0.1:8766 and add your Telegram accounts.

### 3. Start dashboard

```bash
python main.py
```

Open http://127.0.0.1:8765

---

## API Reference

### Accounts
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/accounts` | GET | List connected accounts |

### Dialogs & Messages
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dialogs` | GET | Get all dialogs (params: limit, tag, search) |
| `/api/messages/{account}/{chat_id}` | GET | Get messages from chat |
| `/api/send` | POST | Send message |

### CRM
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crm/tags` | GET | List all tags |
| `/api/crm/tags` | POST | Create new tag |
| `/api/crm/tags/{id}` | DELETE | Delete tag |
| `/api/crm/chat/{account}/{chat_id}` | GET | Get chat CRM data |
| `/api/crm/chat/tag/add` | POST | Add tag to chat |
| `/api/crm/chat/tag/remove` | POST | Remove tag from chat |
| `/api/crm/chat/notes` | POST | Set chat notes |
| `/api/crm/chat/status` | POST | Set chat status |
| `/api/crm/chat/pin` | POST | Toggle pin |

### Templates
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/templates` | GET | List templates |
| `/api/templates` | POST | Create template |
| `/api/templates/{id}` | DELETE | Delete template |

### Sync
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync` | POST | Sync context to files |

---

## Configuration

Edit `server/config.py`:

```python
API_ID = 2040              # Telegram API ID
API_HASH = "..."           # Telegram API Hash
HOST = "127.0.0.1"         # Server host
PORT = 8765                # Server port
MAX_MESSAGES_PER_CHAT = 50 # Messages to load
SYNC_INTERVAL = 300        # Auto-sync interval (seconds)
```

---

## Cursor AI Integration

The system exports context files for Cursor AI:

- `context/active_chats/all_chats.json` — all dialogs data
- `context/pending_replies/unread.json` — chats with unread messages
- `context/pending_replies/unread.md` — markdown summary
- `context/summaries/dialogs_summary.md` — overview table

### Using with Cursor

1. Click "Sync" button to update context files
2. In Cursor, reference `@TelegramHub/context/` files
3. Ask Cursor to analyze chats, suggest replies, etc.

---

## Tech Stack

- **Backend**: FastAPI, Uvicorn
- **Telegram**: Telethon (MTProto)
- **Storage**: JSON files
- **Frontend**: Vanilla JS (embedded in FastAPI)

---

---

## Documentation

| File | Description |
|------|-------------|
| [README.md](README.md) | This file - overview and setup |
| [ROADMAP.md](ROADMAP.md) | Feature roadmap and priorities |
| [SECURITY.md](SECURITY.md) | Account safety and backup guide |
| [CURSOR_INTEGRATION.md](CURSOR_INTEGRATION.md) | AI analysis workflow |

---

## License

MIT
