# Получение UserBot Credentials

## Шаг 1: Получить API_ID и API_HASH

1. Открой в браузере: https://my.telegram.org/apps
2. Войди в аккаунт Telegram (который будет создавать чаты)
   - Введи номер телефона
   - Введи код из Telegram
   - Если есть 2FA - введи пароль

3. На странице "API development tools" заполни форму:
   - App title: `ChatManager` (любое название)
   - Short name: `chatmanager` (любое)
   - Platform: `Desktop` (или Other)
   - Description: `Chat management bot` (любое)

4. Нажми "Create application"

5. Скопируй данные:
   ```
   api_id: 12345678 (число)
   api_hash: abcdef1234567890abcdef1234567890 (строка)
   ```

## Шаг 2: Обновить .env

Открой файл `.env` и заполни:
```env
USERBOT_API_ID=твой_api_id_сюда
USERBOT_API_HASH=твой_api_hash_сюда
```

## Шаг 3: Авторизовать UserBot

После того как заполнишь .env, запусти:

```bash
cd Projects/ChatManager
python setup_userbot.py
```

Скрипт запросит:
1. **Phone number** - введи номер телефона аккаунта (с кодом страны, например: +79123456789)
2. **Confirmation code** - получишь код в Telegram, введи его
3. **2FA password** - если включена двухфакторная аутентификация

После успешной авторизации создастся файл `chat_admin.session` - это сессия UserBot.
В следующий раз авторизация не потребуется.

## Проверка

Запусти UserBot:
```bash
python userbot.py
```

Должно быть:
```
Logged in as: Твоё Имя (@username, ID: 123456789)
Starting polling loop (interval: 10s)
```

Если видишь это - всё работает!

---

**Важно:**
- Храни .env и *.session файлы в секрете
- Не коммить их в Git (уже в .gitignore)
- Используй отдельный аккаунт если возможно
