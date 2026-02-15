"""
Language Tutor Bot v2 — AI-powered language practice (English, Japanese, Spanish).

Features:
  - Voice-only control (no text commands needed)
  - Main menu with language switcher (EN / JP / ES)
  - Intent detection (switch mode, language, plan — all by voice)
  - Tutor mode (detailed analysis) and Free Chat mode
  - Persistent user profiles with detailed progress tracking
  - Timed practice sessions with background timer
  - Adaptive learning plans
  - Text message analysis (writing practice)
  - Legacy /commands still work as fallback
"""
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
from dotenv import load_dotenv

from user_profile import UserProfile
from session_manager import session_manager
from intent_detector import (
    detect_intent, IntentResult,
    INTENT_SPEECH, INTENT_SWITCH_MODE, INTENT_SWITCH_LANG,
    INTENT_SWITCH_FORMAT, INTENT_SHOW_PLAN, INTENT_EDIT_PLAN,
    INTENT_START_SESSION, INTENT_END_SESSION, INTENT_SET_PROFILE,
    INTENT_SHOW_STATS, INTENT_SHOW_INSTRUCTIONS, INTENT_CLEAR_INSTRUCTIONS,
    INTENT_REQUEST_VOICE,
)
from prompts import (
    LANGUAGE_CONFIG, build_system_prompt,
    PLAN_GENERATOR_PROMPT, PROGRESS_REVIEW_PROMPT, SESSION_SUMMARY_PROMPT,
)

load_dotenv()

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-4o"           # Main tutor model
GPT_MINI = "gpt-4o-mini"       # For plan generation, reviews, summaries
TTS_MODEL = "tts-1-hd"

TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

# === INIT ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Main menu: language switcher (EN / JP / ES)
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="EN English"),
            KeyboardButton(text="JP Japanese"),
            KeyboardButton(text="ES Spanish"),
        ],
    ],
    resize_keyboard=True,
)

# Map menu button text -> lang code
LANG_BUTTON_TO_CODE = {
    "en english": "en",
    "english": "en",
    "jp japanese": "jp",
    "japanese": "jp",
    "es spanish": "es",
    "spanish": "es",
}

# User asked "send voice" -> next text message will be TTS and sent as voice
pending_voice_requests: dict = {}

# Accumulated corrections in free_chat mode (cleared when switching to tutor mode)
pending_corrections: dict = {}



# ======================================================================
# FORMATTING
# ======================================================================

def format_corrections_en(user_text: str, ai_response: dict) -> str:
    parts = []
    parts.append(f"**You said:**\n_{user_text}_\n")

    analysis = ai_response.get("analysis", {})
    if analysis.get("overall_quality"):
        parts.append(f"**Level:** {analysis['overall_quality']}\n")

    has_issues = False
    for key, label in [("grammar", "Grammar"), ("vocabulary", "Vocabulary"),
                       ("pronunciation_notes", "Pronunciation"), ("naturalness", "Naturalness")]:
        if analysis.get(key):
            parts.append(f"**{label}:**\n{analysis[key]}\n")
            has_issues = True

    if ai_response.get("corrections"):
        parts.append(f"**Corrections:**\n{ai_response['corrections']}\n")
    if ai_response.get("better_version"):
        parts.append(f"**Native version:**\n_{ai_response['better_version']}_\n")
    if not has_issues:
        parts.append("No mistakes found!\n")
    if ai_response.get("learning_tip"):
        parts.append(f"**Tip:** {ai_response['learning_tip']}\n")
    if ai_response.get("follow_up_question"):
        parts.append(f"**Let's continue:** {ai_response['follow_up_question']}")
    return "\n".join(parts)


def format_corrections_jp(user_text: str, ai_response: dict) -> str:
    parts = []
    parts.append(f"**Ты сказал(а):**\n_{user_text}_\n")

    if ai_response.get("response_romaji"):
        parts.append(f"**Ромадзи:** _{ai_response['response_romaji']}_")
    if ai_response.get("response_translation"):
        parts.append(f"**Перевод:** _{ai_response['response_translation']}_\n")

    analysis = ai_response.get("analysis", {})
    if analysis.get("overall_quality"):
        parts.append(f"**Уровень:** {analysis['overall_quality']}\n")

    has_issues = False
    for key, label in [("grammar", "Грамматика"), ("vocabulary", "Лексика"),
                       ("pronunciation_notes", "Произношение"), ("writing_notes", "Письмо"),
                       ("naturalness", "Естественность")]:
        if analysis.get(key):
            parts.append(f"**{label}:**\n{analysis[key]}\n")
            has_issues = True

    if ai_response.get("corrections"):
        parts.append(f"**Исправления:**\n{ai_response['corrections']}\n")
    if ai_response.get("better_version"):
        parts.append(f"**Носитель сказал бы:**\n_{ai_response['better_version']}_\n")
    if not has_issues:
        parts.append("Ошибок не найдено!\n")
    if ai_response.get("new_words"):
        parts.append(f"**Новые слова:**\n{ai_response['new_words']}\n")
    if ai_response.get("learning_tip"):
        parts.append(f"**Запомни:** {ai_response['learning_tip']}\n")
    if ai_response.get("follow_up_question"):
        parts.append(f"**Продолжим:** {ai_response['follow_up_question']}")
    return "\n".join(parts)


