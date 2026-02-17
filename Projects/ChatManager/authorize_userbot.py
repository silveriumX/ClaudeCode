#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UserBot Authorization Script для запуска на VPS
Авторизует UserBot через Telegram API
"""
import sys
from pyrogram import Client
from config import USERBOT_API_ID, USERBOT_API_HASH, USERBOT_SESSION_NAME

def main():
    print("=== UserBot Telegram Authorization ===")
    print("")
    print("This script will authorize the UserBot with your Telegram account.")
    print("You will need to enter:")
    print("  1. Your phone number (with country code, e.g., +79001234567)")
    print("  2. Verification code from Telegram")
    print("")

    try:
        # Создаём клиента
        app = Client(
            name=USERBOT_SESSION_NAME,
            api_id=USERBOT_API_ID,
            api_hash=USERBOT_API_HASH,
            workdir="."
        )

        # Запускаем авторизацию (интерактивный режим)
        with app:
            me = app.get_me()
            print("")
            print(f"[OK] Authorization successful!")
            print(f"Authorized as: {me.first_name} (@{me.username})")
            print(f"User ID: {me.id}")
            print("")
            print(f"Session file created: {USERBOT_SESSION_NAME}.session")
            print("")
            print("Now you can start the UserBot service:")
            print("  systemctl restart chatmanager-userbot")
            print("  systemctl status chatmanager-userbot")

    except Exception as e:
        print(f"[ERROR] Authorization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
