---
name: google-drive-sheets-auth
description: Google Drive and Sheets auth - OAuth vs Service Account, 403 storage quota fix, scopes for refresh token, webViewLink for files. Use when connecting app to Drive or Sheets, getting 403 on upload, or setting up OAuth/SA for Google APIs.
---

# Google Drive и Sheets: авторизация и типичные ошибки

## Правила

### 1. Drive: 403 «Service Accounts do not have storage quota»

- У **Service Account** нет квоты в обычной папке «Мой диск». Варианты: использовать **OAuth** (обычная папка в «Мой диск») или **Shared Drive** (общий диск), куда SA добавлен как редактор/менеджер.

### 2. OAuth: отдельный scope для Drive

- Если refresh token получен с одним scope (только `https://www.googleapis.com/auth/drive`), при создании credentials для Drive использовать **именно этот scope**, а не общий список (Drive + Sheets). Иначе при refresh будет **invalid_scope**. Для Sheets использовать отдельные credentials с scope для Sheets (или оба scope при первичном получении refresh token).

### 3. Ссылки на файлы

- Отдавать пользователю ссылку для **просмотра**: `webViewLink` из API или `https://drive.google.com/file/d/{id}/view`, а не `uc?export=download` (чтобы открывалось в браузере, а не сразу скачивалось).

### 4. Доступ

- Папку Drive (или Shared Drive) и таблицу Sheets нужно расшарить с тем аккаунтом, от имени которого идёт запрос (email SA или пользователь OAuth). Включить в Google Cloud Console: Drive API и Sheets API (и при необходимости Document AI / Vision).
