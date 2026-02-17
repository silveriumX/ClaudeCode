"""
Скрипт для автоматического создания Google Sheets таблицы ChatManager
Создаёт таблицу в указанной папке с правильной структурой листов
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
SERVICE_ACCOUNT_FILE = 'service_account.json'
FOLDER_ID = '1H2rIofCknpGXHo-px0zw-PJsdhPvnUdv'
SPREADSHEET_NAME = 'ChatManager Database'

def create_spreadsheet():
    """Создать таблицу с правильной структурой"""

    logger.info("=== Creating ChatManager Google Sheets ===")

    # Подключение к Google Sheets
    logger.info("[1/5] Connecting to Google Sheets API...")
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)

    logger.info("[OK] Connected")

    # Создать новую таблицу
    logger.info(f"[2/5] Creating spreadsheet '{SPREADSHEET_NAME}'...")
    spreadsheet = client.create(SPREADSHEET_NAME)
    spreadsheet_id = spreadsheet.id
    logger.info(f"[OK] Created: {spreadsheet_id}")

    # Переместить в папку
    logger.info(f"[3/5] Moving to folder {FOLDER_ID}...")
    try:
        file = drive_service.files().get(fileId=spreadsheet_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents', []))

        drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=FOLDER_ID,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        logger.info("[OK] Moved to folder")
    except Exception as e:
        logger.warning(f"[WARNING] Could not move to folder: {e}")
        logger.warning("Continuing anyway - you can move manually if needed")

    # Настроить листы
    logger.info("[4/5] Setting up sheets structure...")

    # Получить первый лист (по умолчанию "Sheet1")
    worksheet1 = spreadsheet.get_worksheet(0)

    # Переименовать в "Пользователи"
    worksheet1.update_title("Пользователи")

    # Заголовки для листа Пользователи
    headers_users = ['telegram_id', 'имя', 'username', 'роль', 'статус']
    worksheet1.append_row(headers_users)
    logger.info("[OK] Sheet 'Пользователи' created")

    # Создать лист "Чаты"
    worksheet2 = spreadsheet.add_worksheet(title="Чаты", rows=100, cols=8)
    headers_chats = ['id', 'название', 'creator_id', 'дата_создания', 'статус', 'invite_link', 'chat_id', 'описание']
    worksheet2.append_row(headers_chats)
    logger.info("[OK] Sheet 'Чаты' created")

    # Создать лист "Участники"
    worksheet3 = spreadsheet.add_worksheet(title="Участники", rows=100, cols=4)
    headers_participants = ['chat_id', 'user_id', 'роль_в_чате', 'дата_добавления']
    worksheet3.append_row(headers_participants)
    logger.info("[OK] Sheet 'Участники' created")

    # Готово
    logger.info("[5/5] Finalizing...")

    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    logger.info("\n=== SUCCESS ===")
    logger.info(f"Spreadsheet created: {SPREADSHEET_NAME}")
    logger.info(f"Spreadsheet ID: {spreadsheet_id}")
    logger.info(f"URL: {spreadsheet_url}")
    logger.info(f"\nFolder: https://drive.google.com/drive/folders/{FOLDER_ID}")

    # Обновить .env файл
    logger.info("\n[NEXT STEP] Updating .env file...")

    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Заменить GOOGLE_SHEETS_ID
        if 'GOOGLE_SHEETS_ID=YOUR_SHEETS_ID_AFTER_CREATION' in env_content:
            env_content = env_content.replace(
                'GOOGLE_SHEETS_ID=YOUR_SHEETS_ID_AFTER_CREATION',
                f'GOOGLE_SHEETS_ID={spreadsheet_id}'
            )
        elif 'GOOGLE_SHEETS_ID=' in env_content:
            import re
            env_content = re.sub(
                r'GOOGLE_SHEETS_ID=.*',
                f'GOOGLE_SHEETS_ID={spreadsheet_id}',
                env_content
            )

        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)

        logger.info("[OK] .env file updated with GOOGLE_SHEETS_ID")
    except Exception as e:
        logger.error(f"[ERROR] Could not update .env: {e}")
        logger.info(f"Please manually add to .env: GOOGLE_SHEETS_ID={spreadsheet_id}")

    logger.info("\n=== WHAT'S NEXT ===")
    logger.info("1. Add yourself to 'Пользователи' sheet:")
    logger.info(f"   - Open: {spreadsheet_url}")
    logger.info("   - Add row: your_telegram_id | Your Name | username | admin | active")
    logger.info("   - Get your ID from @userinfobot")
    logger.info("")
    logger.info("2. Get UserBot credentials: https://my.telegram.org/apps")
    logger.info("   - Update .env with USERBOT_API_ID and USERBOT_API_HASH")
    logger.info("")
    logger.info("3. Run: python test_system.py")
    logger.info("4. Run: python setup_userbot.py")
    logger.info("5. Run: python deploy_to_vps.py")

    return spreadsheet_id, spreadsheet_url

if __name__ == '__main__':
    try:
        spreadsheet_id, url = create_spreadsheet()
        print(f"\n✅ SPREADSHEET CREATED SUCCESSFULLY!")
        print(f"ID: {spreadsheet_id}")
        print(f"URL: {url}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nMake sure:")
        print("1. service_account.json exists in current directory")
        print("2. Service account has access to the folder")
        print("3. Required libraries installed: pip install gspread oauth2client google-api-python-client")
