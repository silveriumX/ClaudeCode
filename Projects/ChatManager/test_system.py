"""
Тестовый скрипт для проверки работы системы
Проверяет подключение к Google Sheets и базовые операции
"""
import sys
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_google_sheets():
    """Тест подключения к Google Sheets"""
    logger.info("Testing Google Sheets connection...")

    try:
        from sheets import ChatSheetsManager
        sheets = ChatSheetsManager()
        logger.info("[OK] Google Sheets connection established")

        # Проверяем листы
        logger.info("Checking sheets...")
        logger.info(f"[OK] Users sheet: {sheets.users_sheet.title}")
        logger.info(f"[OK] Chats sheet: {sheets.chats_sheet.title}")
        logger.info(f"[OK] Participants sheet: {sheets.participants_sheet.title}")

        return True
    except Exception as e:
        logger.error(f"[ERROR] Google Sheets connection failed: {e}")
        return False

def test_config():
    """Тест конфигурации"""
    logger.info("Testing configuration...")

    try:
        import config

        # Проверяем обязательные параметры
        required = [
            ('TELEGRAM_BOT_TOKEN', config.TELEGRAM_BOT_TOKEN),
            ('USERBOT_API_ID', config.USERBOT_API_ID),
            ('USERBOT_API_HASH', config.USERBOT_API_HASH),
            ('GOOGLE_SHEETS_ID', config.GOOGLE_SHEETS_ID)
        ]

        all_ok = True
        for name, value in required:
            if not value or value == f'your_{name.lower()}_here':
                logger.error(f"[ERROR] {name} not configured in .env")
                all_ok = False
            else:
                logger.info(f"[OK] {name} is set")

        return all_ok
    except Exception as e:
        logger.error(f"[ERROR] Configuration test failed: {e}")
        return False

def main():
    """Главная функция тестирования"""
    logger.info("=== ChatManager System Test ===")
    logger.info("")

    # Тест 1: Конфигурация
    logger.info("Test 1: Configuration")
    config_ok = test_config()
    logger.info("")

    if not config_ok:
        logger.error("[FAILED] Configuration test failed. Check your .env file.")
        sys.exit(1)

    # Тест 2: Google Sheets
    logger.info("Test 2: Google Sheets Connection")
    sheets_ok = test_google_sheets()
    logger.info("")

    if not sheets_ok:
        logger.error("[FAILED] Google Sheets test failed. Check service_account.json and sheet structure.")
        sys.exit(1)

    # Все тесты пройдены
    logger.info("=== ALL TESTS PASSED ===")
    logger.info("")
    logger.info("System is ready to run!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Start Control Bot: python bot.py")
    logger.info("2. Start UserBot: python userbot.py")
    logger.info("3. Open bot in Telegram and send /start")

if __name__ == '__main__':
    main()
