# Conclusions: Skill Graphs & Agent Knowledge Systems

> Изучены: arscontexta (249 файлов), planning-with-files (14k⭐), anthropics/skills, daymade/claude-code-skills, awesome-claude-skills

---

## Что установлено прямо сейчас

### ✅ planning-with-files — глобальный скилл
```
~/.claude/skills/planning-with-files/SKILL.md
~/.claude/settings.json  ← PreToolUse хук активен
```

**Хук делает:** перед каждым Write/Edit/Bash автоматически читает task_plan.md (первые 20 строк).
Это главный механизм — агент не теряет цель после 50+ действий.

### ✅ Репозитории клонированы как marketplace
```
~/.claude/plugins/marketplaces/arscontexta/
~/.claude/plugins/marketplaces/planning-with-files/
```

---

## Главный insight из 249 research claims arscontexta

> "LLM attention degrades as context fills. First ~40% of context window is the 'smart zone'."

Это объясняет ВСЁ:
- Почему длинные сессии деградируют — контекст заполнен
- Почему task_plan.md важен — файл не занимает context window пока не нужен
- Почему fresh context per phase (ralph) — каждая фаза в своём "smart zone"
- Почему skill graph лучше одного большого файла — агент загружает только нужные узлы

**Практический вывод:** 3 уровня памяти агента:
```
Уровень 1 — Context (volatile):  CLAUDE.md + активные rules + текущий разговор
Уровень 2 — Files (task-level):  task_plan.md + findings.md + progress.md
Уровень 3 — Vault (persistent):  arscontexta knowledge base между сессиями
```

Сейчас у тебя есть 1 и 2. Уровень 3 — следующий шаг.

---

## Как использовать прямо сейчас

### planning-with-files — для каждой задачи 3+ шагов

```bash
# В любом проекте, начало сложной задачи:
/planning-with-files    ← скилл покажет шаблоны

# Создать три файла в корне проекта:
task_plan.md    ← фазы, решения, ошибки (хук читает его автоматически!)
findings.md     ← всё что нашёл/узнал в процессе
progress.md     ← лог сессии, результаты тестов
```

**Правило "2 действия":** после каждых 2 поисков/чтений → сохрани в findings.md немедленно.

**3-Strike Protocol:**
```
Попытка 1: Диагноз + фикс
Попытка 2: Другой подход (НЕ тот же!)
Попытка 3: Пересмотр допущений
После 3 провалов: объяснить пользователю что пробовал
```

### Telegram bot skill graph — для дебаггинга

```
.claude/knowledge/telegram-bots/INDEX.md  ← уже создан
```

При ошибке в боте: агент читает INDEX → следует по wikilinks → загружает только нужные узлы.
Например: двойное уведомление → _moc_safety → try-except-scope → notification-ordering.

---

## Что запустить в следующей сессии (приоритет)

### 1. arscontexta setup (20 минут, один раз, максимальный ROI)

```
/plugin install arscontexta@agenticnotetaking
→ перезапустить Claude Code
→ /arscontexta:setup
```

Ответишь на 2-4 вопроса о своём домене. Получишь:
- vault (notes/ + inbox/ + ops/ + self/)
- 16 скиллов: /reduce, /reflect, /reweave, /verify, /seed, /ralph...
- 4 хука: session-orient, write-validate, auto-commit, session-capture
- CLAUDE.md файл для vault
- Навигационные MOC файлы

**Использовать preset: Research** (атомарные заметки, явные связи, полный пайплайн)

Потом для каждой сессии с ботом:
```
/seed [файл с заметками о сессии]   ← добавить в очередь
/ralph 3                             ← обработать 3 задачи (каждая в fresh context)
/remember                            ← заминировать learnings из сессии
/reflect                             ← найти связи между заметками, обновить MOC
```

### 2. anthropics/skills официальный репо

```
/plugin marketplace add anthropics/skills
/plugin install example-skills@anthropic-agent-skills   ← webapp-testing, mcp-builder
/plugin install document-skills@anthropic-agent-skills  ← pdf, docx, pptx, xlsx
```

