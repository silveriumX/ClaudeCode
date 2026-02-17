"""
Настройка структуры существующей таблицы
Создает нужные листы и заголовки
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys

SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_ID = '1aRJrrxdK0J1nuRnRE795T2Se_s0NpeNKRSREf0PbevU'

print("=" * 70)
print("SETTING UP CHATMANAGER SPREADSHEET STRUCTURE")
print("=" * 70)
print()

# Подключение
print("[1/4] Connecting...")
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
print(f"[OK] Connected to: {spreadsheet.title}")
print()

# Переименовать первый лист
print("[2/4] Renaming first sheet to 'Пользователи'...")
worksheet1 = spreadsheet.get_worksheet(0)
worksheet1.update_title("Пользователи")
headers_users = ['telegram_id', 'имя', 'username', 'роль', 'статус']
worksheet1.update('A1:E1', [headers_users])
print("[OK] Sheet 'Пользователи' created")
print(f"     Headers: {headers_users}")
print()

# Создать лист "Чаты"
print("[3/4] Creating sheet 'Чаты'...")
try:
    worksheet2 = spreadsheet.add_worksheet(title="Чаты", rows=100, cols=8)
except gspread.exceptions.APIError as e:
    if 'already exists' in str(e):
        worksheet2 = spreadsheet.worksheet("Чаты")
        print("[INFO] Sheet already exists, using existing")
    else:
        raise

headers_chats = ['id', 'название', 'creator_id', 'дата_создания', 'статус', 'invite_link', 'chat_id', 'описание']
worksheet2.update('A1:H1', [headers_chats])
print("[OK] Sheet 'Чаты' created")
print(f"     Headers: {headers_chats}")
print()

# Создать лист "Участники"
print("[4/4] Creating sheet 'Участники'...")
try:
    worksheet3 = spreadsheet.add_worksheet(title="Участники", rows=100, cols=4)
except gspread.exceptions.APIError as e:
    if 'already exists' in str(e):
        worksheet3 = spreadsheet.worksheet("Участники")
        print("[INFO] Sheet already exists, using existing")
    else:
        raise

headers_participants = ['chat_id', 'user_id', 'роль_в_чате', 'дата_добавления']
worksheet3.update('A1:D1', [headers_participants])
print("[OK] Sheet 'Участники' created")
print(f"     Headers: {headers_participants}")
print()

print("=" * 70)
print("SUCCESS! SPREADSHEET READY")
print("=" * 70)
print()
print(f"Spreadsheet: {spreadsheet.title}")
print(f"URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
print()
print("Sheets created:")
print("  1. Пользователи (5 columns)")
print("  2. Чаты (8 columns)")
print("  3. Участники (4 columns)")
print()
print("NEXT STEPS:")
print()
print("1. Add yourself to 'Пользователи' sheet:")
print("   - Get your Telegram ID from @userinfobot")
print("   - Add row: your_id | Your Name | username | admin | active")
print()
print("2. Run system test:")
print("   python test_system.py")
print()
print("3. Setup UserBot:")
print("   - Get credentials from https://my.telegram.org/apps")
print("   - Update .env with USERBOT_API_ID and USERBOT_API_HASH")
print("   - Run: python setup_userbot.py")
print()
print("4. Deploy to VPS:")
print("   python deploy_to_vps.py")
