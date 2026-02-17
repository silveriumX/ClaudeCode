# Google Sheets Setup Guide

Пошаговая инструкция по настройке Google Sheets для ChatManager Bot.

## Шаг 1: Создание Google Sheets таблицы

1. Перейдите на https://sheets.google.com
2. Создайте новую таблицу (кнопка "+ Создать" или "+ Create")
3. Назовите таблицу: "ChatManager Database" (или любое удобное имя)
4. Скопируйте ID таблицы из URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_SPREADSHEET_ID/edit
   ```

## Шаг 2: Создание листов

Создайте 3 листа в таблице с ТОЧНЫМИ названиями:

### Лист 1: "Пользователи"

Заголовки (первая строка):

| telegram_id | имя | username | роль | статус |
|-------------|-----|----------|------|--------|

**Описание колонок:**
- `telegram_id` - Telegram ID пользователя (число)
- `имя` - Полное имя пользователя
- `username` - Telegram username (без @)
- `роль` - Роль: `admin`, `manager`, или `member`
- `статус` - Статус: `active` или `blocked`

**Пример данных:**
```
123456789 | John Doe | johndoe | admin | active
987654321 | Jane Smith | janesmith | manager | active
```

### Лист 2: "Чаты"

Заголовки (первая строка):

| id | название | creator_id | дата_создания | статус | invite_link | chat_id | описание |
|----|----------|------------|---------------|--------|-------------|---------|----------|

**Описание колонок:**
- `id` - Уникальный ID запроса (генерируется ботом)
- `название` - Название чата
- `creator_id` - Telegram ID создателя
- `дата_создания` - Дата и время создания запроса
- `статус` - Статус: `pending`, `creating`, `created`, `failed`, `archived`
- `invite_link` - Ссылка-приглашение (заполняется UserBot)
- `chat_id` - Telegram chat_id (заполняется UserBot)
- `описание` - Описание чата (опционально)

**Пример данных:**
```
REQ-20260208-151030-a3c | Закупки январь | 123456789 | 08.02.2026 15:10:30 | created | https://t.me/+xyz | -1001234567890 | Чат для обсуждения закупок
```

### Лист 3: "Участники"

Заголовки (первая строка):

| chat_id | user_id | роль_в_чате | дата_добавления |
|---------|---------|-------------|-----------------|

**Описание колонок:**
- `chat_id` - Telegram chat_id
- `user_id` - Telegram user_id участника
- `роль_в_чате` - Роль: `creator`, `admin`, или `member`
- `дата_добавления` - Дата добавления в чат

**Пример данных:**
```
-1001234567890 | 123456789 | creator | 08.02.2026 15:10:35
-1001234567890 | 987654321 | member | 08.02.2026 15:11:00
```

## Шаг 3: Service Account

### 3.1 Создание Service Account

Используйте инструкцию из FinanceBot:

См. файл: `Projects/FinanceBot/docs/GOOGLE_SHEETS_SETUP_FIRST_TIME.md`

Краткая версия:
1. Перейдите в Google Cloud Console: https://console.cloud.google.com
2. Создайте новый проект (или выберите существующий)
3. Включите Google Sheets API:
   - APIs & Services → Library
   - Найдите "Google Sheets API"
   - Нажмите "Enable"
4. Создайте Service Account:
   - APIs & Services → Credentials
   - Create Credentials → Service Account
   - Заполните имя: "chatmanager-bot"
   - Нажмите Create and Continue
5. Скачайте JSON ключ:
   - Перейдите в созданный Service Account
   - Keys → Add Key → Create New Key
   - Выберите JSON
   - Сохраните файл как `service_account.json` в папку проекта

### 3.2 Предоставление доступа к таблице

1. Откройте файл `service_account.json`
2. Найдите поле `client_email`, например:
   ```json
   "client_email": "chatmanager-bot@project-id.iam.gserviceaccount.com"
   ```
3. Скопируйте этот email
4. Откройте вашу Google Sheets таблицу
5. Нажмите "Поделиться" (Share) в правом верхнем углу
6. Вставьте скопированный email
7. Выберите роль: "Редактор" (Editor)
8. Снимите галочку "Уведомить" (Notify)
9. Нажмите "Готово" (Done)

## Шаг 4: Добавление тестового пользователя

Чтобы протестировать бота, добавьте себя в лист "Пользователи":

1. Узнайте свой Telegram ID:
   - Напишите боту @userinfobot
   - Он отправит ваш ID
2. Добавьте строку в лист "Пользователи":
   ```
   YOUR_TELEGRAM_ID | Your Name | your_username | admin | active
   ```

Пример:
```
123456789 | John Doe | johndoe | admin | active
```

## Шаг 5: Конфигурация .env

Создайте файл `.env` в папке проекта (на основе `.env.example`):

```env
# Control Bot Token (получить у @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# UserBot (получить на https://my.telegram.org/apps)
USERBOT_API_ID=12345678
USERBOT_API_HASH=abcdef1234567890abcdef1234567890
USERBOT_SESSION=chat_admin

# Google Sheets (ID из URL таблицы)
GOOGLE_SHEETS_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# Настройки (опционально)
CHAT_POLL_INTERVAL=10
REQUIRE_APPROVAL=False
```

## Шаг 6: Проверка настройки

1. Убедитесь, что `service_account.json` находится в папке проекта
2. Убедитесь, что `.env` заполнен корректными данными
3. Убедитесь, что в листе "Пользователи" есть хотя бы один пользователь с ролью `admin`
4. Все листы созданы с правильными заголовками

## Готово!

Теперь можно запускать бота:

```bash
# Активировать виртуальное окружение (если есть)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Установить зависимости
pip install -r requirements.txt

# Запустить Control Bot
python bot.py

# В другом терминале - UserBot
python userbot.py
```

## Troubleshooting

### Ошибка: "List 'Пользователи' не найден"
- Проверьте, что лист называется ТОЧНО "Пользователи" (с заглавной буквы, кириллица)
- Убедитесь, что в config.py: `SHEET_USERS = 'Пользователи'`

### Ошибка: "Service Account не имеет доступа"
- Убедитесь, что вы дали доступ к таблице для email из `service_account.json`
- Роль должна быть "Редактор" (Editor), не "Читатель" (Viewer)

### Бот не реагирует на команды
- Проверьте, что ваш Telegram ID добавлен в лист "Пользователи"
- Убедитесь, что статус `active`, не `blocked`
- Проверьте роль - должна быть `admin`, `manager` или `member`

### UserBot не создает чаты
- Проверьте, что UserBot успешно авторизовался (в логах должно быть "Logged in as...")
- Убедитесь, что в листе "Чаты" есть запросы со статусом `pending`
- Проверьте интервал polling: `CHAT_POLL_INTERVAL` в .env (по умолчанию 10 секунд)

---

**Версия:** 1.0
**Дата:** 08.02.2026
