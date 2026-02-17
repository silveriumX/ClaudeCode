# ChatManager - Quick Start After Deployment

## Status

✅ **Control Bot:** RUNNING
⚠️ **UserBot:** Requires manual authorization (one-time setup)

## What Works Now

- ✅ Control Bot is live and responding to `/start` in Telegram
- ✅ Google Sheets integration is active
- ✅ All files deployed to VPS
- ✅ Systemd services configured with auto-restart

## What Needs Action

### Authorize UserBot (Required)

**Option 1: On VPS (Recommended)**

```bash
ssh root@195.177.94.189
cd /root/ChatManager
bash authorize_userbot_vps.sh
```

Follow prompts:
1. Enter phone number (e.g., +79123456789)
2. Enter code from Telegram
3. Enter 2FA password (if enabled)

Script will:
- Stop the service
- Run authorization
- Restart the service
- Show status

**Option 2: Local + Upload**

```powershell
# On local machine
cd C:\Users\Admin\Documents\Cursor\Projects\ChatManager
python setup_userbot.py

# Then upload session
# (Use SCP or the deploy script)
```

## Quick Commands

### Check Status
```bash
ssh root@195.177.94.189 "systemctl status chatmanager-bot chatmanager-userbot"
```

### View Logs
```bash
ssh root@195.177.94.189 "journalctl -u chatmanager-bot -n 20"
ssh root@195.177.94.189 "journalctl -u chatmanager-userbot -n 20"
```

### Restart Services
```bash
ssh root@195.177.94.189 "systemctl restart chatmanager-bot"
ssh root@195.177.94.189 "systemctl restart chatmanager-userbot"
```

## Files on VPS

All files are in `/root/ChatManager/`:
- `bot.py` - Control Bot
- `userbot.py` - UserBot
- `config.py` - Configuration
- `sheets.py` - Google Sheets API
- `.env` - Environment variables
- `service_account.json` - Google credentials
- `handlers/` - Telegram handlers
- `utils/` - Helper utilities

## Health Check

Run locally:
```powershell
cd C:\Users\Admin\Documents\Cursor\Projects\ChatManager
python check_deployment.py
```

Shows:
- Service statuses
- Recent logs
- File structure
- Environment check

## Full Documentation

See `DEPLOYMENT_REPORT.md` for complete details.

## Troubleshooting

### Control Bot not responding
```bash
ssh root@195.177.94.189 "journalctl -u chatmanager-bot -n 50"
```

### UserBot crashing
Check authorization status:
```bash
ssh root@195.177.94.189 "ls -lh /root/ChatManager/chat_admin.session"
```

### Google Sheets errors
```bash
ssh root@195.177.94.189 "cd /root/ChatManager && python3 -c 'from sheets import SheetsManager; s = SheetsManager(); print(\"OK\")'"
```

---

**Next Step:** Authorize UserBot using Option 1 above
