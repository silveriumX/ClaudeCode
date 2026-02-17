# Подключение Google Диска, Таблиц и YouTube к Cursor

Пошаговая инструкция: что делать **после** создания проекта в Google Cloud и включения API (YouTube Data API v3, Google Sheets API, Google Drive API).

---

## Что у вас уже есть

- Проект в [Google Cloud Console](https://console.cloud.google.com/)
- Включённые API: **YouTube**, **Google Sheets**, **Google Drive**

MCP Google Drive (`@modelcontextprotocol/server-gdrive`) отключён из‑за ошибки OAuth invalid_client. Для Диска используйте скрипты + Service Account (см. ниже). Ниже — как создать учётные данные и довести интеграцию до рабочего состояния.

---

## Простыми словами: что за «разные способы»

Представьте два способа дать программе доступ к вашим данным.

**1. Робот (Service Account)**
Вы создаёте в Google Cloud «робота» — у него есть свой email (типа `bot@ваш-проект.iam.gserviceaccount.com`). Вы **вручную делитесь** с ним тем, что ему нужно:
— Открываете таблицу → «Поделиться» → вставляете email робота.
— Открываете папку на Диске → «Поделиться» → вставляете тот же email.
Один файл `credentials.json` — это и есть «паспорт» этого робота. Скрипты (Python, Cursor) используют этот файл и получают доступ ко всему, чем вы с роботом поделились: и к таблицам, и к папкам на Диске. **Один JSON = один робот = и Таблицы, и Диск** (если вы с ним поделились).

**2. Вход «как я» (OAuth)**
Программа говорит: «Войди в свой Google-аккаунт в браузере и нажми „Разрешить“». После этого программа работает **от вашего имени** — видит весь ваш Диск, все ваши таблицы, без того чтобы вы вручную шарили каждую папку с роботом.
Так устроен **MCP Google Drive** в Cursor: он не умеет «робота», он умеет только «войди как я». Поэтому для него нужен отдельный шаг — OAuth (файл `gdrive_creds.json` и один раз вход в браузере).

**Итого:**
- **Свои скрипты** (таблицы, загрузка на Диск и т.д.) — один робот, один `credentials.json`, вы просто шарите с ним нужные таблицы и папки.
- **Встроенный в Cursor инструмент «Google Drive»** (MCP) — работает «как вы», для него нужен вход через браузер (OAuth), отдельно от робота.

**YouTube** — та же идея в двух вариантах:
- **Поиск видео** (публичное) — достаточно **API Key** (просто ключ в настройках, без входа).
- **Ваш канал** (загрузка, аналитика, плейлисты) — нужно один раз **войти как вы** (OAuth), как с Диском.

---

## Что сделать, чтобы всё работало: Диск + поиск YouTube + полноценный YouTube

Ниже — минимальный набор действий.

| Цель | Что сделать |
|------|-------------|
| **Работать со своим Диском** (из Cursor: искать файлы, читать) | Настроить **OAuth для Drive MCP**: создать OAuth-клиент в Google Cloud, сохранить `client_id` и `client_secret` в `gdrive_creds.json`, один раз войти в браузере, когда MCP попросит. Подробно — раздел 3 ниже. |
| **Поиск видео на YouTube** (из скриптов или Cursor) | Создать **API Key** в Google Cloud, вставить его в `.env` как `YOUTUBE_API_KEY`. Подробно — раздел 4.1. |
| **Полноценно пользоваться YouTube** (загрузка, плейлисты, аналитика своего канала) | Дополнительно настроить **OAuth для YouTube**: тот же или отдельный OAuth-клиент (Desktop), один раз войти в браузере, в коде использовать сохранённые токены. Подробно — раздел 4.2. |
| **Таблицы и Диск из своих скриптов** (без MCP) | Один **Service Account**: скачать JSON, сохранить как `credentials.json`, в таблицах и нужных папках на Диске нажать «Поделиться» и добавить email из этого JSON. В `.env` указать путь к файлу и при необходимости `GOOGLE_SHEETS_ID`. Подробно — раздел 2. |

### Drive без MCP (рабочий вариант)

MCP `@modelcontextprotocol/server-gdrive` часто даёт **invalid_client** по OAuth. Вместо него используйте **скрипты + Service Account**:

1. В Google Drive откройте нужную папку → **Поделиться** → добавьте **cursor@neat-geode-329707.iam.gserviceaccount.com** (или ваш Service Account email из `credentials.json`) с правами **Просмотр** или **Редактирование**.
2. Скопируйте **ID папки** из URL: `https://drive.google.com/drive/folders/ЭТОТ_ID`.
3. В Cursor или в терминале выполните:
   ```bash
   python Scripts/list_drive_folder.py ЭТОТ_ID
   ```
   Или задайте в `.env`: `GOOGLE_DRIVE_FOLDER_ID=...` и запускайте `python Scripts/list_drive_folder.py`.
4. Для загрузки файлов и других операций используйте `Utils/google_api.py` (методы `upload_file`, `list_files_in_folder`, `create_folder` и т.д.) — они уже работают с `credentials.json`.

После этого: один раз настроили OAuth для Drive MCP — работаете со своим Диском через Cursor; один раз создали API Key для YouTube — можете искать видео; при необходимости добавили OAuth для YouTube — можете управлять своим каналом.

---

## Почему разные способы авторизации? (подробнее)

- **Ваши скрипты** (Sheets, Drive) — один Service Account, один `credentials.json`, оба API (Sheets и Drive) работают с ним.
- **MCP Google Drive** — это готовый сервер, он умеет только OAuth («войти как вы»), поэтому для него нужен отдельный файл `gdrive_creds.json` и один раз вход в браузере.
- **YouTube**: поиск и публичные данные — **API Key**; загрузка и управление своим каналом — **OAuth** (как с Диском).

---

## 1. Какие учётные данные нужны

| Сервис        | Для чего в Cursor                    | Тип учётных данных      |
|---------------|--------------------------------------|-------------------------|
| **Google Drive**  | MCP: поиск/чтение файлов в вашем Диске | **OAuth 2.0** (Desktop) |
| **Google Таблицы**| Скрипты и AI (чтение/запись)          | **Service Account**     |
| **YouTube**       | Публичные данные (поиск, метаданные) | **API Key**            |
| **YouTube**       | Свой канал (загрузка, статистика)    | **OAuth 2.0** (опционально) |

Дальше — по шагам для каждого типа.

---

## 2. Service Account (для Google Таблиц и Drive из скриптов)

**Один файл `credentials.json`** подходит и для Sheets API, и для Drive API в ваших скриптах. Подходит для автоматизации без входа пользователя: скрипты в Cursor, `Utils/google_api.py`, загрузка в Drive и т.д.

### 2.1 Создать Service Account

1. В Google Cloud: **APIs & Services** → **Credentials**.
2. **Create Credentials** → **Service account**.
3. Имя, например: `cursor-sheets-drive`.
4. **Create and Continue** → роль **Editor** (или нужная вам) → **Done**.

### 2.2 Создать ключ (JSON)

1. Откройте созданный Service Account.
2. Вкладка **Keys** → **Add Key** → **Create new key**.
3. Тип: **JSON** → **Create** — файл скачается.

### 2.3 Сохранить и подключить

1. Сохраните файл в безопасное место, например:
   - `C:\Users\Admin\Documents\Cursor\credentials.json`
   или
   - `C:\Users\Admin\Documents\Cursor\Scripts\GoogleSheets\credentials.json`
2. Добавьте в `.gitignore`:
   ```text
   credentials.json
   gdrive_creds.json
   ```
3. Для **Google Таблиц**: откройте таблицу → **Поделиться** → добавьте `client_email` из JSON (вид `...@....iam.gserviceaccount.com`) с правами **Редактор**.

Переменные в `.env` (пример):

```env
GOOGLE_SERVICE_ACCOUNT_FILE=C:\Users\Admin\Documents\Cursor\credentials.json
GOOGLE_SHEETS_ID=ваш_spreadsheet_id
```

Использование в Cursor: скрипты из `Scripts/GoogleSheets/`, `Utils/google_api.py` и skill **google-sheets-integration** (см. `.cursor/skills/google-sheets-integration/SKILL.md`).

---

## 3. OAuth 2.0 (для Google Drive MCP и «своего» Диска)

Чтобы MCP в Cursor работал с **вашим** Google Диском (поиск, чтение файлов), нужны OAuth-учётные данные и один раз войти в аккаунт.

### 3.1 Настроить экран согласия OAuth

1. **APIs & Services** → **OAuth consent screen**.
2. User Type: **External** (или Internal, если у вас Google Workspace).
3. Заполните название приложения, email поддержки, сохраните.

**External — это нормально и безопасно для личного использования.**
- У личного аккаунта (@gmail.com) есть только вариант External; Internal доступен только в корпоративном Google Workspace.
- **External** не значит «приложение публичное»: вы не публикуете его в магазин. Оно просто может запросить вход от любого пользователя Google, если тот сам нажмёт «Разрешить».
- Оставьте приложение в статусе **Testing** (тестирование): тогда войти смогут только вы и до 100 добавленных вами тестовых пользователей. Верификацию Google проходить не нужно. Не нажимайте «Publish app» — так приложение остаётся личным.
- Client ID и Client Secret храните только у себя (файл `gdrive_creds.json` в `.gitignore`, не коммитить). Для сценария «только я и Cursor + мой Диск» этого достаточно.

### 3.2 Создать OAuth Client ID

1. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.
2. Application type: **Desktop app**.
3. Имя, например: `Cursor Google Drive`.
4. **Create** — появится окно с **Client ID** и **Client Secret**.

### 3.3 Файл учётных данных для MCP

Официальный сервер `@modelcontextprotocol/server-gdrive` может ожидать либо путь к файлу, либо JSON в переменной окружения. В вашем `.cursor/mcp.json` указано:

```json
"GOOGLE_DRIVE_CREDENTIALS_JSON": "${workspaceFolder}\\gdrive_creds.json"
```

Создайте файл `gdrive_creds.json` в корне workspace (рядом с `.env`) в формате **OAuth client**:

```json
{
  "installed": {
    "client_id": "ВАШ_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "ваш-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "ВАШ_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

Подставьте свои **Client ID** и **Client secret** из шага 3.2. Для типа **Desktop** в консоли часто дают только `client_id` и `client_secret` — тогда структура может быть такой (зависит от реализации MCP):

```json
{
  "client_id": "xxx.apps.googleusercontent.com",
  "client_secret": "xxx"
}
```

Если MCP при первом запуске откроет браузер для входа — войдите в свой Google-аккаунт и разрешите доступ. После этого токены обычно сохраняются и MCP будет работать с вашим Диском.

**Важно:** не коммитьте `gdrive_creds.json` в git (должен быть в `.gitignore`).

---

## 4. YouTube API

### 4.1 API Key (поиск, публичные данные)

1. **APIs & Services** → **Credentials** → **Create Credentials** → **API key**.
2. Создайте ключ, при необходимости ограничьте по API (YouTube Data API v3) и по HTTP referrers / IP.
3. В `.env` добавьте:

```env
YOUTUBE_API_KEY=ваш_api_key
```

Этого достаточно, чтобы скрипты или код в Cursor обращались к YouTube Data API v3 (поиск видео, метаданные каналов и т.д.).

### 4.2 OAuth для своего канала (опционально)

Если нужно загружать видео, управлять плейлистами, смотреть аналитику **своего** канала:

1. Используйте тот же OAuth client, что и для Drive (тип Desktop), или создайте второй.
2. В коде запрашивайте scope `https://www.googleapis.com/auth/youtube` (и при необходимости `youtube.upload`, `youtube.readonly`).
3. Один раз выполните вход в браузере, сохраните токены (например, в `token.json`) и используйте их в скриптах.

Отдельного MCP для YouTube в текущей конфигурации нет — доступ через свои скрипты и переменные окружения.

---

## 5. Краткий чеклист «что делать дальше»

- [ ] **Service Account** создан, JSON-ключ скачан и сохранён (например, `credentials.json`).
- [ ] `credentials.json` добавлен в `.gitignore`.
- [ ] Для нужных Google Таблиц: доступ по email Service Account выдан (Поделиться).
- [ ] В `.env` указаны `GOOGLE_SERVICE_ACCOUNT_FILE` и при необходимости `GOOGLE_SHEETS_ID`.
- [ ] **OAuth client** (Desktop) создан в Google Cloud.
- [ ] Файл `gdrive_creds.json` создан в корне workspace с `client_id` и `client_secret` (и при необходимости полной структурой `installed`).
- [ ] В `.cursor/mcp.json` путь в `GOOGLE_DRIVE_CREDENTIALS_JSON` ведёт на существующий `gdrive_creds.json`.
- [ ] Cursor перезапущен; при первом использовании Drive MCP при необходимости выполнен вход в Google.
- [ ] **YouTube:** создан API key и в `.env` добавлен `YOUTUBE_API_KEY`.
- [ ] При необходимости YouTube OAuth настроен в своих скриптах (отдельно от этой инструкции).

---

## 6. Где что лежит в проекте

| Назначение              | Файл / место |
|-------------------------|--------------|
| Учётные данные Drive MCP / Service Account | `gdrive_creds.json` (корень workspace) |
| Сервисный аккаунт для Google Таблиц (редактирование) | **cursor@neat-geode-329707.iam.gserviceaccount.com** — добавить в «Поделиться» на нужные таблицы как редактора |
| Service Account (Таблицы/Drive API) | `gdrive_creds.json` или `credentials.json` (путь в `GOOGLE_SERVICE_ACCOUNT_FILE`) |
| Переменные окружения    | `.env` (см. `.env.example`), в т.ч. `GOOGLE_SHEETS_SERVICE_ACCOUNT` |
| MCP конфиг              | `.cursor/mcp.json` |
| Скрипты Google Таблиц   | `Scripts/GoogleSheets/`, `Utils/google_api.py` |
| Skill по Таблицам       | `.cursor/skills/google-sheets-integration/SKILL.md` |
| Документация по Sheets  | `Documentation/API/GOOGLE_SHEETS_INTEGRATION.md` |

---

## 7. Проверка

- **Таблицы:** выполните `python Scripts/GoogleSheets/google_sheets_reader.py` (если таблица по ссылке «доступна всем») или используйте `Utils/google_api.py` с `credentials.json` и `GOOGLE_SHEETS_ID`.
- **Drive MCP:** в Cursor в чате попросите, например: «Покажи список файлов в моём Google Диске» или «Найди в Drive документы с названием X» — AI должен использовать инструменты MCP.
- **YouTube:** напишите скрипт или запрос к YouTube Data API v3 с `YOUTUBE_API_KEY` (например, поиск видео) и выполните его из Cursor/терминала.

После выполнения этих шагов Google Диск (через MCP), Google Таблицы (через скрипты и skill) и YouTube (через API key и при необходимости OAuth) будут подключены к Cursor.
