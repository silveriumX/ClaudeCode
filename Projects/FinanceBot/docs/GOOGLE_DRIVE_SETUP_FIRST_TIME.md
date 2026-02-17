# Подключение к Google Drive для работы с файлами с нуля

Пошаговая инструкция для человека, который **никогда не настраивал Google Drive API**. Как включить API, создать папку, настроить загрузку и доступ к файлам через Service Account или OAuth.

**Что получится:** возможность загружать файлы в Google Drive, создавать папки и получать ссылки на файлы из кода или приложения.

**Время:** около 15–20 минут.

---

## Что нужно заранее

- Проект в Google Cloud (если его ещё нет — создайте в [console.cloud.google.com](https://console.cloud.google.com/): выпадающий список проекта → New Project).
- Решите, как будете подключаться к Drive:
  - **Вариант A (проще):** **Service Account** — нужен файл `service_account.json` из этого же проекта. Файлы загружаются «от имени» этой учётной записи; папку на Drive вы создаёте своим аккаунтом и даёте доступ по email Service Account.
  - **Вариант B:** **OAuth** — файлы попадают в **ваш личный** Google Drive. Один раз входите в браузере и получаете refresh_token.

Ниже — общие шаги (включение API, папка), затем отдельно A и B.

---

## Часть 1. Включить Google Drive API

API должен быть включён **в том же проекте**, где создан Service Account (для варианта A) или где будет создан OAuth-клиент (для варианта B).

### Шаг 1.1. Открыть консоль и выбрать проект

1. Откройте в браузере: **https://console.cloud.google.com/**
2. Вверху страницы выберите **ваш проект** (тот, в котором будете создавать учётные данные для Drive).

### Шаг 1.2. Открыть библиотеку API

1. В **левом меню** нажмите **"APIs & Services"** (или **"Интерфейсы и сервисы"**).
2. В подменю выберите **"Library"** (**"Библиотека"**).

### Шаг 1.3. Включить Google Drive API

1. В поисковой строке вверху введите: **Google Drive API**.
2. В результатах нажмите на карточку **"Google Drive API"**.
3. На странице API нажмите синюю кнопку **"Enable"** (**"Включить"**).
4. Дождитесь сообщения об успешном включении.

Без этого шага загрузка файлов будет возвращать ошибку **403 (accessNotConfigured)**.

---

## Часть 2. Папка на Google Drive

Нужна папка, куда будут загружаться файлы (или создайте её позже из кода).

### Шаг 2.1. Создать папку

1. Откройте **https://drive.google.com/** в браузере.
2. Войдите в нужный Google-аккаунт.
3. Нажмите **"Создать"** (**"New"**) → **"Папку"** (**"Folder"**).
4. Введите название папки (например: **Загрузки приложения**).
5. Нажмите **"Создать"** (**"Create"**).

### Шаг 2.2. Узнать ID папки

1. Откройте созданную папку (двойной клик).
2. Посмотрите адресную строку браузера. URL будет вида:
   ```
   https://drive.google.com/drive/folders/1a2B3c4D5e6F7g8H9i0J_xxxxxxxxxx
   ```
3. **ID папки** — это часть после `/folders/`:
   ```
   1a2B3c4D5e6F7g8H9i0J_xxxxxxxxxx
   ```
4. Скопируйте этот ID — он понадобится в конфиге (часто как `GOOGLE_DRIVE_FOLDER_ID` или аналог).

---

## Вариант A: Service Account

Файлы загружаются от имени Service Account. У вас уже должен быть файл `service_account.json` из этого же проекта (если нет — создайте Service Account в APIs & Services → Credentials → Create Credentials → Service account, затем добавьте ключ типа JSON и скачайте его).

### Шаг A.1. Узнать email Service Account

1. Откройте файл **`service_account.json`**.
2. Найдите поле **`"client_email"`**. Значение — email вида:
   `имя@проект.iam.gserviceaccount.com`
3. Скопируйте этот email целиком.

### Шаг A.2. Дать папке доступ для Service Account

1. На **https://drive.google.com/** откройте нужную папку (из шага 2.1).
2. Нажмите правой кнопкой по папке → **"Поделиться"** (**"Share"**) или кнопку **"Поделиться"** вверху.
3. В поле "Добавить пользователей" **вставьте скопированный email** Service Account.
4. Роль выберите **"Редактор"** (**"Editor"**).
5. Снимите галочку "Уведомить" (необязательно).
6. Нажмите **"Готово"** / **"Отправить"**.

### Шаг A.3. Настроить приложение

В конфиге или переменных окружения укажите:

- Путь к **`service_account.json`** (или содержимое ключа).
- **ID папки** из шага 2.2 (например переменная `GOOGLE_DRIVE_FOLDER_ID`).

Для варианта A **не нужны** OAuth Client ID, Client Secret и Refresh Token — приложение использует только `service_account.json` и ID папки.

**Итог по варианту A:** Drive API включён, папка создана, доступ папки выдан Service Account, в настройках указаны путь к ключу и ID папки. После этого можно вызывать API загрузки файлов в эту папку.

---

## Вариант B: OAuth — файлы в вашем личном Drive

Файлы загружаются **от имени вашего Google-аккаунта** и появляются в вашем Drive. Нужно один раз настроить OAuth (экран согласия и учётные данные приложения).

### Шаг B.1. Настроить OAuth consent screen

1. Откройте **https://console.cloud.google.com/apis/credentials**
2. Убедитесь, что выбран нужный проект.
3. В левом меню нажмите **"OAuth consent screen"** (**"Экран согласия OAuth"**).
4. Если тип приложения ещё не выбран:
   - Выберите **"External"** (**"Внешний"**) (или "Internal", если Google Workspace).
   - Нажмите **"Create"** (**"Создать"**).
5. Заполните обязательные поля:
   - **App name:** например `Моё приложение Drive`
   - **User support email:** ваш email
   - **Developer contact:** ваш email
6. Нажмите **"Save and Continue"** (**"Сохранить и продолжить"**).
7. На шаге "Scopes" нажмите **"Add or Remove Scopes"**, найдите **Google Drive API** и отметьте scope **`.../auth/drive`** (полный доступ к Drive). Сохраните.
8. Снова **"Save and Continue"**.
9. На шаге "Test users" (если приложение External): нажмите **"Add Users"** и добавьте свой Google-email. Сохраните.
10. Нажмите **"Back to Dashboard"**.

### Шаг B.2. Создать OAuth 2.0 Client ID (Desktop)

1. В меню слева выберите **"Credentials"** (**"Учётные данные"**).
2. Нажмите **"+ Create Credentials"** (**"+ Создать учётные данные"**).
3. Выберите **"OAuth client ID"**.
4. **Application type:** выберите **"Desktop app"** (**"Классическое приложение"**).
5. **Name:** любое (например `Drive Desktop`).
6. Нажмите **"Create"** (**"Создать"**).
7. Появится окно с **Client ID** и **Client Secret**. Скопируйте оба значения или нажмите **"Download JSON"**.

### Шаг B.3. Добавить Client ID и Client Secret в конфиг

В конфиге или переменных окружения укажите (подставьте свои значения):

- `GOOGLE_DRIVE_CLIENT_ID` — Client ID
- `GOOGLE_DRIVE_CLIENT_SECRET` — Client Secret
- `GOOGLE_DRIVE_FOLDER_ID` — ID папки из шага 2.2

Переменную для **Refresh Token** пока не заполняйте — её получите на следующем шаге.

### Шаг B.4. Получить refresh_token

Нужно один раз авторизоваться в браузере и сохранить refresh_token. Обычно для этого в проекте есть скрипт (например `get_drive_refresh_token.py` или аналог), который:

1. Использует Client ID и Client Secret из конфига.
2. Запускает локальный OAuth-сервер и открывает браузер.
3. Вы входите в Google и нажимаете «Разрешить» доступ к Drive.
4. Скрипт получает refresh_token и выводит его (или записывает в конфиг).

**Если такого скрипта нет**, можно использовать общий поток:

1. Установите: `pip install google-auth-oauthlib`
2. В коде используйте `google_auth_oauthlib.flow.InstalledAppFlow` с scope `https://www.googleapis.com/auth/drive`, запустите `run_local_server()`, после входа в браузере возьмите `creds.refresh_token` и сохраните в конфиг как `GOOGLE_DRIVE_REFRESH_TOKEN` (или аналог).

При первом входе в браузере, если появится «Приложение не проверено», выберите **"Переход к приложению"** / **"Advanced"** → переход по ссылке вашего приложения, затем нажмите **"Разрешить"** для доступа к Google Drive.

### Шаг B.5. Папка для OAuth

Папка может быть в **вашем** Drive — вы создали её в части 2. Убедитесь, что в конфиге указан **ID этой папки**. Отдельно давать доступ кому-то не нужно: загрузка идёт от вашего имени.

**Итог по варианту B:** Drive API включён, настроен OAuth consent screen, создан Desktop OAuth client, в конфиге указаны Client ID, Client Secret, Folder ID и Refresh Token. После этого приложение может загружать файлы в указанную папку на вашем Drive.

---

## Проверка работы

После настройки проверьте подключение к Drive из кода. Пример на Python с Google API Client:

```python
from google.oauth2.credentials import Credentials  # для OAuth
# или
from google.oauth2.service_account import Credentials  # для Service Account
from googleapiclient.discovery import build

# Для Service Account:
# creds = Credentials.from_service_account_file('service_account.json', scopes=['https://www.googleapis.com/auth/drive'])
# Для OAuth: подставьте refresh_token, client_id, client_secret

service = build('drive', 'v3', credentials=creds)
results = service.files().list(pageSize=5, fields="files(id, name)").execute()
print('OK', results.get('files', []))
```

Если выводится список файлов или пустой список без ошибки — подключение настроено верно.

---

## Операции с файлами (общее)

| Действие | Описание |
|----------|----------|
| **Загрузка файла** | Через Drive API v3: `files().create()` с `media_body` и при необходимости `parents=[folder_id]`. После загрузки можно выдать право «по ссылке» и получить `webViewLink` или ссылку на скачивание. |
| **Создание папки** | `files().create()` с `mimeType: "application/vnd.google-apps.folder"` и при необходимости `parents`. |
| **Удаление файла** | `files().delete(fileId=id)`. В коде приложения эту операцию нужно вызывать явно; по умолчанию многие скрипты только загружают. |
| **Список файлов в папке** | `files().list(q=f"'{folder_id}' in parents", fields="files(id, name, webViewLink)")`. |

Конкретные имена методов и переменных зависят от вашего приложения; здесь указана общая схема через Drive API v3.

---

## Частые ошибки

| Ошибка / Симптом | Что проверить |
|------------------|----------------|
| **403 / accessNotConfigured** | Google Drive API включён **в том же проекте**, где создан Service Account или OAuth client (APIs & Services → Library → Google Drive API → Enable). |
| **403 / permission denied** (вариант A) | Папка на Drive расшарена для **редактора** по email из `service_account.json` (поле `client_email`). |
| **Refresh token не получен** (вариант B) | В OAuth consent screen добавлен ваш email в Test users; в браузере нажали «Разрешить» для доступа к Drive. |
| **Файл не появляется в папке** | В конфиге указан правильный **ID папки** (из URL `.../folders/ID`, без лишних символов). |
| **Учётные данные в другом проекте** | Drive API и учётные данные (Service Account или OAuth client) должны быть в **одном проекте** в Google Cloud. |

---

## Краткий чеклист

- [ ] Google Drive API включён в нужном проекте.
- [ ] Создана папка на Drive, скопирован её ID.
- [ ] **Вариант A:** папка расшарена на email Service Account (Редактор); в настройках указаны путь к `service_account.json` и ID папки.
- [ ] **Вариант B:** настроен OAuth consent screen, создан OAuth client (Desktop), в конфиге указаны Client ID, Client Secret, Folder ID; получен refresh_token и добавлен в конфиг.
- [ ] Проверка из кода: запрос к Drive API (например list files) выполняется без ошибки.

---

**Версия:** 1.1
**Дата:** 07.02.2026
