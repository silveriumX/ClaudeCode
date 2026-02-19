---
description: Telegram Conflict error — "terminated by other getUpdates request". Caused by two bot instances running simultaneously (polling mode). Fix: deleteWebhook + wait 25-30 seconds + kill old process + restart. Critical for VPS deployment.
---

# Conflict Error

```
telegram.error.Conflict: Terminated by other getUpdates request;
make sure that only one bot instance is running
```

This error means two processes are calling `getUpdates` simultaneously. Telegram allows only one polling connection per token.

## When It Happens

1. **Redeployment without stopping the old process** — `nohup python bot.py &` a second time while the first is still running
2. **Webhook not cleared before switching to polling** — if the bot was deployed with webhooks, `getUpdates` will fail until the webhook is removed
3. **Process survives restart** — the old process is still alive because `pkill -f bot.py` didn't reach it

## The Fix Sequence

```bash
# 1. Delete any active webhook (clears Telegram-side block)
curl "https://api.telegram.org/bot{TOKEN}/deleteWebhook"

# 2. Wait — Telegram needs time to release the connection
sleep 30

# 3. Kill all bot processes
pkill -f "python bot.py"
# or more specific:
pkill -f "FinanceBot/bot.py"

# 4. Verify no process remains
ps aux | grep bot.py

# 5. Start fresh
nohup python bot.py > bot.log 2>&1 &
```

## Why 25-30 Seconds

Telegram holds the long-polling connection open for ~20-25 seconds. If you restart before the connection times out, the new instance will get the Conflict error immediately. The 25-30s wait lets the old connection expire on Telegram's side.

## Python Equivalent

```python
import asyncio
from telegram import Bot

async def clear_webhook(token: str):
    bot = Bot(token=token)
    result = await bot.delete_webhook(drop_pending_updates=True)
    print(f"Webhook deleted: {result}")
    await asyncio.sleep(30)

asyncio.run(clear_webhook(BOT_TOKEN))
```

## In Deployment Scripts

When deploying via paramiko/SSH, the sequence must be:

```python
# paramiko deployment pattern
ssh.exec_command("pkill -f 'python bot.py' || true")
time.sleep(2)

# Delete webhook via API before starting
ssh.exec_command(f"curl -s 'https://api.telegram.org/bot{token}/deleteWebhook'")
time.sleep(30)

# Start new instance
ssh.exec_command("cd /opt/bot && nohup python bot.py > bot.log 2>&1 &")
```

## Detecting Which Process is Running

```bash
# Find the process
ps aux | grep bot.py | grep -v grep

# See what port/log it's writing to
lsof -p {PID}

# Kill by PID if pkill isn't working
kill -9 {PID}
```

## Related

- Deploy skills: `/deploy-linux-vps` and `/telegram-bot-linux` cover the full deployment flow including this fix
- For multi-instance deployment (intentional), use webhook mode instead of polling — each server gets its own webhook endpoint
