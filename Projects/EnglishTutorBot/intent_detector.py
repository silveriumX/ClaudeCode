"""
Intent Detector — classifies transcribed voice messages into intents.

Uses a lightweight GPT model (gpt-4o-mini) for fast, cheap classification.
Cost: ~$0.0001 per call.
"""
import json
from typing import Optional
from openai import OpenAI

from prompts import INTENT_SYSTEM_PROMPT

# Intent constants
INTENT_SPEECH = "speech"
INTENT_SWITCH_MODE = "switch_mode"
INTENT_SWITCH_LANG = "switch_lang"
INTENT_SWITCH_FORMAT = "switch_format"
INTENT_SHOW_PLAN = "show_plan"
INTENT_EDIT_PLAN = "edit_plan"
INTENT_START_SESSION = "start_session"
INTENT_END_SESSION = "end_session"
INTENT_SET_PROFILE = "set_profile"
INTENT_SHOW_STATS = "show_stats"
INTENT_SHOW_INSTRUCTIONS = "show_instructions"
INTENT_CLEAR_INSTRUCTIONS = "clear_instructions"
INTENT_REQUEST_VOICE = "request_voice"

# Cheap fast model for intent detection
INTENT_MODEL = "gpt-4o-mini"


class IntentResult:
    """Parsed intent result."""
    def __init__(self, intent: str, detail: str = ""):
        self.intent = intent
        self.detail = detail

    def __repr__(self):
        return f"IntentResult(intent={self.intent!r}, detail={self.detail!r})"


def detect_intent(client: OpenAI, text: str) -> IntentResult:
    """Classify transcribed text into an intent.

    Args:
        client: OpenAI client instance
        text: Transcribed voice message text

    Returns:
        IntentResult with intent type and optional detail
    """
    # Short-circuit: very short messages are almost always speech
    if len(text.split()) <= 2:
        # But check for known short commands
        lower = text.lower().strip()
        quick_map = {
            "stop": IntentResult(INTENT_END_SESSION),
            "enough": IntentResult(INTENT_END_SESSION),
            "end": IntentResult(INTENT_END_SESSION),
            "start": IntentResult(INTENT_START_SESSION),
        }
        for keyword, result in quick_map.items():
            if keyword in lower:
                return result

    try:
        response = client.chat.completions.create(
            model=INTENT_MODEL,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=100,
        )

        data = json.loads(response.choices[0].message.content)
        intent = data.get("intent", INTENT_SPEECH)
        detail = data.get("detail", "")

        # Validate intent
        valid_intents = {
            INTENT_SPEECH, INTENT_SWITCH_MODE, INTENT_SWITCH_LANG,
            INTENT_SWITCH_FORMAT, INTENT_SHOW_PLAN, INTENT_EDIT_PLAN,
            INTENT_START_SESSION, INTENT_END_SESSION, INTENT_SET_PROFILE,
            INTENT_SHOW_STATS, INTENT_SHOW_INSTRUCTIONS, INTENT_CLEAR_INSTRUCTIONS,
            INTENT_REQUEST_VOICE,
        }
        if intent not in valid_intents:
            intent = INTENT_SPEECH

        return IntentResult(intent=intent, detail=detail)

    except Exception:
        # On any error, default to speech — don't block the conversation
        return IntentResult(intent=INTENT_SPEECH)
