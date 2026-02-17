# ChatManager Bot

AI-first система управления рабочими чатами в Telegram с гибридным подходом (UserBot + Control Bot).

## Описание

ChatManager решает проблему неуправляемых чатов, создаваемых разными людьми. Система обеспечивает:

- **Централизованное создание чатов** через единую точку входа (Control Bot)
- **Автоматическое управление** через UserBot (создание групп, генерация invite links)
- **Разделение ролей** (admin/manager/member) с разными правами доступа
- **Прозрачность** - все данные в Google Sheets для полного контроля
- **AI-ready архитектура** - легко интегрировать AI-модерацию, саммари, авто-ответы

## Архитектура

Система состоит из трех компонентов:

### 1. Control Bot (python-telegram-bot)
Интерфейс для пользователей:
- Запрос на создание чата через удобное меню
- Просмотр своих чатов
- Получение invite-ссылок

### 2. UserBot (Pyrogram)
Работает от аккаунта-администратора:
- Создание групповых чатов
- Генерация invite links
- Назначение администраторов (опционально)

### 3. Google Sheets
Единое хранилище данных:
- **Пользователи**: telegram_id, имя, роль, статус
- **Чаты**: id, название, создатель, статус, invite_link
- **Участники**: chat_id, user_id, роль в чате

## Workflow

```
Пользователь → Control Bot → Google Sheets → UserBot → Telegram API
     ↓              ↓              ↑              ↓
  /new_chat    Запись запроса  Polling     Создание чата
     ↓              ↓           (10 сек)        ↓
  Ввод данных  Статус: pending    ↓         Invite link
     ↓              ↓              ↓              ↓
  Подтверждение    ↓         Обновление   Статус: created
     ↓              ↓              ↓              ↓
  "Ожидайте..."    ↓              ↓         → Google Sheets
     ↓              ←──────────────┴──────────────┘
  Получение ссылки (через /my_chats)
```

## Быстрый старт (MVP за 20 минут)

### Шаг 1: Клонирование и зависимости (3 мин)

```bash
cd Projects/ChatManager

# Создать виртуальное окружение (опционально)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 2: Настройка Google Sheets (5 мин)

См. подробную инструкцию: [`docs/GOOGLE_SHEETS_SETUP.md`](docs/GOOGLE_SHEETS_SETUP.md)

Кратко:
1. Создать Google Sheets таблицу
2. Создать 3 листа: "Пользователи", "Чаты", "Участники"
3. Настроить Service Account
4. Дать доступ к таблице
5. Добавить себя в лист "Пользователи" с ролью `admin`

### Шаг 3: Получение токенов (7 мин)

#### Control Bot Token:
1. Написать @BotFather в Telegram
2. Отправить `/newbot`
3. Следовать инструкциям
4. Скопировать токен

#### UserBot API credentials:
1. Перейти на https://my.telegram.org/apps
2. Войти в свой Telegram аккаунт
3. Создать приложение
4. Скопировать `api_id` и `api_hash`

**ВАЖНО:** Используйте ОТДЕЛЬНЫЙ аккаунт Telegram для UserBot, не основной!

### Шаг 4: Конфигурация (2 мин)

Скопировать `.env.example` в `.env` и заполнить:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
USERBOT_API_ID=ваш_api_id
USERBOT_API_HASH=ваш_api_hash
USERBOT_SESSION=chat_admin
GOOGLE_SHEETS_ID=id_вашей_таблицы
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
```

Положить `service_account.json` в папку проекта.

### Шаг 5: Запуск (3 мин)

**Терминал 1 - Control Bot:**
```bash
python bot.py
```

**Терминал 2 - UserBot:**
```bash
python userbot.py
```

При первом запуске UserBot запросит:
- Номер телефона
- Код подтверждения из Telegram
- Пароль 2FA (если включен)

После авторизации создастся файл `chat_admin.session` - при следующих запусках авторизация не требуется.

### Шаг 6: Тестирование

1. Открыть бота в Telegram
2. Отправить `/start`
3. Отправить `/new_chat`
4. Ввести название чата
5. Ввести описание (или `-` чтобы пропустить)
6. Подтвердить создание
7. Подождать 10-30 секунд
8. Отправить `/my_chats` - получить invite link

## Команды бота

### Для всех пользователей:
- `/start` - Запуск бота и информация
- `/help` - Справка по командам
- `/my_chats` - Список ваших чатов

### Для admin и manager:
- `/new_chat` - Создать запрос на новый чат
- `New Chat` (кнопка меню)

## Роли пользователей

### Admin
- Создание неограниченного числа чатов
- Просмотр всех чатов (опционально)
- Управление пользователями (опционально)

### Manager
- Создание чатов для своей команды
- Просмотр только своих чатов

### Member
- Просмотр чатов, где является участником
- Не может создавать чаты

Роли настраиваются в листе "Пользователи" в Google Sheets.

## Структура проекта

```
Projects/ChatManager/
├── README.md                  # Этот файл
├── requirements.txt           # Зависимости Python
├── .env.example              # Пример конфигурации
├── .env                      # Конфигурация (не коммитить!)
├── service_account.json      # Service Account ключ (не коммитить!)
├── chat_admin.session        # Сессия UserBot (не коммитить!)
├── config.py                 # Конфигурация и константы
├── bot.py                    # Control Bot (главный файл)
├── userbot.py                # UserBot (Pyrogram)
├── sheets.py                 # Работа с Google Sheets
├── handlers/
│   ├── __init__.py
│   ├── start.py             # /start, /help
│   ├── menu.py              # Главное меню
│   └── chat_request.py      # Создание запроса на чат
├── utils/
│   ├── __init__.py
│   └── auth.py              # Декораторы авторизации
└── docs/
    └── GOOGLE_SHEETS_SETUP.md  # Настройка Google Sheets
```

