# TelegramHub Security Guide

## Account Safety

### What Can Cause Account Ban

| Action | Risk Level | Our Approach |
|--------|------------|--------------|
| Mass messaging (100+ chats) | HIGH | Limited to 20-30 with delays |
| Sending same message repeatedly | HIGH | Vary text, use templates |
| Adding users to groups | VERY HIGH | Never do automatically |
| Too many API requests | MEDIUM | Rate limiting built-in |
| Logging in from new device | LOW | We use existing sessions |
| Automated replies | LOW | Safe with reasonable delays |

### Built-in Protections

1. **Rate Limiting**
   - Minimum 2 second delay between messages
   - Broadcast limited to 30 chats per batch
   - 5 second delay between broadcast messages

2. **Flood Wait Handling**
   - Automatic detection of FloodWaitError
   - Pause and retry after wait period
   - Log all flood events

3. **Session Safety**
   - Sessions stored locally (not cloud)
   - No session data sent to external servers
   - Regular backup recommended

### Recommended Practices

**DO:**
- Use delays between bulk actions
- Vary message content slightly
- Keep broadcast batches small (< 30)
- Backup sessions weekly
- Monitor for Telegram warnings

**DON'T:**
- Send identical messages to 100+ chats
- Use for adding users to groups
- Share session files
- Ignore FloodWait errors
- Automate friend requests

---

## Session Backup

### Manual Backup

```powershell
# Copy sessions folder
Copy-Item -Path "TelegramHub\accounts\sessions" -Destination "D:\Backup\TelegramHub_sessions_$(Get-Date -Format 'yyyyMMdd')" -Recurse
```

### Automated Daily Backup

Create `backup_sessions.ps1`:

```powershell
$source = "C:\Users\Admin\Documents\Cursor\Projects\TelegramHub\accounts\sessions"
$dest = "D:\Backup\TelegramHub"
$date = Get-Date -Format "yyyyMMdd"

# Create backup
Copy-Item -Path $source -Destination "$dest\sessions_$date" -Recurse -Force

# Keep only last 7 backups
Get-ChildItem $dest -Directory | Sort-Object CreationTime -Descending | Select-Object -Skip 7 | Remove-Item -Recurse -Force
```

Add to Task Scheduler to run daily.

---

## Data Security

### What We Store

| Data | Location | Encrypted |
|------|----------|-----------|
| Telegram sessions | /accounts/sessions/ | By Telegram |
| CRM data (tags, notes) | /data/crm_chats.json | No |
| Templates | /data/templates.json | No |
| Context exports | /context/ | No |

### Recommendations

1. **Encrypt sensitive folders** (Windows BitLocker or VeraCrypt)
2. **Don't share session files** — they grant full account access
3. **Use strong Windows password**
4. **Regular backups to external drive**

---

## Telegram API Limits

### Known Limits

| Action | Limit | Consequence |
|--------|-------|-------------|
| Messages per second | ~30 | FloodWait |
| Messages to new users | ~50/day | Temporary restriction |
| Join groups | ~20/day | Account warning |
| API requests | ~30/second | FloodWait |

### FloodWait Errors

When Telegram returns FloodWait:
1. System automatically pauses
2. Waits required time (usually 30s-5min)
3. Retries operation
4. Logs the event

---

## Emergency: Account Restricted

If your account gets restricted:

1. **Don't panic** — temporary restrictions are common
2. **Stop all automation** — disable TelegramHub
3. **Wait 24-48 hours**
4. **Check Telegram app** for warnings
5. **Gradually resume** — start with manual actions

### Permanent Ban Prevention

- Never use for spam
- Don't mass-add users to groups
- Keep human-like behavior patterns
- Respond to Telegram's verification requests
