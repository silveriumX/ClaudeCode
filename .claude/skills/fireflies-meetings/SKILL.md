---
name: fireflies-meetings
description: Транскрипция и обработка встреч через Fireflies — саммари, экшены, поиск по встречам и автоматическое добавление задач в план.
---

# Fireflies: транскрипты встреч и автоматизация

## Что делать по шагам

1. **Проверить MCP Fireflies**
   - В MCP конфигурации должен быть сервер `fireflies` с URL `https://api.fireflies.ai/mcp`.
   - В заголовках должен быть подставлен реальный API key.

2. **Выбрать инструменты MCP:**
   - Поиск по встречам: `fireflies_search` или `fireflies_get_transcripts`
   - По одной встрече: `fireflies_get_summary` (саммари + экшены), `fireflies_get_transcript` (полный текст), `fireflies_fetch` (всё разом)

3. **Выдать результат в едином формате:**
   - Краткий саммари (2–4 предложения)
   - Список action items с ответственным
   - Ключевые темы/решения

4. **Интеграция с задачами:**
   - Если пользователь просит «добавить в план» / «вытащить задачи»:
     - Взять action items из ответа Fireflies
     - Добавить в актуальный `Work/Задачи/План на ДД.ММ.ГГГГ.md`
     - Обновить `АКТУАЛЬНЫЕ_ЗАДАЧИ.md`

---

## Получение API key

1. Войти на app.fireflies.ai
2. **Integrations** → **Fireflies API** (или **Settings** → **Developer Settings**)
3. Скопировать API key и вставить в MCP конфигурацию: `Authorization: Bearer YOUR_FIREFLIES_API_KEY`

**Важно:** не коммитить реальный ключ в репозиторий.

## Связанные файлы

- `/daily-plan` — добавление action items в план
- `.claude/rules/task-management.md` — система задач
