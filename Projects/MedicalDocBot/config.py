"""
Конфигурация MedicalDocBot — отдельный Google-аккаунт (не связан с FinanceBot).
Поддерживается авторизация через Service Account (JSON-ключ).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Google: Service Account (рекомендуется) — путь к JSON-ключу
# Аккаунт cursor@neat-geode-329707.iam.gserviceaccount.com должен иметь доступ к папке и таблице
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account_medical.json")

# ID папки на Google Drive, куда загружать документы
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# ID Google Таблицы, куда писать строки о загруженных файлах
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")

# Имя листа в таблице (если нет — используется первый лист)
SHEET_NAME_DOCUMENTS = os.getenv("SHEET_NAME_DOCUMENTS", "Документы")

# Лист «Медицинские документы» — расширенная таблица с OCR-данными (v2)
SHEET_NAME_MEDICAL_DOCS = os.getenv("SHEET_NAME_MEDICAL_DOCS", "Медицинские документы")

# OAuth для Drive (как в FinanceBot) — тогда обычная папка в «Мой диск» работает, без Shared Drive
GOOGLE_DRIVE_CLIENT_ID = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "")
GOOGLE_DRIVE_CLIENT_SECRET = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "")
GOOGLE_DRIVE_REFRESH_TOKEN = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN", "")

# Для Service Account (Drive + Таблицы)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Для OAuth только Drive — refresh token выдаётся с этим scope (get_drive_refresh_token.py)
DRIVE_OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive"]

# OpenAI (для извлечения полей из OCR-текста через GPT-4o-mini)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