## Настройки конфигурации

Можно кастомизировать в `config.py` или через `.env`:

```python
# Интервал проверки Google Sheets UserBot'ом (секунды)
CHAT_POLL_INTERVAL = 10

# Требуется ли одобрение запросов (False = авто-создание)
REQUIRE_APPROVAL = False

# Права участников чата по умолчанию
DEFAULT_CHAT_PERMISSIONS = {
    'can_send_messages': True,
    'can_send_media': True,
    'can_invite_users': False,
    ...
}
```

## Расширение функционала (Post-MVP)

Система спроектирована для легкого расширения:

### 1. Назначение администраторов в чатах
```python
# В userbot.py добавить:
await app.promote_chat_member(
    chat_id,
    user_id,
    privileges=ChatPrivileges(...)
)
```

### 2. AI-модерация
- Webhook от Control Bot → обработка сообщений через Claude API
- Авто-ответы на частые вопросы
- Генерация саммари встреч
- Уведомления о важных событиях

### 3. Мониторинг активности
- UserBot слушает события в чатах
- Запись статистики в новый лист "Активность"
- Отчеты по активности чатов

### 4. Архивация чатов
```python
# Добавить команду /archive_chat
# UserBot архивирует чат, обновляет статус в Sheets
```

### 5. Интеграция с ClickUp
- Создание задачи в ClickUp при создании чата
- Синхронизация участников
- Автоматическое обновление статусов

## Безопасность

### Требования к аккаунту-администратору:

⚠️ **КРИТИЧНО:** Используйте ОТДЕЛЬНЫЙ Telegram аккаунт для UserBot!

- Telegram может ограничить аккаунт при подозрении на спам
- Рекомендуется использовать "прогретый" аккаунт (старый, с историей)
- Не создавайте > 10 чатов в час (риск флудвейта)
- Храните `chat_admin.session` в безопасности

### Что НЕ коммитить в Git:

- `.env` - токены и секреты
- `service_account.json` - ключ Google Service Account
- `chat_admin.session` - сессия UserBot

Эти файлы уже добавлены в `.gitignore`.

## Troubleshooting

### UserBot не авторизуется
- Проверьте `USERBOT_API_ID` и `USERBOT_API_HASH` в `.env`
- Убедитесь, что аккаунт не заблокирован
- Попробуйте удалить `chat_admin.session` и авторизоваться заново

### Control Bot не реагирует
- Проверьте, что ваш Telegram ID добавлен в лист "Пользователи"
- Убедитесь, что статус `active`, а не `blocked`
- Проверьте логи бота: `python bot.py`

### Чаты не создаются
- Проверьте логи UserBot: должно быть "Logged in as..."
- Убедитесь, что в листе "Чаты" есть запросы со статусом `pending`
- Проверьте, что UserBot имеет права на создание групп (не все аккаунты)

### Ошибка FloodWait
- UserBot превысил лимит запросов
- Увеличьте `CHAT_POLL_INTERVAL` в `.env`
- Подождите время, указанное в ошибке

## Деплой на VPS

Для развертывания на сервере:

1. Скопировать файлы на VPS
2. Настроить systemd services (как в FinanceBot)
3. Запустить оба процесса как демоны

Пример systemd service:

```ini
[Unit]
Description=ChatManager Control Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/ChatManager
ExecStart=/path/to/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Аналогично для UserBot: `chatmanager-userbot.service`

## Принципы децентрализованной архитектуры

Система следует принципам из [`Documentation/DECENTRALIZED_ARCHITECTURE_PRINCIPLES.md`](../../Documentation/DECENTRALIZED_ARCHITECTURE_PRINCIPLES.md):

- **Разделение ролей**: каждый пользователь делает свою работу
- **Минимум информации**: manager видит только свои чаты
- **Единый источник данных**: Google Sheets для полной прозрачности
- **Масштабируемость**: легко добавить новые роли и функции

## Связанные проекты

- **FinanceBot** (`Projects/FinanceBot/`) - референс архитектуры
- **VoiceBot** (`Projects/VoiceBot/`) - пример AI-интеграции

## Лицензия

Внутренний проект. Не для публичного использования.

## Авторы

- Архитектура: по аналогии с FinanceBot
- Реализация: ChatManager MVP

---

**Версия:** 1.0.0
**Дата:** 08.02.2026
**Статус:** MVP Ready (20 минут до запуска)

## Быстрая проверка готовности

- [ ] Установлены зависимости (`pip install -r requirements.txt`)
- [ ] Создана Google Sheets таблица с 3 листами
- [ ] Настроен Service Account и дан доступ
- [ ] Получен Bot Token от @BotFather
- [ ] Получены UserBot credentials с my.telegram.org
- [ ] Заполнен `.env` файл
- [ ] Добавлен тестовый пользователь в "Пользователи"
- [ ] Запущен Control Bot (`python bot.py`)
- [ ] Запущен UserBot (`python userbot.py`)
- [ ] Протестирован `/new_chat` в боте

Если все ✅ - система готова к работе!
