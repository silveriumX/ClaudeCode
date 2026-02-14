---
name: openai-json-extraction
description: Get reliable JSON from OpenAI API for "text to structured fields". Use chat models (gpt-4.1-mini, gpt-4o-mini), not reasoning models; set temperature, max_tokens, response_format. Use when extracting structured data from text/documents, or when API returns empty content or 400.
---

# Надёжное получение JSON из OpenAI

## Правила

### 1. Выбор модели

- Для задачи «текст → JSON» использовать **обычные chat-модели**: gpt-4.1-mini, gpt-4o-mini и т.п. Они поддерживают `temperature`, `max_tokens` и стабильно возвращают `content`.
- **Reasoning-модели** (o1, o3) часто не поддерживают `temperature` и могут отдавать **пустой** `message.content` при ограничении по токенам (все токены уходят на «думание»). Для extraction их не использовать.

### 2. Параметры запроса

- `temperature=0.1` (или низкое) — для предсказуемого вывода.
- `max_tokens` — для обычных chat-моделей; у части новых моделей параметр называется `max_completion_tokens` — проверять документацию API.
- При поддержке: `response_format={"type": "json_object"}` — чтобы ответ был в виде JSON.

### 3. Промпт

- В системном промпте явно перечислить **все поля JSON** и их смысл. Указать: не выдумывать данные; если поле неизвестно — вернуть пустую строку `""`. При необходимости зафиксировать формат даты (например ДД.ММ.ГГГГ).

### 4. Парсинг ответа

- Допускать обёртку в markdown: ответ может быть вида `` ```json ... ``` ``. Перед `json.loads()` снять обёртку (удалить первую/последнюю строки с ```).
- Если `message.content` пустой — залогировать и не падать; вернуть пустой результат или значения по умолчанию.
