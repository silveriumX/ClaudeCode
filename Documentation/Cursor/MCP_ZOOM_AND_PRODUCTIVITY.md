# MCP: Zoom, Cursor и полезные серверы для жизни и работы

Руководство по настройке MCP-интеграции Zoom с Cursor и обзор MCP-серверов, превращающих Cursor в «операционную систему» для продуктивности.

---

## 1. Zoom + Cursor — пошаговая настройка

### Что даёт Zoom MCP

- **get_meetings** — список активных встреч Zoom
- **create_meeting** — создание встречи
- **update_meeting** — изменение встречи
- **delete_meeting** — удаление встречи

Управление встречами можно делать прямо из чата Cursor («создай встречу на завтра в 15:00», «покажи мои встречи» и т.д.).

### Шаг 1. Приложение в Zoom Marketplace

1. Откройте [Zoom Marketplace](https://marketplace.zoom.us/).
2. **Develop** → **Build App** → выберите **Server to Server OAuth App**.
3. Заполните название и данные приложения.
4. **Add Scopes** — добавьте права для работы с встречами (см. ниже).
5. Активируйте приложение (**Activate**).
6. На странице **App Credentials** скопируйте:

#### Add Scopes — какие права включить (точные имена в интерфейсе Zoom)

В диалоге **Add Scopes** Zoom показывает **гранулярные** scopes (не просто `meeting:read` / `meeting:write`). Нужны scopes из категории **Meetings** (левая панель — Product: Meetings).

**1. Просмотр встреч (get_meetings, детали встречи)**
В поиске введите **meeting:read** и отметьте:

| Отображаемое название | Scope (точное имя) |
|------------------------|--------------------|
| **View a meeting**     | **meeting:read:meeting:admin** |
| или (если нужны только свои встречи) | **meeting:read:meeting:master** |

*Не путать с:* `meeting:read:past_qa:admin` (Q&A), `meeting:read:risk_alert:admin` (риски) — для MCP не нужны.

**2. Создание / изменение / удаление встреч (create_meeting, update_meeting, delete_meeting)**
Очистите поиск или введите **meeting:write** и отметьте scope для создания/изменения встреч:

| Отображаемое название | Scope (точное имя) |
|------------------------|--------------------|
| **Create a meeting** / **Update a meeting** / аналог | **meeting:write:meeting:admin** |
| или только свои встречи | **meeting:write:meeting:master** |

Прокрутите список вниз («Scroll for more»), если нужного пункта не видно.

**Итого для Zoom MCP отметьте:**
- **meeting:read:meeting:admin** — просмотр встреч
- **meeting:write:meeting:admin** — создание, изменение, удаление встреч

(Варианты с **:master** — если приложение работает только от имени одного пользователя.)

После выбора нажмите **Done** и сохраните приложение.

*Соответствует [Zoom Developer APIs](https://developers.zoom.us/docs/api/), [Meetings APIs](https://developers.zoom.us/docs/api/meetings/), гранулярным scopes в Add Scopes.*

В п. 6 выше скопируйте: **Account ID**, **Client ID**, **Client Secret**.

### Шаг 2. Конфигурация в Cursor

В `.cursor/mcp.json` (в корне проекта или в `C:\Users\Admin\.cursor\mcp.json`) добавьте блок `zoom`:

```json
"zoom": {
  "command": "npx",
  "args": ["-y", "@prathamesh0901/zoom-mcp-server"],
  "env": {
    "ZOOM_ACCOUNT_ID": "ваш_account_id",
    "ZOOM_CLIENT_ID": "ваш_client_id",
    "ZOOM_CLIENT_SECRET": "ваш_client_secret"
  }
}
```

Подставьте свои значения из Zoom Marketplace. Не коммитьте секреты в репозиторий — используйте переменные окружения или локальный `mcp.json`, добавленный в `.gitignore`.

### Шаг 3. Перезапуск Cursor

После сохранения `mcp.json` полностью перезапустите Cursor. В чате в разделе **Available Tools** должны появиться инструменты Zoom (`get_meetings`, `create_meeting` и т.д.).

### Проверка подключения и функции Zoom MCP

**Как проверить, что Zoom MCP работает**

1. Перезапустите Cursor (если только что добавили конфиг).
2. Откройте чат с AI (Ctrl+L).
3. Справа в **Available Tools** найдите инструменты с префиксом **zoom** или названиями: `get_meetings`, `create_meeting`, `update_meeting`, `delete_meeting`.
4. Напишите в чате: **«Покажи мои активные встречи Zoom»** или **«Используй Zoom MCP: get_meetings»**. AI вызовет инструмент и вернёт список встреч (или «No active meetings»).

Если инструменты Zoom не видны — откройте **Cursor Settings → MCP** и проверьте, что сервер **zoom** в статусе подключён (зелёный). Логи MCP: `%APPDATA%\Cursor\logs\[дата]\...\MCP Logs.log`.

**Доступные инструменты (4 шт.)**

| Инструмент | Описание | Параметры |
|------------|----------|-----------|
| **get_meetings** | Список всех активных встреч Zoom | Нет (пустой вызов) |
| **create_meeting** | Создать новую встречу | `topic` (название), `start_time` (время начала), `timezone` (часовой пояс), `duration` (длительность в минутах), `agenda` (описание/повестка) |
| **update_meeting** | Изменить существующую встречу | `id` (ID встречи), `topic`, `start_time`, `duration`, `timezone`, `agenda` |
| **delete_meeting** | Удалить встречу | `id` (ID встречи) |

**Примеры фраз в чате**

- «Покажи мои встречи Zoom» → вызовет `get_meetings`.
- «Создай встречу Zoom завтра в 15:00 на 1 час, тема "Синхронизация", описание "Обсудить задачи"» → AI подставит параметры и вызовет `create_meeting` (в т.ч. timezone по умолчанию).
- «Удали встречу Zoom с ID 123456789» → вызовет `delete_meeting` с `id: "123456789"`.
- «Измени встречу Zoom [ID]: новая тема и время» → вызовет `update_meeting`.

Формат **start_time** в Zoom API — обычно ISO 8601 или `YYYY-MM-DDTHH:mm:ss` (уточняется сервером). AI подставит корректный формат при создании/обновлении.

**Получение персональной конференции (Personal Meeting Room / PMI)**

Для получения ссылки на вашу постоянную персональную конференцию Zoom:

1. **Через Cursor чат (рекомендуется):**
   Напишите: **«Покажи мои встречи Zoom»** или **«Используй Zoom: get_meetings»**.
   В списке найдите встречу с типом "Personal Meeting Room" или постоянную встречу — там будет `join_url` и `password`.

2. **Вручную через веб-интерфейс:**
   Откройте [Zoom Profile](https://zoom.us/profile) → найдите раздел **"Personal Meeting ID"** → скопируйте ссылку и пароль.

3. **Сохранить для быстрого доступа:**
   Данные можно сохранить в `Data/zoom_personal_meeting.txt` (шаблон уже создан).
   Или добавьте ссылку в закладки браузера.

**Примечание:** Для автоматического получения PMI через API может потребоваться дополнительный scope `meeting:read:list_meetings:admin` в Zoom Marketplace (если `get_meetings` не возвращает список).

### Связка Zoom и Fireflies (у вас уже есть)

- **Zoom** — создание/управление встречами.
- **Fireflies** — транскрипция и саммари уже проведённых встреч.

Вместе это даёт полный цикл: создание встречи → проведение в Zoom → разбор по транскрипту в Cursor через Fireflies.

**Fireflies и повторяющаяся персональная конференция (PMI в календаре)**

Если у вас в календаре запланирована **персональная конференция Zoom как повторяющееся событие** (каждый день и т.д.) и интеграция Fireflies + Zoom настроена:

- **Да, Fireflies будет подключаться автоматически** к каждому такому событию, если:
  1. В приглашении календаря есть **ссылка на Zoom** (ваша PMI-ссылка).
  2. У Fireflies подключён **календарь** (Google Calendar, Outlook и т.д.) — Fireflies смотрит события в календаре и по ссылке определяет встречу Zoom.
  3. В настройках Zoom разрешён вход Fireflies (ожидающая комната выключена или Fred одобрен; при интеграции Zoom с Fireflies Fred обычно входит без запроса).

Пароль встречи должен быть **включён в ссылку** (например, `?pwd=...`), чтобы Fireflies мог зайти без ручного ввода. Ваша PMI-ссылка из `Data/zoom_personal_meeting.txt` уже содержит пароль в URL — этого достаточно.

Итого: при повторяющемся событии в календаре с одной и той же Zoom-ссылкой (PMI) Fireflies будет автоматически подключаться к этой встрече каждый раз, когда она по расписанию начнётся.
Подробнее: [How to integrate Zoom with Fireflies](https://guide.fireflies.ai/articles/8956173738-how-to-integrate-zoom-with-fireflies), [Auto-join and Email Recap](https://guide.fireflies.ai/articles/1605971414-learn-about-the-fireflies-auto-join-and-email-recap-settings).

---

## 2. Полезные MCP-серверы для «жизни и работы» в Cursor

Ниже — серверы по категориям. Конфиг добавляется в тот же `.cursor/mcp.json` в блок `mcpServers`.

### Календарь и почта

| Сервер | Назначение | Установка / пакет |
|--------|------------|--------------------|
| **Google Calendar MCP** | События календаря (создание, список, анализ расписания) | `google-calendar-mcp` (cursormcp.dev) |
| **Mcp Gsuite** | Gmail + Google Calendar в одном сервере | ~414 stars, популярный выбор |
| **Gmail MCP** | Просмотр, отправка, метки, саммари писем | Отдельный Gmail MCP (cursormcp.dev) |

Пример для **Gsuite** (Gmail + Calendar):

```json
"gsuite": {
  "command": "npx",
  "args": ["-y", "mcp-gsuite"],
  "env": {
    "GMAIL_CREDENTIALS_PATH": "путь к credentials.json",
    "GOOGLE_CALENDAR_ID": "ваш календарь"
  }
}
```

Точные переменные и OAuth — в README соответствующего репозитория (обычно Google Cloud Project + OAuth 2.0).

### Задачи и проекты (у вас уже есть ClickUp)

| Сервер | Назначение |
|--------|------------|
| **Todoist** | Задачи, проекты, напоминания (~290 stars) |
| **Notion** | Страницы, базы, заметки — поиск, чтение, создание, обновление |
| **TickTick** | Задачи и автоматизация |
| **Trello** | Доски и карточки |
| **Plane** | Проекты и issues |

Пример **Todoist**:

```json
"todoist": {
  "command": "npx",
  "args": ["-y", "todoist-mcp-server"],
  "env": {
    "TODOIST_API_TOKEN": "ваш_токен"
  }
}
```

Токен: Todoist → Settings → Integrations → API token.

### Документы и заметки

| Сервер | Назначение |
|--------|------------|
| **Notion** | Официальная/community интеграция — страницы и базы |
| **Office Word MCP** | Создание и правка .docx (~459 stars) |
| **OneNote** | Блокноты и страницы через Microsoft Graph |
| **Slidespeak** | Презентации (PowerPoint через API) |

### Связь и коммуникация

| Сервер | Назначение |
|--------|------------|
| **Zoom** | Встречи (см. выше) |
| **Fireflies** | Транскрипты встреч (уже подключены) |
| **Slack** | Через Zapier MCP или нативные MCP для Slack |
| **Mattermost** | Каналы и сообщения |

### Универсальная автоматизация

| Сервер | Назначение |
|--------|------------|
| **Zapier MCP** | Подключение к тысячам приложений (календарь, почта, Slack, CRM и т.д.) одним MCP |

Полезно, когда нужна одна точка входа к разным сервисам без отдельного MCP под каждый.

### Файлы и система (у вас уже есть)

| Сервер | Назначение |
|--------|------------|
| **filesystem** | Файлы и папки (уже в `mcp.json`) |
| **document-processor** | Обработка PDF/DOCX и т.д. (уже настроен) |

---

## 3. Рекомендуемый минимальный набор «Cursor как ОС»

Для повседневной работы и жизни разумно иметь:

1. **Zoom** — встречи.
2. **Fireflies** — разбор встреч (уже есть).
3. **ClickUp** — задачи и проекты (уже есть).
4. **Filesystem** — файлы (уже есть).
5. **Один из** Google Calendar / Gsuite / Gmail — календарь и почта.
6. **По желанию:** Notion или Todoist — заметки и личные задачи.
7. **По желанию:** Zapier MCP — если нужны десятки приложений без отдельных MCP.

Дальше можно добавлять Word, OneNote, Slack и т.д. по мере необходимости.

---

## 4. Где искать серверы и конфиги

- **Каталог:** [cursormcp.dev](https://cursormcp.dev/) — категории Communication, Workplace & Productivity и др.
- **Официальная документация Cursor:** [cursor.com/docs/context/mcp](https://cursor.com/docs/context/mcp).
- **Zoom MCP:** [GitHub — Prathamesh0901/zoom-mcp-server](https://github.com/Prathamesh0901/zoom-mcp-server), npm: `@prathamesh0901/zoom-mcp-server`.

---

## 5. Безопасность

- Не храните **ZOOM_CLIENT_SECRET**, **TODOIST_API_TOKEN**, OAuth-ключи и т.п. в публичном репозитории.
- Используйте локальный `mcp.json` и/или переменные окружения.
- При необходимости добавьте `.cursor/mcp.json` в `.gitignore` или храните только шаблон без секретов.

---

## 6. Проверка работы

После добавления любого MCP:

1. Перезапустить Cursor.
2. Открыть чат (Ctrl+L).
3. В **Available Tools** найти новые инструменты (например, `get_meetings` для Zoom).
4. Дать команду в чате: «Покажи мои встречи Zoom» / «Создай встречу завтра в 10:00» и т.д.

Если инструменты не появляются — проверить логи MCP:
`C:\Users\Admin\AppData\Roaming\Cursor\logs\[дата]\window1\exthost\anysphere.cursor-mcp\MCP Logs.log`.

---

*Документ создан 28.01.2026. Актуальность конфигов и пакетов лучше периодически сверять с cursormcp.dev и GitHub.*