def format_corrections_es(user_text: str, ai_response: dict) -> str:
    """Spanish: Russian labels + optional response_translation (same style as JP)."""
    parts = []
    parts.append(f"**Ты сказал(а):**\n_{user_text}_\n")

    if ai_response.get("response_translation"):
        parts.append(f"**Перевод:** _{ai_response['response_translation']}_\n")

    analysis = ai_response.get("analysis", {})
    if analysis.get("overall_quality"):
        parts.append(f"**Уровень:** {analysis['overall_quality']}\n")

    has_issues = False
    for key, label in [("grammar", "Грамматика"), ("vocabulary", "Лексика"),
                       ("pronunciation_notes", "Произношение"),
                       ("naturalness", "Естественность")]:
        if analysis.get(key):
            parts.append(f"**{label}:**\n{analysis[key]}\n")
            has_issues = True

    if ai_response.get("corrections"):
        parts.append(f"**Исправления:**\n{ai_response['corrections']}\n")
    if ai_response.get("better_version"):
        parts.append(f"**Носитель сказал бы:**\n_{ai_response['better_version']}_\n")
    if not has_issues:
        parts.append("Ошибок не найдено!\n")
    if ai_response.get("learning_tip"):
        parts.append(f"**Запомни:** {ai_response['learning_tip']}\n")
    if ai_response.get("follow_up_question"):
        parts.append(f"**Продолжим:** {ai_response['follow_up_question']}")
    return "\n".join(parts)


def format_corrections(user_text: str, ai_response: dict, lang: str) -> str:
    if lang == "jp":
        return format_corrections_jp(user_text, ai_response)
    if lang == "es":
        return format_corrections_es(user_text, ai_response)
    return format_corrections_en(user_text, ai_response)


# ======================================================================
# CORE: transcribe, tutor response, TTS
# ======================================================================

async def transcribe_audio(file_path: Path, lang: str = "en") -> str:
    whisper_lang = LANGUAGE_CONFIG[lang]["whisper_lang"]
    with open(file_path, "rb") as f:
        transcript = openai_client.audio.transcriptions.create(
            model=WHISPER_MODEL, file=f, language=whisper_lang
        )
    return transcript.text


def _should_reply_voice(profile: UserProfile, ai_response: dict, user_sent_voice: bool) -> bool:
    """Decide whether to send reply as voice. Smart: uses AI hint when format is 'auto'."""
    fmt = profile.response_format
    if fmt == "text":
        return False
    if fmt == "voice":
        return True
    # "auto" or legacy: use model's reply_as_voice, default = mirror user's channel
    return ai_response.get("reply_as_voice", user_sent_voice)


async def get_tutor_response(
    user_message: str,
    profile: UserProfile,
    user_sent_voice: bool = True,
) -> dict:
    """Get AI tutor response with full student context."""
    lang = profile.lang
    mode = profile.session_mode

    system_prompt = build_system_prompt(profile, lang=lang, mode=mode, user_sent_voice=user_sent_voice)
    context_messages = profile.get_conversation_context()

    response = openai_client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            *context_messages,
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    ai_response = json.loads(response.choices[0].message.content)

    # Save to history
    profile.add_message(
        user_message=user_message,
        bot_response=ai_response.get("response", ""),
        corrections=ai_response.get("corrections", ""),
        lang=lang,
        mode=mode,
    )

    # Track detailed mistakes from analysis
    analysis = ai_response.get("analysis", {})
    specific_mistakes = analysis.get("specific_mistakes", [])
    if specific_mistakes:
        for m in specific_mistakes:
            profile.track_detailed_mistake(
                mistake_type=m.get("type", "unknown"),
                specific=m.get("specific", ""),
                example=m.get("example", ""),
            )
    else:
        # Fallback: legacy category tracking
        for key in ("grammar", "vocabulary", "pronunciation_notes", "naturalness", "writing_notes"):
            if analysis.get(key):
                profile.track_detailed_mistake(key.replace("_notes", ""), key)

    # Update skill scores if provided
    skill_scores = analysis.get("skill_scores", {})
    for skill_key, score in skill_scores.items():
        if isinstance(score, (int, float)):
            profile.update_skill(skill_key, float(score))

    # Save meta-instruction if GPT detected one (self-modifying behavior)
    meta = ai_response.get("meta_instruction")
    if meta and isinstance(meta, str) and len(meta) > 3:
        profile.add_instruction(meta, source="auto")

    # Check if review is needed
    if profile.needs_review():
        asyncio.create_task(_auto_review(profile))

    return ai_response


