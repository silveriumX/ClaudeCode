# Quick Start Guide - ChatManager

Система готова к запуску за 20 минут! Следуй этому чек-листу.

## Предварительные требования

- [ ] Python 3.7+ установлен
- [ ] Git установлен (опционально, для обновлений)
- [ ] Есть аккаунт Google
- [ ] Есть 2 Telegram аккаунта (основной + для UserBot)

## Шаг 1: Установка зависимостей (3 мин)

```bash
# Перейти в папку проекта
cd Projects/ChatManager

# Создать виртуальное окружение (опционально, но рекомендуется)
python -m venv venv

# Активировать виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

## Шаг 2: Google Sheets (5 мин)

### 2.1 Создать таблицу

1. Открыть https://sheets.google.com
2. Создать новую таблицу: "+ Create" → "Google Sheets"
3. Назвать: "ChatManager Database"
4. Скопировать ID из URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```

### 2.2 Создать листы

Создать 3 листа с ТОЧНЫМИ названиями:

**Лист 1: "Пользователи"**
```
telegram_id | имя | username | роль | статус
```

**Лист 2: "Чаты"**
```
id | название | creator_id | дата_создания | статус | invite_link | chat_id | описание
```

**Лист 3: "Участники"**
```
chat_id | user_id | роль_в_чате | дата_добавления
```

### 2.3 Service Account

См. подробности: `docs/GOOGLE_SHEETS_SETUP.md`

Краткая версия:
1. Google Cloud Console → New Project
2. Enable Google Sheets API
3. Create Service Account → Download JSON key
4. Сохранить как `service_account.json` в папке проекта
5. Дать доступ к таблице для email из `service_account.json`

### 2.4 Добавить себя

Узнать свой Telegram ID: написать @userinfobot

Добавить строку в "Пользователи":
```
YOUR_TELEGRAM_ID | Your Name | your_username | admin | active
```

## Шаг 3: Получить токены (7 мин)

### 3.1 Control Bot Token

1. Открыть @BotFather в Telegram
2. Отправить: `/newbot`
3. Следовать инструкциям
4. Скопировать токен: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### 3.2 UserBot Credentials

⚠️ ВАЖНО: Использовать ОТДЕЛЬНЫЙ аккаунт, не основной!

1. Перейти на https://my.telegram.org/apps
2. Войти в Telegram аккаунт (для UserBot)
3. Create Application
4. Заполнить форму (любые данные)
5. Скопировать:
   - `api_id`: `12345678`
   - `api_hash`: `abcdef1234567890abcdef1234567890`

## Шаг 4: Конфигурация (2 мин)

Создать файл `.env` (скопировать из `.env.example`):

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
USERBOT_API_ID=YOUR_API_ID
USERBOT_API_HASH=YOUR_API_HASH
USERBOT_SESSION=chat_admin
GOOGLE_SHEETS_ID=YOUR_SHEETS_ID
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
CHAT_POLL_INTERVAL=10
REQUIRE_APPROVAL=False
```

Убедиться, что `service_account.json` находится в папке проекта.

## Шаг 5: Тестирование системы (1 мин)

```bash
python test_system.py
```

Должно быть:
```
[OK] TELEGRAM_BOT_TOKEN is set
[OK] USERBOT_API_ID is set
[OK] USERBOT_API_HASH is set
[OK] GOOGLE_SHEETS_ID is set
[OK] Google Sheets connection established
[OK] Users sheet: Пользователи
[OK] Chats sheet: Чаты
[OK] Participants sheet: Участники
=== ALL TESTS PASSED ===
```

Если есть ошибки - проверь конфигурацию и таблицу.

## Шаг 6: Запуск (2 мин)

### 6.1 UserBot (первый раз - с авторизацией)

```bash
python setup_userbot.py
```

Будет запрошено:
- Phone number: `+1234567890` (с кодом страны)
- Confirmation code: получить из Telegram
- 2FA password: если включен

После авторизации создастся `chat_admin.session`.

### 6.2 Запуск обоих ботов

**Терминал 1 - Control Bot:**
```bash
python bot.py
```

Должно быть:
```
ChatManager Bot is ready!
Starting polling...
```

**Терминал 2 - UserBot:**
```bash
python userbot.py
```

Должно быть:
```
Logged in as: Your Name (@username, ID: 123456789)
Starting polling loop (interval: 10s)
```

## Шаг 7: Первый тест (3 мин)

1. Открыть бота в Telegram (найти по username из @BotFather)
2. Отправить: `/start`
3. Должно прийти приветствие с вашей ролью
4. Отправить: `/new_chat`
5. Ввести название: "Test Chat"
6. Ввести описание: "-" (пропустить)
7. Подтвердить создание
8. Получить сообщение: "Chat request created! UserBot is creating..."
9. Подождать 10-30 секунд
10. Отправить: `/my_chats`
11. Получить invite link

## Готово!

Система работает! Теперь можно:

- Создавать чаты через бота
- Получать invite links автоматически
- Добавлять новых пользователей в Google Sheets
- Расширять функционал (см. README.md)

## Troubleshooting

### UserBot не авторизуется
- Проверь `USERBOT_API_ID` и `USERBOT_API_HASH`
- Удали `chat_admin.session` и запусти `setup_userbot.py` снова

### Control Bot не реагирует
- Проверь, что твой ID в листе "Пользователи"
- Убедись, что статус `active`
- Проверь логи: должно быть "ChatManager Bot is ready!"

### Чаты не создаются
- Проверь логи UserBot: должно быть "Logged in as..."
- Убедись, что в "Чаты" есть запросы со статусом `pending`
- Проверь, что UserBot имеет права создавать группы

### Ошибка Google Sheets
- Проверь, что service account имеет доступ к таблице
- Убедись, что листы названы ТОЧНО: "Пользователи", "Чаты", "Участники"
- Проверь, что заголовки в листах правильные

## Дальнейшие шаги

- [ ] Добавить коллег в "Пользователи"
- [ ] Настроить роли (admin/manager/member)
- [ ] Изучить расширение функционала в README.md
- [ ] Настроить деплой на VPS (опционально)
- [ ] Интегрировать AI-модерацию (опционально)

---

**Время выполнения:** ~20 минут
**Сложность:** Простая
**Результат:** Работающая система управления чатами
