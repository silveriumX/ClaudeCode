#!/usr/bin/env python3
"""
Отправить тестовое уведомление об оплате заявки REQ-20260217-115245-06E64C65
к owner и инициатору (Трофимовой).

Запуск: python3 send_test_notification.py
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.sheets import SheetsManager
from src.utils.formatters import format_amount, get_currency_symbols_dict

REQUEST_ID = "REQ-20260217-115245-06E64C65"
RECEIPT_URL = "https://drive.google.com/file/d/1BfvEO3j_7uhw4tf5A9ymlyYHRymKus9A/view?usp=drivesdk"
EXECUTOR_NAME = "Асель"
DEAL_ID = "#bde787aa"


async def main():
    from telegram import Bot

    print("Connecting to Google Sheets...")
    sheets = SheetsManager()

    print(f"Looking up request {REQUEST_ID}...")
    request = sheets.get_request_by_request_id(REQUEST_ID)

    if not request:
        print(f"WARNING: Request {REQUEST_ID} not found. Using hardcoded values.")
        request = {
            "date": "17.02.2026",
            "amount": 10000,
            "currency": "RUB",
            "recipient": "Леонид Медведев",
            "author_id": "",
        }
    else:
        print(f"Found: date={request.get('date')}, amount={request.get('amount')}, "
              f"recipient={request.get('recipient')}, author_id={request.get('author_id', '(пусто)')}")

    date = request.get("date", "17.02.2026")
    amount = float(request.get("amount", 10000))
    currency = request.get("currency", config.CURRENCY_RUB)
    recipient = request.get("recipient", "Леонид Медведев")
    author_id = str(request.get("author_id", "")).strip()

    currency_symbols = get_currency_symbols_dict()
    currency_symbol = currency_symbols.get(currency, "")
    amount_str = format_amount(amount, currency)

    # HTML format — безопасен с URL содержащими _ (Markdown v1 ломается)
    owner_text = (
        f"<b>Заявка оплачена</b>\n\n"
        f"Дата: {date}\n"
        f"Сумма: {amount_str} {currency_symbol}\n"
        f"Получатель: {recipient}\n"
        f"Исполнитель: {EXECUTOR_NAME}\n"
        f"ID сделки: {DEAL_ID}\n"
        f'\n<a href="{RECEIPT_URL}">Открыть чек</a>'
    )

    initiator_text = (
        f"<b>Заявка оплачена</b>\n\n"
        f"Дата: {date}\n"
        f"Сумма: {amount_str} {currency_symbol}\n"
        f"Получатель: {recipient}\n"
        f'\n<a href="{RECEIPT_URL}">Открыть чек</a>'
    )

    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)

    # Отправить owner-ам
    owners = sheets.get_users_by_role(config.ROLE_OWNER)
    print(f"\nFound {len(owners)} owner(s)")
    for owner in owners:
        tg_id = owner.get("telegram_id", "")
        name = owner.get("name", "?")
        if tg_id:
            try:
                await bot.send_message(
                    chat_id=int(float(tg_id)),
                    text=owner_text,
                    parse_mode="HTML",
                )
                print(f"  OK owner: {name} ({tg_id})")
            except Exception as e:
                print(f"  FAIL owner: {name} ({tg_id}): {e}")

    # Отправить инициатору
    if author_id:
        print(f"\nSending to initiator (author_id={author_id})...")
        try:
            await bot.send_message(
                chat_id=int(float(author_id)),
                text=initiator_text,
                parse_mode="HTML",
            )
            print(f"  OK initiator {author_id}")
        except Exception as e:
            print(f"  FAIL initiator {author_id}: {e}")
    else:
        print(
            f"\nWARNING: author_id не найден для {REQUEST_ID}.\n"
            "Проверь колонку 'author_id' (или аналог) в листе 'Основные'."
        )

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