**pdf skill** — производственного качества, работает с теми же библиотеками что и твой текущий pdf-processing rule.

### 3. ralph-loop — для автономных задач

```
/plugin install ralph-loop@claude-plugins-official
```

Использование:
```bash
/ralph-loop "Deploy FinanceBot to VPS. Requirements: stop old process, upload files, start new, verify running. Output <promise>DONE</promise> when complete." --max-iterations 15
```

---

## Скиллы которые стоит добавить позже

| Скилл | Откуда | Зачем |
|-------|--------|-------|
| `webapp-testing` | anthropics/skills | Playwright тестирование веб-интерфейсов |
| `tapestry` | awesome-claude-skills | Создаёт knowledge networks из связанных документов |
| `root-cause-tracing` | obra/superpowers | Трейс ошибок до первопричины (полезно для async bot handlers) |
| `test-driven-development` | obra/superpowers | TDD workflow перед написанием handler кода |
| `prompt-optimizer` | daymade/claude-code-skills | EARS методология для промптов |
| `claude-md-improver` | claude-plugins-official | Периодический аудит CLAUDE.md |

---

## Ключевые команды arscontexta после setup

```bash
# Обработать новый источник знаний:
/seed notes.md          → добавить в очередь
/ralph 1               → обработать (fresh context субагент)

# Найти связи и обновить граф:
/reflect               → связать заметки между собой

# После debugging сессии — заминировать что узнал:
/remember              → создаёт methodology notes из сессии

# Проверить качество vault:
/verify                → recite test + schema + health
/graph                 → orphan notes, dangling links, link density

# Навигация:
/stats                 → метрики vault
/next                  → что делать дальше (reads task stack)

# Запросить методологию:
/arscontexta:ask "Почему важны атомарные заметки?"
/arscontexta:ask "Когда MOC нужно разделить?"
/arscontexta:health    → диагностика vault
```

---

## Максимальная скорость: workflow в одной сессии

```
Начало сессии:
1. Проверить task_plan.md (если есть) ← хук делает это автоматически
2. /next (если vault настроен) ← что делать дальше

Во время работы:
3. Каждые 2 поиска → findings.md
4. После каждой фазы → обновить task_plan.md

Конец сессии:
5. /remember ← заминировать learnings
6. Обновить progress.md
7. git commit (auto-commit хук делает это)
```

---

## Почему skill graph мощнее одного файла

Из arscontexta methodology:
> "notes are skills — curated knowledge injected when relevant"
> "the system is the argument — every note, link, and MOC demonstrates the methodology"

Один файл = одна инъекция контекста при старте.
Skill graph = агент сам выбирает что загружать через traversal.

**Практически:** telegram-bot INDEX.md (50 строк) загружается всегда.
Нужен parse-mode? Агент читает только parse-mode.md (80 строк).
Нужен полный дебаггинг нотификаций? Читает _moc_safety (50 строк) → 3 нужных узла.

Итого: ~180 строк контекста вместо 300 из одного flat файла — и агент читает ТОЛЬКО нужное.

---

## Следующий skill graph для построения

После arscontexta setup, использовать `/learn` чтобы добавить домены:

```bash
# В arscontexta vault:
/arscontexta:add-domain    ← добавить Google Sheets/Drive как второй домен
/learn "Google Sheets OAuth, Service Account, quota errors"
/learn "python-telegram-bot ConversationHandler patterns"
```

Или вручную по той же схеме что и telegram-bots:
```
.claude/knowledge/google-api/INDEX.md
.claude/knowledge/google-api/oauth-vs-sa.md
.claude/knowledge/google-api/quota-errors.md
...
```

---

## TL;DR

1. **Сейчас:** используй `/planning-with-files` для любой задачи 3+ шагов
2. **Следующая сессия:** `/plugin install arscontexta@agenticnotetaking` → `/arscontexta:setup` (20 мин)
3. **После setup:** каждая сессия заканчивается `/remember` и `/reflect`
4. **Постепенно:** расширяй skill graph (.claude/knowledge/) по доменам

Главный принцип arscontexta: **filesystem = persistent memory, context window = working memory**.
Всё важное — в файлы. Context window — только для активной работы.
