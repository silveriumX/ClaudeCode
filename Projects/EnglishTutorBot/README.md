# 🎓 Personal English Tutor Bot

> Your AI English tutor focused on quality learning, not monetization

---

## 🎯 Goal

**Help you genuinely improve your English** through high-quality conversation practice with detailed, expert-level feedback.

---

## ✨ What makes this tutor special

### 1. **Expert-level Analysis**
- ✅ **GPT-5.2** (latest, Dec 2025) - best available model
- ✅ **Multi-dimensional feedback**: grammar, vocabulary, pronunciation, naturalness
- ✅ **Explains WHY**, not just WHAT is wrong
- ✅ **Native speaker alternatives** - learn how real English speakers talk

### 2. **Remembers Your Progress**
- ✅ **Conversation history** - maintains context (last 5 messages)
- ✅ **Tracks your mistakes** - identifies patterns in your errors
- ✅ **Personalized feedback** - focuses on YOUR weak areas
- ✅ **Progress statistics** - see how you're improving

### 3. **High-Quality Voice**
- ✅ **TTS-HD** - crystal clear pronunciation examples
- ✅ **Natural voice** (nova) - sounds like a real person
- ✅ **Perfect for pronunciation practice**

---

## 🆕 New Features (v2.5 - Feb 2026)

### **1. Intelligent Conversationalist** 🧠
- **Long, engaging responses** (2-4 paragraphs) - not just short replies!
- **Real-time web search** - bot automatically searches for current information when needed
- **Deep topic discussions** - anime, programming, business, investments, and more
- **Your interests remembered** - bot learns what you like to talk about

### **2. Natural Learning Flow** 🌊
- **Corrections accumulate** in free_chat mode - no interruptions during conversation
- **Request feedback** anytime with `/feedback` or "give me feedback"
- **Increased context** - bot remembers last 20 messages (was 7) for deeper conversations
- **Smart format** - bot decides when to respond with voice vs text

### **3. How It Works Now:**

**Free Chat Mode (NEW!):**
```
You: "What's the latest news about AI in 2026?"
Bot: [Searches web automatically]
Bot: [2-3 paragraphs about AI trends, citing sources]
     + Engaging follow-up questions
     + Natural conversation flow
     [Mistakes tracked silently in background]

You: "Give me feedback"
Bot: [Shows all accumulated corrections from your last 10 messages]
```

**Tutor Mode (Classic):**
- Detailed analysis after each message
- Immediate corrections and explanations
- Perfect for focused learning sessions

---

## 🚀 Quick Start

### 1. Create your bot
```
1. Open @BotFather in Telegram
2. Send /newbot
3. Name it (e.g., "My English Tutor")
4. Copy the token
```

### 2. Install dependencies
```powershell
cd Projects\EnglishTutorBot
pip install -r requirements.txt
```

### 3. Set your bot token
```powershell
# Option 1: Environment variable
$env:TELEGRAM_TOKEN="your_token_here"
python bot.py

# Option 2: Edit bot.py line 12
TELEGRAM_TOKEN = "your_token_here"
python bot.py
```

---

## 💬 Example Conversation

**You (voice):** "Yesterday I go to cinema with my friend and we watch very interesting movie about AI"

**Bot (voice):** "Oh, AI movies are fascinating! What did you think about how they portrayed AI?"

**Bot (text):**
```
🗣 You said:
"Yesterday I go to cinema with my friend and we watch very interesting movie about AI"

🌿 Level: intermediate

📚 Grammar:
Past tense error: 'go' should be 'went', 'watch' should be 'watched'

📖 Vocabulary:
'very interesting' is correct but basic - natives often use stronger adjectives 
like 'fascinating', 'compelling', 'thought-provoking'

💬 Naturalness:
Missing articles. Natives say 'went to the cinema' (or 'went to the movies' in US)

✏️ Corrections:
• 'Yesterday I **went** to **the** cinema' (past tense + article)
• 'and we **watched** a very interesting movie' (past tense + article)

⭐ Native would say:
"Yesterday I went to the cinema with my friend and we watched a really fascinating movie about AI"

💡 Remember:
Common mistake for Russian speakers: forgetting articles (a/the). 
English needs them before singular countable nouns!

❓ Let's continue:
What did you think about how they portrayed AI?
```

---

## 📊 Commands

**Essential:**
- `/start` - Welcome message and language selection
- `/feedback` - Show accumulated corrections (in free_chat mode)
- `/stats` - View your progress and common mistakes
- `/reset` - Clear conversation history (keeps statistics)

**Modes:**
- `/lang` - Switch language (EN/JP/ES)
- `/mode` - Toggle between tutor ↔ free_chat
- Voice commands work too: "switch to free chat", "back to learning"

**Sessions:**
- `/session` - Start/end timed practice session
- `/plan` - View your learning plan
- `/topic` - Get conversation topic suggestion based on your interests

---

## 📈 Track Your Progress

