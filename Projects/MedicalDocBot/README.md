# MedicalDocBot

Telegram-бот для загрузки медицинских документов в Google Drive и записи в Google Таблицу. Отдельный проект от FinanceBot (можно использовать тот же или отдельный Google-аккаунт / Service Account).

---

## Версии

- **v1 (текущая):** загрузка файлов и фото в Drive + запись строки в таблицу (дата, имя файла, ссылка, Telegram ID, тип). Файлы с почты можно скачать и отправить боту; анализы — сфотографировать и отправить фото.
- **v2 (в планах):** распознавание текста (OCR) и перенос в стандартный формат документов (дата документа, тип, врач/клиника, показатели) в отдельный лист таблицы.

---

## Что нужно для работы

### Шаг 1. Создать бота в Telegram

1. Открой [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправь `/newbot`, укажи имя и username бота.
3. Скопируй выданный **токен** и сохрани (понадобится для `.env`).

### Шаг 2. Папка на Google Drive

**Вариант A — OAuth (как в FinanceBot):** обычная папка в «Мой диск». Нужны те же переменные, что и для Drive в FinanceBot: `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, `GOOGLE_DRIVE_REFRESH_TOKEN`. Папку создаёшь у себя, ID из URL папки — в `GOOGLE_DRIVE_FOLDER_ID`.

**Вариант B — только Service Account:** у SA нет квоты в обычном Drive, нужен **Общий диск (Shared Drive)**. Создать общий диск → добавить SA как «Менеджер контента» → ID корня диска в `GOOGLE_DRIVE_FOLDER_ID`.

Для обычной папки (как FinanceBot): создай папку в Drive, скопируй ID из URL:
`https://drive.google.com/drive/folders/**ЭТОТ_ID**`

### Шаг 3. Google Таблица

1. Создай новую [Google Таблицу](https://sheets.google.com).
2. Первый лист переименуй в **«Документы»** (или оставь как есть — бот будет использовать первый лист).
3. При желании добавь в первую строку заголовки:
   `Дата | Имя файла | Ссылка | Telegram ID | Username | Тип`
4. Скопируй **ID таблицы** из URL:
   `https://docs.google.com/spreadsheets/d/**ЭТОТ_ID**/edit`

### Шаг 4. Service Account в Google Cloud

1. Открой [Google Cloud Console](https://console.cloud.google.com/) и выбери проект (тот же, что для FinanceBot, или новый).
2. **APIs & Services** → **Credentials** → **Create Credentials** → **Service account**.
3. Задай имя (например, `medical-doc-bot`), создай ключ: **Keys** → **Add Key** → **Create new key** → **JSON**.
4. Скачай JSON и сохрани в папку проекта как **`service_account_medical.json`** (или укажи другой путь в `.env`).
5. Включи API: **APIs & Services** → **Library** → включи **Google Drive API** и **Google Sheets API**.

### Шаг 5. Доступ

- **OAuth:** один раз получить refresh token (как в FinanceBot, см. docs по Drive OAuth). Таблицу — «Поделиться» с email из `service_account_medical.json` (Редактор) для записи лога.
- **Только SA:** общий диск — добавить SA как Менеджер контента; таблицу — «Поделиться» с SA (Редактор).

### Шаг 6. Настройка окружения

1. В папке проекта скопируй `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
2. Открой `.env` и подставь:
   - `TELEGRAM_BOT_TOKEN` — токен от BotFather
   - `GOOGLE_DRIVE_FOLDER_ID` — ID папки из шага 2
   - `GOOGLE_SHEETS_ID` — ID таблицы из шага 3
   - Путь к JSON оставь `service_account_medical.json`, если файл лежит в папке проекта.

### Шаг 7. Запуск

```bash
cd Projects/MedicalDocBot
pip install -r requirements.txt
python bot.py
```

Отправь боту в Telegram любой документ или фото — файл появится в папке Drive, в таблицу добавится строка.

---

## Таблица (лист «Документы»)

Бот дописывает строки с колонками:

| Дата       | Имя файла | Ссылка | Telegram ID | Username | Тип     |
|------------|-----------|--------|-------------|----------|---------|
| 06.02.2026 12:00 | file.pdf | https://drive.google.com/... | 123456 | @user | документ |

Тип: «документ» для отправленных файлов, «фото» для отправленных фото.

---

## Безопасность

- Файлы `service_account_medical.json` и `.env` добавлены в `.gitignore` — не коммитить.
- Токен бота храни только в `.env`. При утечке: @BotFather → твой бот → Revoke token → создай новый.

---

## Деплой на VPS (Linux 195.177.94.53 — тот же сервер, что EnglishTutorBot)

Сервер Linux; бот в **отдельной папке** `/root/medical_doc_bot` (EnglishTutorBot — в `/root/english_tutor_bot`).

**Автоматически:** из папки MedicalDocBot выполнить `python deploy_to_vps.py`. Скрипт по SSH создаёт `/root/medical_doc_bot`, заливает файлы, `.env`, `service_account_medical.json`, ставит зависимости, останавливает только процесс MedicalDocBot (`pkill -f /root/medical_doc_bot/bot.py`) и запускает бота через `nohup python3 bot.py`.

**Вручную:** `ssh root@195.177.94.53`, создать `/root/medical_doc_bot`, скопировать туда файлы проекта и `service_account_medical.json`, в `.env` указать `GOOGLE_SERVICE_ACCOUNT_FILE=service_account_medical.json`, затем `pip install -r requirements.txt` и `nohup python3 bot.py >> bot.log 2>> bot_error.log &`.

---

## Дополнительно

- Подробная настройка Google Sheets и Drive с нуля: см. в репозитории `Projects/FinanceBot/docs/GOOGLE_SHEETS_SETUP_FIRST_TIME.md` и `GOOGLE_DRIVE_SETUP_FIRST_TIME.md` (те же шаги для другого проекта).
- Документ для планов по здоровью (нос, спина, анализы, операция и т.д.): `Work/Здоровье_состояние_и_планы.md` — ведётся вручную, бот v1 туда не пишет.
