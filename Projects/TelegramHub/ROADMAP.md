# TelegramHub Roadmap v2

**Updated based on [Entergram CRM](https://entergram.com/) analysis**

---

## Current Status

**Working features:**
- Multi-account management (2+ accounts)
- Unified inbox with all chats
- Send/receive text messages
- Tags, notes, status, pin
- Quick reply templates
- Search & filter
- Cursor AI context export

---

## Phase 0: Stability & Infrastructure (CRITICAL)

Before new features, ensure stable operation.

### 0.1 Auto-Reconnect
**Priority**: CRITICAL
**Effort**: 2 hours

Session health monitoring and auto-reconnect on disconnect.
- Check connection every 60 seconds
- Auto-reconnect on failure
- UI indicator for connection status

### 0.2 Error Handling & Logging
**Priority**: CRITICAL
**Effort**: 2 hours

Proper error handling throughout the app.
- Try/catch for all API calls
- Log errors to file
- User-friendly error messages

### 0.3 Database Migration (Optional)
**Priority**: Medium
**Effort**: 4 hours

Move from JSON files to SQLite for better performance.
- SQLite for CRM data
- Faster queries
- Better concurrency

---

## Phase 1: UI Improvements (Quick Wins)

### 1.1 Custom Tags UI
**Priority**: HIGH
**Effort**: 2 hours

Full tag management in dashboard.
- Create new tag with name + color picker
- Edit existing tags
- Delete tags
- Drag to reorder

### 1.2 Custom Templates UI
**Priority**: HIGH
**Effort**: 2 hours

Template management panel.
- Add new template
- Edit template name & text
- Delete template
- Organize by category

### 1.3 Settings Page
**Priority**: Medium
**Effort**: 2 hours

Centralized settings.
- Manage tags
- Manage templates
- Account settings
- Export/Import data

---

## Phase 2: Broadcast Tool (Entergram's Key Feature)

### 2.1 Broadcast Messaging
**Priority**: VERY HIGH
**Effort**: 4-5 hours

Send same message to multiple chats at once.
- Select multiple chats (checkboxes)
- Filter by tag before broadcast
- Preview recipients
- Send with delay (avoid flood)
- Progress indicator
- Delivery report

**Use cases:**
- Announce to all clients
- Send updates to suppliers
- Mass notifications

### 2.2 Broadcast Templates
**Priority**: HIGH
**Effort**: 2 hours

Save broadcast presets.
- Save filter + template combos
- Quick re-send
- Schedule broadcasts (later)

---

## Phase 3: Analytics (Entergram's Differentiator)

### 3.1 Chat Statistics
**Priority**: HIGH
**Effort**: 3-4 hours

Per-chat analytics.
- Total messages count
- Your messages vs their messages
- Average response time
- Last activity date
- Activity trend (up/down)

### 3.2 Dashboard Overview
**Priority**: HIGH
**Effort**: 3 hours

Summary dashboard with cards.
- Total chats by status
- Unread by account
- Messages today/week
- Most active chats
- Response time average

### 3.3 Activity Heatmap
**Priority**: Medium
**Effort**: 3 hours

Visual activity patterns.
- Hour-by-hour activity
- Day-of-week patterns
- Peak hours identification

---

## Phase 4: Media Support

### 4.1 Media Preview
**Priority**: HIGH
**Effort**: 3-4 hours

View media in messages.
- Image thumbnails
- Video preview
- File info (name, size)
- Download button

### 4.2 Send Media
**Priority**: HIGH
**Effort**: 4-5 hours

Upload and send files.
- Image upload
- Document upload
- Drag & drop
- Progress bar

### 4.3 Reply to Message
**Priority**: HIGH
**Effort**: 2 hours

Reply to specific message.
- Click message to reply
- Reply preview
- Clear reply button

---

## Phase 5: Export & Reporting

### 5.1 Export to CSV/Excel
**Priority**: Medium
**Effort**: 2 hours

Export data for reporting.
- Export chat list
- Export contacts with tags
- Export message history
- Date range filter

### 5.2 Report Generation
**Priority**: Medium
**Effort**: 3 hours

Generate activity reports.
- Daily/weekly summary
- PDF export
- Email report (later)

---

## Phase 6: Advanced Features

### 6.1 Auto-Reply Rules
**Priority**: Medium
**Effort**: 6 hours

Automatic responses.
- Keyword triggers
- Time-based (office hours)
- Per-account rules
- Template responses

### 6.2 Cursor AI Integration v2
**Priority**: Medium
**Effort**: 4 hours

Enhanced AI features.
- "Generate reply" button
- Context-aware suggestions
- Draft approval workflow

### 6.3 Contact Database
**Priority**: Low
**Effort**: 6 hours

Unified contact management.
- Merge duplicate contacts
- Contact profiles
- Cross-account history

---

## Deployment & Stability Guide

### Running as Background Service

**Option 1: Windows Task Scheduler**
```
# Create scheduled task to run on startup
schtasks /create /tn "TelegramHub" /tr "python C:\path\to\main.py" /sc onstart
```

**Option 2: NSSM (Non-Sucking Service Manager)**
```
# Install as Windows service
nssm install TelegramHub "python" "C:\path\to\main.py"
nssm start TelegramHub
```

**Option 3: PM2 (if Node.js installed)**
```
pm2 start "python main.py" --name telegramhub
pm2 save
pm2 startup
```

### Production Checklist

- [ ] Enable auto-reconnect
- [ ] Set up logging to file
- [ ] Configure firewall (port 8765)
- [ ] Create Windows service
- [ ] Set up daily backup of /data folder
- [ ] Monitor disk space

---

## Updated Priority Order

| # | Feature | Impact | Effort | Source |
|---|---------|--------|--------|--------|
| 1 | Auto-reconnect | Critical | Low | Stability |
| 2 | Error handling | Critical | Low | Stability |
| 3 | **Broadcast Tool** | Very High | Medium | Entergram |
| 4 | Custom Tags UI | High | Low | User request |
| 5 | Custom Templates UI | High | Low | User request |
| 6 | Media Preview | High | Medium | Entergram |
| 7 | Dashboard Analytics | High | Medium | Entergram |
| 8 | Chat Statistics | High | Medium | Entergram |
| 9 | Export to CSV | Medium | Low | Entergram |
| 10 | Send Media | High | Medium | Core feature |

---

## Immediate Next Steps

**Today:**
1. Add auto-reconnect mechanism
2. Add basic error logging

**This week:**
3. Custom Tags UI (create/edit/delete)
4. Custom Templates UI
5. Broadcast Tool (send to multiple chats)

**Next week:**
6. Media preview in messages
7. Dashboard with analytics cards
8. Export to CSV

---

## Comparison with Entergram

| Feature | Entergram | TelegramHub | Notes |
|---------|-----------|-------------|-------|
| Multi-accounts | ✅ | ✅ | Both support |
| Tags/Labels | ✅ | ✅ | Need UI improvement |
| Templates | ✅ | ✅ | Need UI improvement |
| Broadcast | ✅ | ❌ | **Priority #1** |
| Analytics | ✅ | ❌ | Add dashboard |
| Heatmaps | ✅ | ❌ | Nice to have |
| Export | ✅ | ❌ | Add CSV export |
| Workspaces | ✅ | ❌ | Not needed for solo |
| Ticketing | ✅ | ❌ | Not needed now |
| Contact Network | ✅ | ❌ | Low priority |
| Encrypted Vault | ✅ | Partial | Sessions are files |
| Pricing | €29-49/mo | Free | Self-hosted |

**Our advantage:** Free, self-hosted, Cursor AI integration, full control.

---

## Not Implementing (Low Value for Solo Use)

- ❌ Workspaces/Teams - single user
- ❌ Contact Network Graph - complex, low value
- ❌ Ticketing System - overkill for personal use
- ❌ SOC2 compliance - not needed for personal
- ❌ Third-party integrations - Cursor is enough