### Use `/stats` to see:
- Total messages sent
- Most common mistake types
- Areas to focus on
- Progress motivation

**Example:**
```
📊 Your Progress

📝 Total messages: 47

⚠️ Areas to improve:
• Grammar: 15x (32%)
• Naturalness: 12x (26%)
• Vocabulary: 8x (17%)

💡 I'll focus on these areas in our conversations

🎯 Member since: 2026-02-11

💪 Good progress! Practice makes perfect!
```

---

## 🎯 How to Get Maximum Benefit

### 1. **Practice Daily**
- Even 5-10 minutes a day is better than 1 hour once a week
- Consistency builds habits and muscle memory

### 2. **Review Feedback Carefully**
- Don't just read corrections - understand WHY
- Try to use corrected phrases in your next message
- The bot remembers your mistakes and will help you fix them

### 3. **Use `/topic` When Stuck**
- Don't know what to say? Get a topic suggestion
- Forces you to construct longer, more complex responses

### 4. **Challenge Yourself**
- Try using new vocabulary you learned
- Experiment with complex grammar structures
- Talk about topics outside your comfort zone

### 5. **Check `/stats` Weekly**
- See which areas need more work
- Celebrate your progress
- Adjust your focus based on patterns

---

## ⚙️ Customization

### Choose Model (in bot.py line 21):

**Важно:** Я не знаю какие модели доступны в 2026. Проверь актуальные на:
👉 https://platform.openai.com/docs/models

```python
# Используй последнюю доступную модель:
GPT_MODEL = "gpt-5.3"  # если доступна в 2026
# или
GPT_MODEL = "o3"  # reasoning модель
# или
GPT_MODEL = "gpt-4o"  # если новых нет
```

**См. [HOW_TO_CHOOSE_MODEL.md](./HOW_TO_CHOOSE_MODEL.md) - как проверить актуальные модели.**

### Change Voice (in bot.py):
```python
TTS_VOICE = "nova"     # Female, energetic (current)
# TTS_VOICE = "alloy"  # Neutral
# TTS_VOICE = "echo"   # Male
# TTS_VOICE = "fable"  # British accent
# TTS_VOICE = "onyx"   # Deep male
# TTS_VOICE = "shimmer" # Soft female
```

---

## 💰 API Costs (for personal use)

**Per conversation (voice message + response):**
- Whisper (transcription): ~$0.006
- **GPT-5.2** (analysis): ~$0.08-0.12 ← **Current (latest model)**
- **o3** reasoning (max quality): ~$0.15-0.25 (slower, most detailed)
- **gpt-4o** (budget): ~$0.05-0.08 (previous generation)
- TTS-HD (voice response): ~$0.02
- **Total with GPT-5.2:** ~$0.10-0.15

**Monthly estimate (GPT-5.2):**
- 10 messages/day: ~$30-45/month
- 20 messages/day: ~$60-90/month
- 30 messages/day: ~$90-135/month

**Worth it?** If you'd pay $50-100/month for a human tutor (1-2 hours), this gives you unlimited practice.

**Want cheaper?** Use `gpt-4o` (~$45/month for 30/day). See [MODELS_GUIDE.md](./MODELS_GUIDE.md).

---

## 🔧 Technical Details

### Technologies:
- **Python 3.10+**
- **aiogram 3.13** - Telegram Bot
- **OpenAI API:**
  - Whisper - Speech recognition
  - GPT-4o - Language analysis
  - TTS-HD - Voice generation

### Files:
- `bot.py` - Main bot code
- `user_profile.py` - Progress tracking
- `requirements.txt` - Dependencies

### Data Storage:
- `user_data/` - Your conversation history and statistics (JSON files)
- `temp_audio/` - Temporary audio files (auto-deleted)

---

## 🐛 Troubleshooting

### Bot doesn't respond
1. Check bot is running (`python bot.py`)
2. Verify bot token is correct
3. Check internet connection

### "Invalid token"
- Token is wrong - get a new one from @BotFather
- Check for extra spaces/characters

### Voice quality issues
- Upgrade to TTS-HD: `TTS_MODEL = "tts-1-hd"` (already set)
- Try different voices (see Customization section)

### OpenAI errors
- Check balance at platform.openai.com
- Verify API key is valid (already in code from VoiceBot)

---

## 📚 Learning Resources

Want to go deeper? Combine this bot with:

- **Reading:** News articles, books
- **Listening:** Podcasts, YouTube
- **Writing:** Journal in English
- **Speaking:** This bot + language exchange partners

**This bot is your 24/7 speaking partner who never judges and always helps.**

---

## 🎓 Philosophy

This bot is designed for **serious learners** who want:
- ✅ Honest, detailed feedback
- ✅ Real improvement, not just encouragement
- ✅ Understanding of patterns in mistakes
- ✅ Quality over quantity

**Not just a chatbot - a genuine learning tool.**

---

**Ready to improve your English? Start now! 🚀**

```powershell
python bot.py
```
