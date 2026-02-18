---
name: google-drive-oauth-token
description: Получение и обновление OAuth refresh_token для Google Drive. Используй когда нужно настроить загрузку файлов на Google Drive через OAuth, когда видишь ошибки "storageQuotaExceeded", "invalid_grant", "Token has been expired or revoked", когда нужно создать скрипт get_drive_refresh_token.py, или когда бот не может загрузить файлы в Drive через Service Account.
version: 1.0.0
---

# Google Drive OAuth: получение refresh_token

## Когда нужен этот скилл

- Бот получает `403 storageQuotaExceeded` при загрузке в Drive
- Ошибка `invalid_grant: Token has been expired or revoked`
- Drive работает через Service Account, но файлы не сохраняются
- Нужно впервые настроить загрузку файлов на личный Google Drive

## Почему Service Account не работает для Drive

Service Account не имеет собственного дискового пространства. Попытка загрузить файл через SA вызывает:
```
403 storageQuotaExceeded: Service Accounts do not have storage quota.
```

**Решение:** использовать OAuth от имени реального Google-аккаунта, на Drive которого будут храниться файлы.

---

## Алгоритм действий

### 1. Проверить логи — подтвердить причину

```bash
python vps_connect.py errors 30
# или
python vps_connect.py shell "journalctl -u <service> -n 50 | grep -i 'drive\|oauth\|token'"
```

Признаки проблемы в логах:
- `Drive OAuth failed` → токен не работает, используется SA
- `Drive mode: Service Account` вместо `Drive mode: OAuth`
- `storageQuotaExceeded` при загрузке файла
- `invalid_grant` при старте бота

### 2. Создать скрипт get_drive_refresh_token.py

Создать в корне проекта файл `get_drive_refresh_token.py`:

```python
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
    print("ERROR: Не найдены GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET в .env")
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
print("Войди в Google аккаунт, на котором лежит папка с файлами.")
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
print("2. Открой файл .env в папке проекта")
print("3. Замени значение GOOGLE_DRIVE_REFRESH_TOKEN=")
print("4. Задеплой обновлённый .env на VPS:")
print()
print("   python vps_connect.py deploy")
print()
print("5. Перезапусти бота:")
print()
print("   python vps_connect.py restart")
print()
```

### 3. Запустить скрипт

```bash
pip install google-auth-oauthlib
python get_drive_refresh_token.py
```

Войти в браузере в нужный Google аккаунт, выдать разрешения.

### 4. Обновить .env

Скопировать токен из вывода скрипта в `.env`:
```
GOOGLE_DRIVE_REFRESH_TOKEN=1//03gZ...
```

### 5. Убедиться что .env попадает в deploy

Проверить `vps_connect.py` — `.env` должен быть в `CORE_FILES`:

```python
CORE_FILES = [
    "src/bot.py",
    ...
    "requirements.txt",
    ".env",          # ← должна быть эта строка
]
```

Если нет — добавить.

### 6. Задеплоить и проверить

```bash
python vps_connect.py deploy
python vps_connect.py restart
```

Проверить лог — должно появиться:
```
Drive: OAuth connection successful
Drive mode: OAuth
```

---

## Необходимые переменные в .env

```env
GOOGLE_DRIVE_CLIENT_ID=xxxxxxxxx.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=GOCSPX-xxxxxxxxx
GOOGLE_DRIVE_REFRESH_TOKEN=1//03gZ...            # получается скриптом
GOOGLE_DRIVE_FOLDER_ID=1DKgTYETPST...            # ID папки на Drive
```

Получить `CLIENT_ID` и `CLIENT_SECRET`:
1. Google Cloud Console → APIs & Services → Credentials
2. Create Credentials → OAuth 2.0 Client ID → Desktop app
3. Папку `GOOGLE_DRIVE_FOLDER_ID` скопировать из URL: `drive.google.com/drive/folders/ВОТ_ЭТО`

---

## Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `storageQuotaExceeded` | Используется Service Account | Получить refresh_token через скрипт |
| `invalid_grant` | Токен истёк или был отозван | Перезапустить скрипт, получить новый токен |
| `Drive mode: Service Account` в логах | OAuth не настроен или упал | Проверить все 4 переменные в .env |
| Браузер не открылся | Нет GUI / запуск на сервере | Запускать скрипт ЛОКАЛЬНО, не на VPS |
| `UnicodeEncodeError` при выводе токена | Windows cp1251 консоль | Скрипт уже содержит фикс через `io.TextIOWrapper` |

---

## Важно: токен получается ОДИН РАЗ локально

- Скрипт запускается на локальном компьютере (нужен браузер)
- Полученный токен прописывается в `.env` и деплоится на VPS
- Refresh token не истекает сам по себе, но аннулируется если:
  - Пользователь отозвал доступ в Google аккаунте
  - Приложение было пересоздано в Google Cloud Console
  - Прошло 6 месяцев без использования (только для unverified apps)
