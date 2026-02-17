# Настройка Google Drive через OAuth (QR-коды)

Загрузка QR-кодов идёт **от имени вашего Google-аккаунта** (OAuth), а не Service Account. Так Google разрешает писать файлы в ваш Drive.

## Шаг 1: OAuth 2.0 в Google Cloud Console

1. Откройте [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials).
2. Выберите тот же проект, где уже настроены Sheets (и где был Service Account).
3. **Create Credentials** → **OAuth client ID**.
4. Если первый раз — настройте **OAuth consent screen**:
   - User Type: **External** (или Internal, если Workspace).
   - Заполните название приложения, email поддержки, сохраните.
5. Снова **Create Credentials** → **OAuth client ID**:
   - Application type: **Desktop app**.
   - Name: например `Finance Bot Drive`.
6. Создайте и **скопируйте Client ID и Client Secret**.

## Шаг 2: Локально получить refresh_token

1. В папке проекта создайте/дополните `.env`:
   ```env
   GOOGLE_DRIVE_CLIENT_ID=ваш_client_id
   GOOGLE_DRIVE_CLIENT_SECRET=ваш_client_secret
   ```
2. Установите зависимости:
   ```bash
   pip install google-auth-oauthlib google-auth google-auth-httplib2
   ```
3. Запустите один раз:
   ```bash
   python get_drive_refresh_token.py
   ```
4. Откроется браузер — войдите в нужный Google-аккаунт и разрешите доступ к Google Drive.
5. В консоль выведется строка вида:
   ```env
   GOOGLE_DRIVE_REFRESH_TOKEN=1//0g...
   ```
   Скопируйте её в `.env`.

## Шаг 3: Папка на Drive

1. На [drive.google.com](https://drive.google.com) создайте папку для QR-кодов (например, «FinanceBot QR»).
2. Откройте папку, скопируйте ID из URL:
   `https://drive.google.com/drive/folders/**ВОТ_ЭТОТ_ID**`
3. Добавьте в `.env`:
   ```env
   GOOGLE_DRIVE_FOLDER_ID=этот_id
   ```

## Шаг 4: Итоговый .env (локально и на VPS)

```env
TELEGRAM_BOT_TOKEN=...
GOOGLE_SHEETS_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

GOOGLE_DRIVE_CLIENT_ID=...
GOOGLE_DRIVE_CLIENT_SECRET=...
GOOGLE_DRIVE_REFRESH_TOKEN=...
GOOGLE_DRIVE_FOLDER_ID=...
```

На VPS скопируйте эти переменные в `/root/finance_bot/.env`, перезапустите бота.

## Проверка

После перезапуска создайте CNY-заявку и загрузите QR-код. Файл должен появиться в указанной папке на вашем Google Drive, ссылка — в таблице.

## Безопасность

- `GOOGLE_DRIVE_CLIENT_SECRET` и `GOOGLE_DRIVE_REFRESH_TOKEN` — секреты. Не публикуйте их и не кладите в репозиторий.
- `.env` должен быть в `.gitignore`.
