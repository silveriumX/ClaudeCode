# Пошаговая инструкция по запуску системы

## Предварительные требования

1. **Node.js** (версия 18 или выше)
   - Скачать: https://nodejs.org/
   - Проверить установку: `node --version`

2. **PostgreSQL** (версия 14 или выше)
   - Скачать: https://www.postgresql.org/download/
   - Или использовать облачную БД (например, ElephantSQL)

3. **Telegram Bot Token**
   - Откройте [@BotFather](https://t.me/BotFather) в Telegram
   - Отправьте `/newbot`
   - Следуйте инструкциям, получите токен

4. **Google Cloud аккаунт**
   - Регистрация: https://console.cloud.google.com/

## Шаг 1: Установка зависимостей

```bash
cd Projects/FinanceSystem
npm install
```

## Шаг 2: Настройка Google Sheets

Следуйте инструкциям в файле [GOOGLE_SHEETS_SETUP.md](./GOOGLE_SHEETS_SETUP.md)

## Шаг 3: Настройка базы данных

### Вариант А: Локальная PostgreSQL

1. Установите PostgreSQL
2. Создайте базу данных:

```sql
CREATE DATABASE finance_system;
```

3. Ваш DATABASE_URL будет:
```
postgresql://postgres:your_password@localhost:5432/finance_system
```

### Вариант Б: Облачная БД (ElephantSQL)

1. Зарегистрируйтесь на https://www.elephantsql.com/
2. Создайте новый инстанс (Free Tiny Turtle план)
3. Скопируйте URL подключения

## Шаг 4: Настройка переменных окружения

1. Скопируйте файл с примером:

```bash
copy .env.example .env
```

2. Откройте `.env` и заполните все значения:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Google Sheets API
GOOGLE_SERVICE_ACCOUNT_EMAIL=finance-bot@your-project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="[PRIVATE_KEY_PLACEHOLDER]
MAIN_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
PAYROLL_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/finance_system

# Owner Telegram ID
OWNER_TELEGRAM_ID=123456789

# Manager+ Limit
MANAGER_PLUS_LIMIT=10000
```

**Важно:**
- `TELEGRAM_BOT_TOKEN` - получите у @BotFather
- `OWNER_TELEGRAM_ID` - ваш Telegram ID (получите у @userinfobot)
- `GOOGLE_PRIVATE_KEY` - скопируйте ВЕСЬ ключ из JSON файла, включая `\n`

## Шаг 5: Инициализация базы данных

```bash
npm run dev
```

При первом запуске система автоматически создаст все необходимые таблицы.

## Шаг 6: Регистрация пользователей

После запуска бота нужно зарегистрировать первого пользователя (владельца).

Это делается вручную через базу данных:

```sql
INSERT INTO users (telegram_id, username, full_name, role)
VALUES (123456789, 'your_username', 'Ваше Имя', 'owner');
```

Замените:
- `123456789` - на ваш Telegram ID (из @userinfobot)
- `your_username` - на ваш @username в Telegram
- `Ваше Имя` - на ваше имя

## Шаг 7: Тестирование

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Вы должны увидеть приветственное сообщение
5. Отправьте `/help` - должен показать список команд

## Шаг 8: Добавление других пользователей

Используйте SQL для добавления пользователей:

```sql
-- Менеджер
INSERT INTO users (telegram_id, username, full_name, role, company)
VALUES (987654321, 'manager_ivan', 'Иван Петров', 'manager', 'ООО Альфа');

-- Оплатитель
INSERT INTO users (telegram_id, username, full_name, role)
VALUES (555555555, 'executor_anna', 'Анна Сидорова', 'executor');

-- Зарплатный специалист
INSERT INTO users (telegram_id, username, full_name, role)
VALUES (444444444, 'payroll_olga', 'Ольга Кузнецова', 'payroll');
```

## Запуск в продакшн

### Вариант А: PM2 (рекомендуется)

1. Установите PM2:
```bash
npm install -g pm2
```

2. Соберите проект:
```bash
npm run build
```

3. Запустите:
```bash
pm2 start dist/index.js --name finance-bot
pm2 save
pm2 startup
```

### Вариант Б: Systemd (Linux)

1. Создайте файл `/etc/systemd/system/finance-bot.service`:

```ini
[Unit]
Description=Finance Management Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/FinanceSystem
ExecStart=/usr/bin/node dist/index.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

2. Запустите:
```bash
sudo systemctl enable finance-bot
sudo systemctl start finance-bot
```

## Проверка работоспособности

Чеклист:

- [ ] Бот отвечает на `/start` и `/help`
- [ ] Владелец видит команды для своей роли
- [ ] Менеджер может создать заявку (следующий этап разработки)
- [ ] Данные записываются в Google Sheets (следующий этап)
- [ ] Балансы кошельков отображаются корректно (следующий этап)

## Troubleshooting

### Бот не запускается

**Проверьте:**
1. Правильность `TELEGRAM_BOT_TOKEN`
2. Подключение к интернету
3. Логи: проверьте вывод в консоли

### Ошибка подключения к БД

**Проверьте:**
1. Правильность `DATABASE_URL`
2. Запущена ли PostgreSQL
3. Существует ли база данных

### Ошибка Google Sheets API

**Проверьте:**
1. Включен ли Google Sheets API в проекте
2. Правильность `GOOGLE_PRIVATE_KEY` (должны быть `\n`)
3. Добавлен ли сервисный аккаунт в доступы к таблицам

### Бот не отвечает пользователю

**Проверьте:**
1. Зарегистрирован ли пользователь в БД
2. Правильно ли указан `telegram_id`
3. Логи бота в консоли

## Получение помощи

Если возникли проблемы:

1. Проверьте логи в консоли
2. Проверьте audit_log в базе данных
3. Проверьте права доступа к Google Sheets

## Следующие шаги

После успешного запуска базовой инфраструктуры можно переходить к:

1. Реализации создания заявок через Telegram
2. Одобрению заявок владельцем
3. Оплате заявок
4. Редактированию и коммуникации
5. Остальным функциям согласно плану разработки
