#!/usr/bin/env python3
"""Test authorize handler locally"""
import asyncio
from pyrogram import Client
from config import USERBOT_API_ID, USERBOT_API_HASH, USERBOT_SESSION

async def test_authorize():
    print("Testing UserBot authorization...")

    # Simulate phone number input
    phone = "+79001234567"  # Example

    try:
        app = Client(
            name=USERBOT_SESSION,
            api_id=USERBOT_API_ID,
            api_hash=USERBOT_API_HASH,
            workdir="."
        )

        await app.connect()
        print(f"[OK] Connected to Telegram")

        # Try to send code
        sent_code = await app.send_code(phone)
        print(f"[OK] Code sent! Phone code hash: {sent_code.phone_code_hash[:20]}...")
        print(f"[INFO] Check 'Saved Messages' in Telegram for the code")

        await app.disconnect()

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_authorize())
