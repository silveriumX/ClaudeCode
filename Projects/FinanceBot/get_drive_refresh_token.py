"""
Получить refresh_token для Google Drive OAuth.

Запускается ОДИН РАЗ локально на компьютере.
Открывает браузер для авторизации Google аккаунта.
Выводит refresh_token — его нужно прописать в .env (и на VPS).

Требования:
    pip install google-auth-oauthlib python-dotenv
"""
import io
import os
import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv(Path(__file__).parent / ".env")

CLIENT_ID = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Не найдены GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET в .env")
    print("   Добавь их и запусти скрипт снова.")
    sys.exit(1)

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

SCOPES = ["https://www.googleapis.com/auth/drive"]

print("=" * 60)
print("Получение refresh_token для Google Drive")
print("=" * 60)
print()
print("Сейчас откроется браузер.")
print("Войди в Google аккаунт, на котором лежит папка с чеками.")
print()

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
creds = flow.run_local_server(
    port=0,
    prompt="consent",
    access_type="offline",
)

refresh_token = creds.refresh_token

print()
print("=" * 60)
print("✅ Авторизация успешна!")
print("=" * 60)
print()
print("Твой refresh_token:")
print()
print(f"  {refresh_token}")
print()
print("Что дальше:")
print()
print("1. Скопируй строку выше")
print("2. Открой файл .env в папке FinanceBot")
print("3. Замени значение GOOGLE_DRIVE_REFRESH_TOKEN=")
print("4. Загрузи обновлённый .env на VPS:")
print()
print("   python vps_connect.py deploy")
print()
print("5. Перезапусти бота:")
print()
print("   python vps_connect.py restart")
print()
