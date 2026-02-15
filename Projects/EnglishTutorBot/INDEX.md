# EnglishTutorBot — Personal English Tutor

> Expert-level AI tutor for serious English learning (personal use, not monetization)

---

## 📁 Project Files

```
EnglishTutorBot/
├── bot.py                          # Main bot (GPT-5.2 + TTS-HD + history)
├── user_profile.py                 # Progress tracking (integrated)
├── test_openai.py                  # API test
├── requirements.txt                # Dependencies
├── .env.example                    # Config template
├── .gitignore                      # Git settings
│
├── START_HERE.md                   # ← Begin here!
├── README.md                       # Full documentation
├── QUICKSTART.md                   # 5-minute setup
├── ROADMAP.md                      # Future improvements
├── MODELS_GUIDE.md                 # Model comparison (o1 vs gpt-4o vs mini)
│
├── 📦 DEPLOYMENT FILES (VPS)
├── DEPLOY_WINDOWS_COMPLETE.ps1     # ⭐ Interactive deployment script
├── QUICKSTART_DEPLOY.md            # ⚡ 5-minute deploy guide
├── DEPLOYMENT_REPORT.md            # 📋 Full deployment documentation
├── deploy_commands.ps1             # Manual copy-paste commands
├── deploy_auto.py                  # Automated SSH deployment
├── deploy.py                       # Deployment manager
└── INDEX.md                        # This file
```

---

## 🎯 What Makes This Special

### Quality-First Approach:
- ✅ **GPT-5.2** (latest Dec 2025) - best available
- ✅ **TTS-HD** - crystal clear voice
- ✅ **Multi-dimensional analysis** - grammar, vocab, pronunciation, naturalness
- ✅ **Explains WHY** - not just what's wrong
- ✅ **Native alternatives** - how real speakers say it

### Personalized Learning:
- ✅ **Conversation history** - maintains context
- ✅ **Mistake tracking** - identifies your patterns
- ✅ **Adaptive feedback** - focuses on YOUR weak areas
- ✅ **Progress stats** - see improvement over time

---

## 🚀 Quick Start

1. **Read:** [START_HERE.md](./START_HERE.md) - full overview
2. **Setup:** [QUICKSTART.md](./QUICKSTART.md) - 5-minute installation
3. **Run:** `python bot.py`
4. **Practice!** 🎙

---

## 💬 How It Works

**You send:** 🎙 Voice message in English

**Bot returns:**
1. 🎙 Voice response (continues conversation)
2. 📊 Detailed analysis:
   - Grammar check
   - Vocabulary suggestions
   - Pronunciation notes
   - Naturalness feedback
3. ⭐ Native alternative (how to say it better)
4. 💡 Learning tip
5. ❓ Follow-up question

---

## 📊 Features

### Core:
- **Voice conversation** - natural dialogue
- **Expert analysis** - GPT-4o quality
- **HD voice** - clear pronunciation
- **Conversation memory** - tracks context

### Progress Tracking:
- `/stats` - view your progress
- `/topic` - get conversation ideas
- `/reset` - clear history

### Smart Features:
- Remembers your mistakes
- Focuses on your weak areas
- Adapts to your level
- Provides context-aware feedback

---

## 💰 Cost (Personal Use)

**Per conversation:** ~$0.10-0.15 (using GPT-5.2)

**Monthly estimates:**
- 10 messages/day: ~$30-45/month
- 20 messages/day: ~$60-90/month
- 30 messages/day: ~$90-135/month

**Compare to human tutor:** $50-100/month for 1-2 hours vs unlimited practice.

---

## 🎓 Learning Philosophy

**This bot is for serious learners who want:**
- Honest, expert-level feedback
- Real improvement, not just encouragement
- Understanding of their mistake patterns
- Quality analysis over quick responses

**Not just a chatbot - a genuine learning tool.**

---

## 🔧 Configuration

### Bot Token:
- Get from @BotFather
- Set via `$env:TELEGRAM_TOKEN="..."`
- Or edit `bot.py` line 16

### OpenAI API:
- Already configured (from VoiceBot)
- Uses GPT-5.2 (latest, best quality)
- TTS-HD enabled

### Voice:
- Current: `nova` (female, energetic)
- Options: alloy, echo, fable, onyx, shimmer
- Change in `bot.py` line 18

---

## 📦 VPS Deployment

### Quick Deploy to Windows Server:

**Target:** 195.177.94.53 (Windows Server)

**Method 1: Interactive Script (Recommended)**
1. Connect via RDP to 195.177.94.53
2. Copy `DEPLOY_WINDOWS_COMPLETE.ps1` to server
3. Run in PowerShell as Administrator
4. Follow prompts (5-10 minutes)

**Method 2: Manual Commands**
1. Connect via RDP
2. Copy all commands from `deploy_commands.ps1`
3. Paste into PowerShell

**Documentation:**
- [QUICKSTART_DEPLOY.md](./QUICKSTART_DEPLOY.md) - Quick guide
- [DEPLOYMENT_REPORT.md](./DEPLOYMENT_REPORT.md) - Full docs

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| [START_HERE.md](./START_HERE.md) | Complete overview |
| [README.md](./README.md) | Full documentation |
| [QUICKSTART.md](./QUICKSTART.md) | 5-minute local setup |
| [ROADMAP.md](./ROADMAP.md) | Future improvements |
| [MODELS_GUIDE.md](./MODELS_GUIDE.md) | Model comparison (o1/gpt-4o/mini) |
| [QUICKSTART_DEPLOY.md](./QUICKSTART_DEPLOY.md) | ⚡ VPS deployment guide |
| [DEPLOYMENT_REPORT.md](./DEPLOYMENT_REPORT.md) | 📋 Full deployment docs |

---

## 🎯 Tips for Success

1. **Practice daily** - consistency matters
2. **Read feedback carefully** - understand WHY
3. **Apply corrections** - use them in next message
4. **Check `/stats`** weekly - track patterns
5. **Use `/topic`** when stuck

---

## 🔗 Related Projects

- **VoiceBot** - source of OpenAI token
- **FinanceBot** - example of VPS deployment
- **TelegramHub** - universal bot architecture

---

## 📊 Current Status

- **Version:** 2.0 (Personal Learning Edition)
- **Focus:** Quality over features
- **Status:** Production ready
- **Purpose:** Serious English improvement

---

## 🚀 Next Steps

1. Read [START_HERE.md](./START_HERE.md)
2. Follow [QUICKSTART.md](./QUICKSTART.md)
3. Start practicing!
4. Check [ROADMAP.md](./ROADMAP.md) for ideas

---

**Created:** 11.02.2026  
**Purpose:** Personal English learning  
**Quality:** Expert-level with GPT-5.2 (latest model)  
**Cost:** ~$30-135/month depending on usage
