"""
Autonomous test: simulate a conversation with the bot in Japanese.
Calls the tutor logic directly (no Telegram, no voice) to test JP pipeline.
"""
import asyncio
import os
import sys
from pathlib import Path

# === WINDOWS UNICODE FIX ===
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
# === END UNICODE FIX ===

# Run from project root so imports and .env work
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(Path(__file__).resolve().parent)

from dotenv import load_dotenv
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("No OPENAI_API_KEY in .env - skip live API test")
    sys.exit(0)

# Import after chdir
from bot import get_tutor_response, format_corrections_message

TEST_USER_ID = 999999  # fake user for test
JP_PHRASES = [
    "kinou eiga wo mimashita. totemo omoshirokatta desu.",
    "nihongo wo benkyou shiteimasu. mada heta desu.",
    "ashita tomodachi to resutoran ni ikimasu.",
]


async def run_conversation():
    print("=" * 60)
    print("JAPANESE TUTOR - SIMULATED CONVERSATION TEST")
    print("=" * 60)

    for i, phrase in enumerate(JP_PHRASES, 1):
        print(f"\n--- Turn {i} ---")
        print(f"[User (simulated)]: {phrase}")

        try:
            ai_response = await get_tutor_response(phrase, TEST_USER_ID, lang="jp")
        except Exception as e:
            print(f"[Error] {e}")
            continue

        reply = ai_response.get("response", "")
        romaji = ai_response.get("response_romaji", "")
        translation = ai_response.get("response_translation", "")

        print(f"[Bot (Japanese)]: {reply}")
        if romaji:
            print(f"[Romaji]: {romaji}")
        if translation:
            print(f"[Translation]: {translation}")

        # Short analysis
        analysis = ai_response.get("analysis", {})
        if analysis.get("overall_quality"):
            print(f"[Level]: {analysis['overall_quality']}")
        if analysis.get("learning_tip"):
            print(f"[Tip]: {analysis['learning_tip'][:150]}...")
        if ai_response.get("follow_up_question"):
            print(f"[Next question]: {ai_response['follow_up_question'][:100]}...")

        # Full formatted block (as user would see in Telegram)
        formatted = format_corrections_message(phrase, ai_response, lang="jp")
        print("\n[Full feedback block (excerpt)]:")
        print(formatted[:600] + "..." if len(formatted) > 600 else formatted)

    print("\n" + "=" * 60)
    print("CONVERSATION TEST DONE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_conversation())