async def generate_voice(text: str, output_path: Path, lang: str = "en"):
    voice = LANGUAGE_CONFIG[lang]["tts_voice"]
    response = openai_client.audio.speech.create(
        model=TTS_MODEL, voice=voice, input=text
    )
    response.write_to_file(output_path)


# ======================================================================
# AUTO REVIEW (runs in background every N messages)
# ======================================================================

async def _auto_review(profile: UserProfile):
    """Generate a progress snapshot using GPT."""
    try:
        stats = profile.get_stats()
        mistakes = profile.get_top_mistakes(10)
        weak = profile.get_weak_skills()
        strong = profile.get_strong_skills()

        context = (
            f"Student level: {stats['level']}\n"
            f"Total messages: {stats['total_messages']}\n"
            f"Top mistakes: {json.dumps([m['specific'] for m in mistakes], ensure_ascii=False)}\n"
            f"Weak skills: {json.dumps([(k, v['score']) for k, v in weak], ensure_ascii=False)}\n"
            f"Strong skills: {json.dumps([(k, v['score']) for k, v in strong], ensure_ascii=False)}\n"
        )
        last_snap = profile.get_last_snapshot()
        if last_snap:
            context += f"Previous assessment ({last_snap['date']}): {last_snap['level_estimate']}\n"

        response = openai_client.chat.completions.create(
            model=GPT_MINI,
            messages=[
                {"role": "system", "content": PROGRESS_REVIEW_PROMPT},
                {"role": "user", "content": context},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        data = json.loads(response.choices[0].message.content)

        profile.add_progress_snapshot(
            level_estimate=data.get("level_estimate", stats["level"]),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            notes=data.get("notes", ""),
        )

        # Update skills from review
        for skill_key, score in data.get("skill_updates", {}).items():
            if isinstance(score, (int, float)):
                profile.update_skill(skill_key, float(score))

        # Save bot observations (self-written notes about the student)
        observations = data.get("observations", [])
        for obs in observations:
            if isinstance(obs, str) and len(obs) > 5:
                profile.add_observation(obs)

    except Exception as e:
        logger.exception(f"Auto review failed for user {profile.user_id}: {e}")
        # Don't crash the bot on review failure


# ======================================================================
# INTENT HANDLERS
# ======================================================================

async def handle_switch_mode(message: types.Message, profile: UserProfile, detail: str):
    new_mode = detail if detail in ("tutor", "free_chat") else (
        "free_chat" if profile.session_mode == "tutor" else "tutor"
    )
    profile.session_mode = new_mode

    # Clear accumulated corrections when switching to tutor mode
    if new_mode == "tutor":
        pending_corrections.pop(profile.user_id, None)

    if new_mode == "free_chat":
        text = ("Switched to free chat mode! "
                "I'll just talk naturally without corrections. "
                "Say 'back to learning' when you want feedback again.")
        if profile.lang in ("jp", "es"):
            text = ("Переключил на свободный чат! "
                    "Просто общаемся без разбора ошибок. "
                    "Скажи 'обратно к учебе' когда захочешь разбор.")
    else:
        text = ("Back to tutor mode! "
                "I'll analyze your speech and give detailed feedback.")
        if profile.lang in ("jp", "es"):
            text = ("Вернулись в режим учителя! "
                    "Буду анализировать речь и давать подробный разбор.")

    await message.answer(text)


def _next_lang(current: str) -> str:
    """Cycle: en -> jp -> es -> en."""
    if current == "en":
        return "jp"
    if current == "jp":
        return "es"
    return "en"


async def handle_switch_lang(message: types.Message, profile: UserProfile, detail: str):
    valid_langs = ("en", "jp", "es")
    new_lang = detail if detail in valid_langs else _next_lang(profile.lang)
    profile.lang = new_lang
    cfg = LANGUAGE_CONFIG[new_lang]

    if new_lang == "jp":
        await message.answer(
            f"{cfg['flag']} Переключено на японский!\n"
            "Отправляй голосовые на японском.\n"
            "Ромадзи и перевод в каждом ответе."
        )
    elif new_lang == "es":
        await message.answer(
            f"{cfg['flag']} Переключено на испанский!\n"
            "Отправляй голосовые на испанском.\n"
            "Разбор и перевод в каждом ответе."
        )
    else:
        await message.answer(
            f"{cfg['flag']} Switched to English!\n"
            "Send voice messages in English.\n"
            "I'll analyze and help you improve!"
        )


async def handle_start_session(message: types.Message, profile: UserProfile):
    topic = profile.get_todays_topic() or "General practice"

    await session_manager.start_session(
        user_id=profile.user_id,
        topic=topic,
        mode=profile.session_mode,
        lang=profile.lang,
    )

    if profile.lang in ("jp", "es"):
        await message.answer(
            f"Сессия начата!\n"
            f"Тема: {topic}\n"
            f"Режим: {'учитель' if profile.session_mode == 'tutor' else 'свободный чат'}\n\n"
            "Начинай говорить!"
        )
    else:
        await message.answer(
            f"Session started!\n"
            f"Topic: {topic}\n"
            f"Mode: {profile.session_mode}\n\n"
            "Start speaking!"
        )


async def handle_end_session(message: types.Message, profile: UserProfile):
    # Clear accumulated corrections on session end
    pending_corrections.pop(profile.user_id, None)

    record = await session_manager.end_session(profile.user_id, reason="user_request")
    if record:
        if profile.lang in ("jp", "es"):
            await message.answer(
                f"Сессия завершена!\n"
                f"Продолжительность: {record['duration_actual_seconds'] // 60} мин\n"
                f"Сообщений: {record['messages_count']}\n\n"
                "Отличная практика!"
            )
        else:
            await message.answer(
                f"Session complete!\n"
                f"Duration: {record['duration_actual_seconds'] // 60} min\n"
                f"Messages: {record['messages_count']}\n\n"
                "Great practice!"
            )
    else:
        text = "No active session." if profile.lang == "en" else "Нет активной сессии."  # jp, es -> RU
        await message.answer(text)


async def handle_show_plan(message: types.Message, profile: UserProfile):
    plan = profile._lang_data().get("learning_plan", {})
    stats = profile.get_stats()

    parts = []
    if profile.lang in ("jp", "es"):
        parts.append(f"Уровень: {stats['level']}")
        parts.append(f"Сообщений: {stats['total_messages']} | Серия: {stats['streak_days']} дн.")
        if plan.get("global_goal"):
            parts.append(f"\nЦель: {plan['global_goal']}")
        if plan.get("current_focus"):
            parts.append(f"Фокус: {plan['current_focus']}")
        weekly = plan.get("weekly_plan")
        if weekly and isinstance(weekly, dict):
            parts.append(f"\nНеделя: {weekly.get('week_goal', '')}")
            schedule = weekly.get("schedule", {})
            for day, info in schedule.items():
                status = "done" if info.get("completed") else "pending"
                parts.append(f"  {day}: {info.get('topic', '?')} [{status}]")
        mistakes = profile.get_top_mistakes(3)
        if mistakes:
            parts.append("\nОсновные ошибки:")
            for m in mistakes:
                parts.append(f"  - {m['specific']} ({m['times_seen']}x)")
    else:
        parts.append(f"Level: {stats['level']}")
        parts.append(f"Messages: {stats['total_messages']} | Streak: {stats['streak_days']} days")
        if plan.get("global_goal"):
            parts.append(f"\nGoal: {plan['global_goal']}")
        if plan.get("current_focus"):
            parts.append(f"Focus: {plan['current_focus']}")
        weekly = plan.get("weekly_plan")
        if weekly and isinstance(weekly, dict):
            parts.append(f"\nWeek: {weekly.get('week_goal', '')}")
            schedule = weekly.get("schedule", {})
            for day, info in schedule.items():
                status = "done" if info.get("completed") else "pending"
                parts.append(f"  {day}: {info.get('topic', '?')} [{status}]")
        mistakes = profile.get_top_mistakes(3)
        if mistakes:
            parts.append("\nTop mistakes:")
            for m in mistakes:
                parts.append(f"  - {m['specific']} ({m['times_seen']}x)")

    await message.answer("\n".join(parts) if parts else "No plan yet. Tell me your goals!")


async def handle_edit_plan(message: types.Message, profile: UserProfile, detail: str):
    """Generate or update the weekly plan based on user request."""
    stats = profile.get_stats()
    mistakes = profile.get_top_mistakes(5)
    weak = profile.get_weak_skills()

    context = (
        f"Student request: {detail}\n"
        f"Current level: {stats['level']}\n"
        f"Language: {profile.lang}\n"
        f"Top mistakes: {json.dumps([m['specific'] for m in mistakes], ensure_ascii=False)}\n"
        f"Weak skills: {json.dumps([(k, v['score']) for k, v in weak], ensure_ascii=False)}\n"
    )
    current_plan = profile._lang_data().get("learning_plan", {})
    if current_plan.get("global_goal"):
        context += f"Current goal: {current_plan['global_goal']}\n"

    try:
        response = openai_client.chat.completions.create(
            model=GPT_MINI,
            messages=[
                {"role": "system", "content": PLAN_GENERATOR_PROMPT},
                {"role": "user", "content": context},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        plan_data = json.loads(response.choices[0].message.content)

        profile.update_plan(
            weekly_plan={
                "week_start": datetime.now().strftime("%Y-%m-%d"),
                "week_goal": plan_data.get("week_goal", ""),
                "format": plan_data.get("format", "mixed"),
                "session_duration_minutes": plan_data.get("session_duration_minutes", 5),
                "schedule": plan_data.get("schedule", {}),
            },
            ai_recommendations=plan_data.get("recommendations", []),
        )

        # Update default session duration
        dur = plan_data.get("session_duration_minutes", 5)
        profile.data["settings"]["default_session_minutes"] = dur
        profile.save()

        if profile.lang in ("jp", "es"):
            await message.answer(
                f"План обновлен!\n"
                f"Цель: {plan_data.get('week_goal', '')}\n"
                f"Формат: {dur}-мин сессии\n\n"
                "Скажи 'давай позанимаемся' чтобы начать!"
            )
        else:
            await message.answer(
                f"Plan updated!\n"
                f"Goal: {plan_data.get('week_goal', '')}\n"
                f"Format: {dur}-min sessions\n\n"
                "Say 'let's practice' to start!"
            )

    except Exception as e:
        await message.answer(f"Could not generate plan: {str(e)[:200]}")


async def handle_set_profile(message: types.Message, profile: UserProfile, detail: str):
    # Simple: extract name if present
    lower = detail.lower()
    for prefix in ("my name is ", "call me ", "i'm ", "i am ",
                    "menya zovut ", "ya "):
        if lower.startswith(prefix):
            name = detail[len(prefix):].strip().title()
            profile.display_name = name
            await message.answer(f"Got it, {name}!")
            return
    profile.display_name = detail.strip().title()
    await message.answer(f"Profile updated: {detail}")


async def handle_switch_format(message: types.Message, profile: UserProfile, detail: str):
    valid = ("text", "voice", "auto")
    new_format = detail if detail in valid else (
        "text" if profile.response_format == "voice" else
        "voice" if profile.response_format == "text" else "auto"
    )
    profile.response_format = new_format

    if new_format == "text":
        text = ("Switched to text only. I'll reply with text."
                if profile.lang == "en" else
                "Только текст. Буду отвечать текстом.")
    elif new_format == "voice":
        text = ("Switched to voice only. I'll send voice replies."
                if profile.lang == "en" else
                "Только голос. Отвечаю голосовыми.")
    else:
        text = ("Smart mode: I'll choose voice or text depending on the reply (default)."
                if profile.lang == "en" else
                "Умный режим: сам выбираю голос или текст в зависимости от ответа.")
    await message.answer(text)


async def handle_show_instructions(message: types.Message, profile: UserProfile):
    instructions = profile.get_instructions()
    observations = profile.get_observations()

    parts = []
    if profile.lang == "en":
        parts.append("--- Your Instructions ---")  # jp, es -> Russian block below
        if instructions:
            for i, inst in enumerate(instructions):
                parts.append(f"{i+1}. {inst['text']}  ({inst['added']})")
        else:
            parts.append("(none)")
        parts.append("\n--- Bot Observations ---")
        if observations:
            for obs in observations:
                parts.append(f"- {obs['text']}  ({obs['added']})")
        else:
            parts.append("(none)")
        parts.append("\nSay 'forget everything' to clear all.")
    else:
        parts.append("--- Ваши инструкции ---")
        if instructions:
            for i, inst in enumerate(instructions):
                parts.append(f"{i+1}. {inst['text']}  ({inst['added']})")
        else:
            parts.append("(пусто)")
        parts.append("\n--- Наблюдения бота ---")
        if observations:
            for obs in observations:
                parts.append(f"- {obs['text']}  ({obs['added']})")
        else:
            parts.append("(пусто)")
        parts.append("\nСкажи 'забудь все' чтобы очистить.")

    await message.answer("\n".join(parts))


async def handle_clear_instructions(message: types.Message, profile: UserProfile):
    profile.clear_instructions()
    text = ("All instructions and observations cleared!"
            if profile.lang == "en" else
            "Все инструкции и наблюдения очищены!")
    await message.answer(text)


async def handle_request_voice(message: types.Message, profile: UserProfile, detail: str):
    """User asked to record/send a voice message. If detail has text — TTS it; else ask for text and set pending."""
    lang = profile.lang
    text_to_speak = (detail or "").strip()
    if text_to_speak:
        temp_output = TEMP_DIR / f"voice_req_{message.message_id}.mp3"
        try:
            await generate_voice(text_to_speak, temp_output, lang=lang)
            await message.answer_voice(voice=types.FSInputFile(temp_output))
        finally:
            if temp_output.exists():
                temp_output.unlink()
        return
    pending_voice_requests[profile.user_id] = True
    if lang == "en":
        reply = "What text should I say? Send it and I'll reply with a voice message."
    elif lang in ("jp", "es"):
        reply = "Напиши текст — я озвучу и отправлю голосовым сообщением."
    else:
        reply = "What text should I say? Send it and I'll reply with a voice message."
    await message.answer(reply)


# ======================================================================
# TELEGRAM HANDLERS
# ======================================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    profile = UserProfile(message.from_user.id)
    # Set display name from Telegram
    if not profile.display_name and message.from_user.first_name:
        profile.display_name = message.from_user.first_name

    lang = profile.lang
    cfg = LANGUAGE_CONFIG[lang]

    await message.answer(
        f"Hi{', ' + profile.display_name if profile.display_name else ''}! "
        f"I'm your language tutor.\n\n"
        f"Current: {cfg['flag']} {cfg['name']} | Mode: {profile.session_mode}\n\n"
        f"Just send a voice message to start practicing!\n"
        f"Use the buttons below to switch language (EN / JP / ES), or say:\n"
        f"  - 'Switch to English/Japanese/Spanish'\n"
        f"  - 'Let's just chat' / 'Back to learning'\n"
        f"  - 'Let's practice' (start timed session)\n"
        f"  - 'Show my plan' / 'Show progress'\n\n"
        f"Or use: /lang /stats /plan /session",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


@dp.message(Command("lang"))
async def cmd_lang(message: types.Message):
    profile = UserProfile(message.from_user.id)
    new_lang = _next_lang(profile.lang)
    await handle_switch_lang(message, profile, new_lang)


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    profile = UserProfile(message.from_user.id)
    await handle_show_plan(message, profile)


@dp.message(Command("plan"))
async def cmd_plan(message: types.Message):
    profile = UserProfile(message.from_user.id)
    await handle_show_plan(message, profile)


@dp.message(Command("session"))
async def cmd_session(message: types.Message):
    profile = UserProfile(message.from_user.id)
    if session_manager.has_active_session(profile.user_id):
        await handle_end_session(message, profile)
    else:
        await handle_start_session(message, profile)


@dp.message(Command("mode"))
async def cmd_mode(message: types.Message):
    profile = UserProfile(message.from_user.id)
    new_mode = "free_chat" if profile.session_mode == "tutor" else "tutor"
    await handle_switch_mode(message, profile, new_mode)


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    profile = UserProfile(message.from_user.id)
    profile.clear_conversation_history()
    await message.answer("Conversation history cleared for this language. Stats and plan preserved.")


@dp.message(Command("instructions"))
async def cmd_instructions(message: types.Message):
    profile = UserProfile(message.from_user.id)
    await handle_show_instructions(message, profile)


@dp.message(Command("textmode"))
async def cmd_textmode(message: types.Message):
    profile = UserProfile(message.from_user.id)
    await handle_switch_format(message, profile, "text")


@dp.message(Command("voicemode"))
async def cmd_voicemode(message: types.Message):
    profile = UserProfile(message.from_user.id)
    await handle_switch_format(message, profile, "voice")


# ======================================================================
# VOICE HANDLER (main pipeline)
# ======================================================================

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    profile = UserProfile(message.from_user.id)
    lang = profile.lang

    # Set name on first interaction
    if not profile.display_name and message.from_user.first_name:
        profile.display_name = message.from_user.first_name

    status_msg = await message.answer(
        "Listening..." if lang == "en" else "Слушаю..."
    )

    temp_input = TEMP_DIR / f"in_{message.message_id}.ogg"
    temp_output = TEMP_DIR / f"out_{message.message_id}.mp3"

    try:
        # 1. Download
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, temp_input)

        # 2. Transcribe
        await status_msg.edit_text(
            "Transcribing..." if lang == "en" else "Распознаю..."
        )
        user_text = await transcribe_audio(temp_input, lang=lang)

        # 3. Detect intent — but only for SHORT messages when NO session is active.
        #    During an active session, everything is speech unless it's a
        #    very short explicit stop command.
        has_session = session_manager.has_active_session(profile.user_id)
        word_count = len(user_text.split())

        # During active session: only detect "end_session" from short messages
        # Outside session: detect all intents, but only from short messages (<15 words)
        run_full_intent = (not has_session) and (word_count < 15)
        run_stop_only = has_session and (word_count <= 5)

        intent = None
        if run_full_intent:
            intent = detect_intent(openai_client, user_text)
        elif run_stop_only:
            # Quick local check for stop words only
            lower = user_text.lower().strip()
            stop_words = ("stop", "enough", "end", "finish", "done",
                          "стоп", "хватит", "закончим", "достаточно")
            for sw in stop_words:
                if sw in lower:
                    intent = IntentResult(INTENT_END_SESSION)
                    break

        # 4. Route by intent (only if detected)
        if intent and intent.intent != INTENT_SPEECH:
            if intent.intent == INTENT_SWITCH_MODE:
                await status_msg.delete()
                await handle_switch_mode(message, profile, intent.detail)
                return

            if intent.intent == INTENT_SWITCH_LANG:
                await status_msg.delete()
                await handle_switch_lang(message, profile, intent.detail)
                return

            if intent.intent in (INTENT_SHOW_PLAN, INTENT_SHOW_STATS):
                await status_msg.delete()
                await handle_show_plan(message, profile)
                return

            if intent.intent == INTENT_EDIT_PLAN:
                await status_msg.edit_text(
                    "Updating plan..." if lang == "en" else "Обновляю план..."
                )
                await handle_edit_plan(message, profile, intent.detail)
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                return

            if intent.intent == INTENT_START_SESSION:
                await status_msg.delete()
                await handle_start_session(message, profile)
                return

            if intent.intent == INTENT_END_SESSION:
                await status_msg.delete()
                await handle_end_session(message, profile)
                return

            if intent.intent == INTENT_SET_PROFILE:
                await status_msg.delete()
                await handle_set_profile(message, profile, intent.detail)
                return

            if intent.intent == INTENT_SWITCH_FORMAT:
                await status_msg.delete()
                await handle_switch_format(message, profile, intent.detail)
                return

            if intent.intent == INTENT_SHOW_INSTRUCTIONS:
                await status_msg.delete()
                await handle_show_instructions(message, profile)
                return

            if intent.intent == INTENT_CLEAR_INSTRUCTIONS:
                await status_msg.delete()
                await handle_clear_instructions(message, profile)
                return

            if intent.intent == INTENT_REQUEST_VOICE:
                await status_msg.delete()
                await handle_request_voice(message, profile, intent.detail)
                return

        # 5. Normal speech — get tutor response
        await status_msg.edit_text(
            "Analyzing..." if lang == "en" else "Анализирую..."
        )

        # Track session activity
        session_manager.on_message(profile.user_id)
        ai_response = await get_tutor_response(
            user_message=user_text,
            profile=profile,
        )

        response_text = ai_response.get("response", "")

        # 6. Send response: voice or text (smart: AI can choose via reply_as_voice when format is "auto")
        use_voice = _should_reply_voice(profile, ai_response, user_sent_voice=True)
        if use_voice:
            await status_msg.edit_text(
                "Speaking..." if lang == "en" else "Озвучиваю..."
            )
            await generate_voice(response_text, temp_output, lang=lang)
            await status_msg.delete()
            await message.answer_voice(voice=types.FSInputFile(temp_output))
        else:
            await status_msg.delete()
            await message.answer(response_text)

        # 7. Send corrections / extras
        if profile.session_mode == "tutor":
            corrections_text = format_corrections(user_text, ai_response, lang=lang)
            try:
                await message.answer(corrections_text, parse_mode="Markdown")
            except Exception:
                await message.answer(corrections_text)
        else:
            # Free chat: show translation for JP (romaji+translation) or ES (translation only)
            if lang == "jp":
                romaji = ai_response.get("response_romaji", "")
                translation = ai_response.get("response_translation", "")
                if romaji or translation:
                    extra = ""
                    if romaji:
                        extra += f"Romaji: {romaji}\n"
                    if translation:
                        extra += f"Translation: {translation}"
                    await message.answer(extra)
            elif lang == "es":
                translation = ai_response.get("response_translation", "")
                if translation:
                    await message.answer(f"Перевод: {translation}")

    except Exception as e:
        error_text = (f"Error: {str(e)[:300]}\nTry again!"
                      if lang == "en"
                      else f"Ошибка: {str(e)[:300]}\nПопробуй ещё раз!")
        try:
            await status_msg.edit_text(error_text)
        except Exception:
            pass

    finally:
        for f in (temp_input, temp_output):
            if f.exists():
                f.unlink()


# ======================================================================
# TEXT HANDLER (writing practice)
# ======================================================================

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    """Process text messages: menu buttons, then writing practice or commands."""
    profile = UserProfile(message.from_user.id)
    lang = profile.lang
    user_text = message.text.strip()

    # Main menu: language switcher buttons
    key = user_text.lower()
    if key in LANG_BUTTON_TO_CODE:
        new_lang = LANG_BUTTON_TO_CODE[key]
        if new_lang != profile.lang:
            await handle_switch_lang(message, profile, new_lang)
        else:
            cfg = LANGUAGE_CONFIG[profile.lang]
            await message.answer(f"{cfg['flag']} Already: {cfg['name']}")
        return

    # Pending voice: user asked "record voice", now sent text -> TTS and send voice
    uid = message.from_user.id
    if uid in pending_voice_requests:
        text_to_speak = user_text
        if text_to_speak:
            temp_output = TEMP_DIR / f"voice_req_{message.message_id}.mp3"
            try:
                await generate_voice(text_to_speak, temp_output, lang=lang)
                await message.answer_voice(voice=types.FSInputFile(temp_output))
            finally:
                if temp_output.exists():
                    temp_output.unlink()
        else:
            await message.answer(
                "Send me the text you want me to say as a voice message." if lang == "en"
                else "Напиши текст, который озвучить."
            )
        pending_voice_requests.pop(uid, None)
        return

    # Intent detection: only for short messages (<15 words) when no session active
    has_session = session_manager.has_active_session(profile.user_id)
    word_count = len(user_text.split())
    intent = None

    if (not has_session) and word_count < 15:
        intent = detect_intent(openai_client, user_text)
    elif has_session and word_count <= 5:
        lower = user_text.lower()
        stop_words = ("stop", "enough", "end", "done",
                      "стоп", "хватит", "закончим")
        for sw in stop_words:
            if sw in lower:
                intent = IntentResult(INTENT_END_SESSION)
                break

    if intent and intent.intent != INTENT_SPEECH:
        if intent.intent == INTENT_SWITCH_MODE:
            await handle_switch_mode(message, profile, intent.detail)
            return
        if intent.intent == INTENT_SWITCH_LANG:
            await handle_switch_lang(message, profile, intent.detail)
            return
        if intent.intent in (INTENT_SHOW_PLAN, INTENT_SHOW_STATS):
            await handle_show_plan(message, profile)
            return
        if intent.intent == INTENT_EDIT_PLAN:
            await handle_edit_plan(message, profile, intent.detail)
            return
        if intent.intent == INTENT_START_SESSION:
            await handle_start_session(message, profile)
            return
        if intent.intent == INTENT_END_SESSION:
            await handle_end_session(message, profile)
            return
        if intent.intent == INTENT_SET_PROFILE:
            await handle_set_profile(message, profile, intent.detail)
            return
        if intent.intent == INTENT_SWITCH_FORMAT:
            await handle_switch_format(message, profile, intent.detail)
            return
        if intent.intent == INTENT_SHOW_INSTRUCTIONS:
            await handle_show_instructions(message, profile)
            return
        if intent.intent == INTENT_CLEAR_INSTRUCTIONS:
            await handle_clear_instructions(message, profile)
            return
        if intent.intent == INTENT_REQUEST_VOICE:
            await handle_request_voice(message, profile, intent.detail)
            return

    # Normal text: treat as writing practice
    status_msg = await message.answer(
        "Analyzing your writing..." if lang == "en" else "Анализирую текст..."
    )

    try:
        session_manager.on_message(profile.user_id)

        ai_response = await get_tutor_response(
            user_message=user_text,
            profile=profile,
            user_sent_voice=False,
        )

        await status_msg.delete()

        # Reply: smart format (AI can choose voice even for text input when format is "auto")
        reply = ai_response.get("response", "")
        use_voice = _should_reply_voice(profile, ai_response, user_sent_voice=False)
        if use_voice and reply:
            temp_output = TEMP_DIR / f"out_txt_{message.message_id}.mp3"
            try:
                await generate_voice(reply, temp_output, lang=lang)
                await message.answer_voice(voice=types.FSInputFile(temp_output))
            finally:
                if temp_output.exists():
                    temp_output.unlink()
        else:
            await message.answer(reply)

        if profile.session_mode == "tutor":
            corrections_text = format_corrections(user_text, ai_response, lang=lang)
            try:
                await message.answer(corrections_text, parse_mode="Markdown")
            except Exception:
                await message.answer(corrections_text)

    except Exception as e:
        error_text = f"Error: {str(e)[:300]}"
        try:
            await status_msg.edit_text(error_text)
        except Exception:
            pass


# ======================================================================
# MAIN
# ======================================================================

async def main():
    print("=" * 50)
    print("Language Tutor Bot v2")
    print("EN + JP + ES | Voice Control | Main Menu | Sessions | Plans")
    print("=" * 50)
    print(f"GPT: {GPT_MODEL} | Mini: {GPT_MINI}")
    print(f"Whisper: {WHISPER_MODEL} | TTS: {TTS_MODEL}")
    print("=" * 50)
    print("Running... Ctrl+C to stop")
    print("=" * 50)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
