#!/usr/bin/env python3
"""
Один раз получить refresh_token для Google Drive (OAuth).
Запустить локально: откроется браузер, войди в Google, нажми «Разрешить» — refresh token попадёт в .env.
"""
import os
import sys
from pathlib import Path

# .env в папке MedicalDocBot
PROJECT_DIR = Path(__file__).resolve().parent
os.chdir(PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_DRIVE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("=" * 60)
    print("Сначала создай OAuth 2.0 в Google Cloud Console:")
    print("1. https://console.cloud.google.com/apis/credentials")
    print("2. Выбери проект (например neat-geode-329707)")
    print("3. Create credentials -> OAuth client ID")
    print("4. Если первый раз: настрой OAuth consent screen (External, название приложения)")
    print("5. Application type: Desktop app, Name: MedicalDocBot Drive")
    print("6. Скопируй Client ID и Client Secret")
    print()
    print("Добавь в MedicalDocBot/.env:")
    print("  GOOGLE_DRIVE_CLIENT_ID=...")
    print("  GOOGLE_DRIVE_CLIENT_SECRET=...")
    print("  и запусти этот скрипт снова.")
    print("=" * 60)
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Установи: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": ["http://localhost:8765/", "http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )

    print("Откроется браузер — войди в Google и нажми «Разрешить».")
    creds = flow.run_local_server(port=8765)

    refresh_token = creds.refresh_token
    if not refresh_token:
        print("Refresh token не получен. Попробуй снова.")
        sys.exit(1)

    env_path = PROJECT_DIR / ".env"
    content = env_path.read_text(encoding="utf-8")
    if "GOOGLE_DRIVE_REFRESH_TOKEN=" in content:
        import re
        content = re.sub(r"GOOGLE_DRIVE_REFRESH_TOKEN=.*", "GOOGLE_DRIVE_REFRESH_TOKEN=" + refresh_token, content)
    else:
        content = content.rstrip() + "\nGOOGLE_DRIVE_REFRESH_TOKEN=" + refresh_token + "\n"
    env_path.write_text(content, encoding="utf-8")

    print()
    print("=" * 60)
    print("Готово. GOOGLE_DRIVE_REFRESH_TOKEN записан в .env")
    print("Дальше: python deploy_to_vps.py — на VPS подхватится тот же .env")
    print("=" * 60)


if __name__ == "__main__":
    main()
