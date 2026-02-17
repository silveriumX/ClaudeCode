"""
Вспомогательный скрипт для первичной настройки UserBot
Помогает авторизоваться и создать session файл
"""
import asyncio
from pyrogram import Client
import config

async def setup_userbot():
    """Настройка и авторизация UserBot"""
    print("[SETUP] ChatManager UserBot Setup")
    print(f"[INFO] API ID: {config.USERBOT_API_ID}")
    print(f"[INFO] Session: {config.USERBOT_SESSION}")
    print()

    print("[INFO] Starting authorization...")
    print("[INFO] You will be asked for:")
    print("  1. Phone number (with country code, e.g., +1234567890)")
    print("  2. Confirmation code from Telegram")
    print("  3. 2FA password (if enabled)")
    print()

    app = Client(
        config.USERBOT_SESSION,
        api_id=config.USERBOT_API_ID,
        api_hash=config.USERBOT_API_HASH
    )

    async with app:
        me = await app.get_me()
        print()
        print("[SUCCESS] Authorization successful!")
        print(f"[INFO] Logged in as: {me.first_name}")
        print(f"[INFO] Username: @{me.username}")
        print(f"[INFO] ID: {me.id}")
        print()
        print(f"[INFO] Session file created: {config.USERBOT_SESSION}.session")
        print("[INFO] You can now run: python userbot.py")

if __name__ == '__main__':
    asyncio.run(setup_userbot())
