# Почему не работает инструмент Task (делегирование субагентам)

**Дата:** 2026-01-29
**Суть:** Инструмент Task отсутствует в списке инструментов агента или виден, но не вызывается — делегирование кастомным субагентам (например verifier) недоступно.

---

## 1. Корневая причина (вывод из форума и кода)

### 1.1 Разрыв между промптом и набором инструментов

- В системный промпт агента **подставляется** контекст делегирования: `<<subagent_delegation_context>>` с инструкцией использовать `Task(subagent_type="verifier", prompt="...")`.
- В **набор инструментов** агента (toolset), который реально передаётся модели, инструмент **Task не добавляется** или добавляется, но вызов блокируется.

Цитата с форума Cursor (пользователь Guillaume Costanza):

> "The subagent delegation context mentioned in the system prompt is guidance for how to delegate, but **the actual Task tool doesn't exist in this environment**."

То есть модель **инструктируют** вызывать Task, но **инструмента Task у неё нет** — это баг/недоведённая реализация на стороне Cursor.

### 1.2 Аналогичный баг в Claude Code (Anthropic)

В репозитории **anthropics/claude-code** описан тот же класс проблемы ([issue #9865](https://github.com/anthropics/claude-code/issues/9865)):

- Task tool берёт список агентов из внутреннего массива `activeAgents`.
- В `activeAgents` попадают **только встроенные** агенты (general-purpose, Explore и т.д.).
- Кастомные агенты из параметра `--agents` и из файловой системы (`.claude/agents/*.md`) **не добавляются** в этот массив.
- Итог: Task tool «не видит» кастомных агентов и при вызове выдаёт ошибку «Agent type 'X' not found».

**Вывод:** Ошибка в **пайплайне загрузки агентов**: кастомные агенты не попадают в список, который использует Task. В Cursor ситуация может быть ещё жёстче: в части сборок Task **вообще не регистрируется** в toolset (см. ниже).

---

## 2. Что наблюдают пользователи (форум Cursor, январь 2026)

| Сборка / версия              | Task в списке инструментов | Вызов Task работает |
|-----------------------------|----------------------------|----------------------|
| Early Access 2.4.21 (Stable)| **Нет**                    | Нет                  |
| Nightly 2.5                 | **Да**                     | **Нет** (не вызывается) |

Источники:

- [SubAgent invocation not working (Early Access / Nightly)](https://forum.cursor.com/t/subagent-invocation-not-working-anymore-on-most-recent-nightly-and-early-access-builds/149987)
- [Task Tool Missing for Custom Agents](https://forum.cursor.com/t/task-tool-missing-for-custom-agents-in-cursor-agents-documentation-pages-return-errors/149771)
- [Task tool not found](https://forum.cursor.com/t/task-tool-not-found/149379)

Отсюда две возможные причины на стороне Cursor:

1. **Task не регистрируется в toolset** (Early Access 2.4.21) — кастомные субагенты из `.cursor/agents/` не приводят к появлению инструмента Task.
2. **Task регистрируется, но вызов отключён или падает** (Nightly 2.5) — ошибка в активации/разрешениях/обработчике инструмента.

В обоих случаях это **не настройки пользователя**, а поведение текущих сборок.

---

## 3. Что не является причиной (уже проверено пользователями)

- **План:** на usage-based плане субагенты должны быть «по умолчанию» — при этом Task всё равно отсутствует или не работает.
- **Max Mode:** включали — без изменений.
- **Режим:** Agent (не Ask) — Task по-прежнему недоступен.
- **Файлы субагентов:** `.cursor/agents/verifier.md` с frontmatter `name`, `description` есть; контекст делегирования в промпт подставляется, но инструмента нет.

То есть причина — **в коде/конфигурации Cursor**, а не в локальной настройке проекта или аккаунта.

---

## 4. Техническая гипотеза (объяснение «почему»)

1. **Регистрация инструментов:**
   В части сборок код, который должен добавлять Task в toolset агента при наличии субагентов (или при включённой фиче), не срабатывает или отключён (feature flag, план, тип сессии).

2. **Загрузка кастомных агентов:**
   Даже если Task в toolset есть (Nightly), список агентов для Task может браться только из встроенных имён; кастомные агенты из `.cursor/agents/` не подмешиваются в «activeAgents» (аналогично [claude-code #9865](https://github.com/anthropics/claude-code/issues/9865)).

3. **Результат:**
   Модель получает инструкцию «используй Task», но либо не имеет инструмента Task, либо при вызове Task получает ошибку «agent not found» или отказ в выполнении.

---

## 5. Что делать пока Task не работает

1. **Проверять обновления Cursor** — в новых версиях баг могут починить.
2. **Отслеживать баг-репорты** на [forum.cursor.com](https://forum.cursor.com) (теги subagents, Task tool) и ответы команды Cursor.
3. **Обходной путь:** явно просить агента выполнить проверку по инструкциям из `.cursor/agents/verifier.md` — без вызова Task, в том же чате.

---

## 6. Ссылки

- [Subagents | Cursor Docs](https://cursor.com/docs/context/subagents)
- [Cursor 2.4 Changelog (Subagents)](https://cursor.com/changelog/2-4)
- [SubAgent invocation not working (forum)](https://forum.cursor.com/t/subagent-invocation-not-working-anymore-on-most-recent-nightly-and-early-access-builds/149987)
- [Task Tool Missing for Custom Agents (forum)](https://forum.cursor.com/t/task-tool-missing-for-custom-agents-in-cursor-agents-documentation-pages-return-errors/149771)
- [Task tool cannot find custom agents — Claude Code #9865](https://github.com/anthropics/claude-code/issues/9865)
