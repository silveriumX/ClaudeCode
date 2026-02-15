# ⚡ Quick Start - 5 Minutes to Your English Tutor

## Prerequisites
- Python 3.10+ installed
- OpenAI API key (already in code from VoiceBot)
- Internet connection

---

## Step 1: Create Bot (2 min)

1. Open [@BotFather](https://t.me/BotFather)
2. Send: `/newbot`
3. Name: `My English Tutor`
4. Username: `my_english_tutor_bot`
5. **Copy token** → `123456:ABC-DEF...`

---

## Step 2: Setup (2 min)

```powershell
# Navigate to project
cd Projects\EnglishTutorBot

# Install dependencies
pip install -r requirements.txt

# Set bot token
$env:TELEGRAM_TOKEN="YOUR_TOKEN_HERE"
```

---

## Step 3: Run (1 min)

```powershell
python bot.py
```

**Expected output:**
```
==================================================
🤖 English Tutor Bot Started!
==================================================
📁 Temp files: ...\temp_audio
🤖 GPT Model: gpt-4o
🎤 Whisper Model: whisper-1
🔊 TTS Voice: nova
==================================================
✅ Bot is running... Press Ctrl+C to stop
==================================================
```

---

## Step 4: Test

1. Open your bot in Telegram
2. Press **Start**
3. Send a voice message in English (any topic)
4. Receive voice reply + detailed feedback!

---

## Example First Message

Record and send:
> "Hi! I want to improve my English. Can you help me?"

**You'll get:**
- 🎙 Voice response from the bot
- 📝 Analysis of your grammar/vocabulary
- 💡 Learning tips
- ❓ Follow-up question to continue

---

## Commands to Try

After your first message, try:

```
/topic  - Get a conversation topic
/stats  - View your progress
/reset  - Clear conversation history
```

---

## Troubleshooting

### Bot doesn't start
```powershell
# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### "Invalid token" error
- Get new token from @BotFather
- Make sure no spaces before/after token
- Use quotes: `$env:TELEGRAM_TOKEN="token"`

### Bot doesn't respond in Telegram
- Check `python bot.py` is running
- Look for errors in console
- Test with simple text: just send "test"

---

## Pro Tips

### Make token permanent:
```powershell
# Edit bot.py line 12:
TELEGRAM_TOKEN = "your_token_here"  # Replace this

# Then just run:
python bot.py
```

### Run in background:
```powershell
# Windows: use pythonw
pythonw bot.py

# Or use PowerShell job
Start-Job -ScriptBlock { python bot.py }
```

---

## What's Next?

1. **Practice daily** - send 5-10 voice messages
2. **Check `/stats`** after a week
3. **Use `/topic`** when you don't know what to say
4. **Read feedback carefully** - it's personalized!

---

## File Structure

```
EnglishTutorBot/
├── bot.py              ← Run this
├── user_profile.py     ← Progress tracking (auto-used)
├── requirements.txt    ← Dependencies
└── README.md           ← Full docs
```

---

## API Costs (FYI)

Each conversation: ~$0.06-0.08
- 10/day = ~$20/month
- 20/day = ~$40/month

Much cheaper than human tutor!

---

**Ready in 5 minutes. Start improving your English now! 🚀**
