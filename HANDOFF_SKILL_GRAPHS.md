# HANDOFF: Skill Graphs & Knowledge Systems Session
> Дата: 19.02.2026 | Следующий шаг: /arscontexta:setup

---

## Что сделано в этой сессии

### 1. Изучена концепция Skill Graphs
Статья Heinrich о том, что один skill файл не может держать глубокие знания домена.
Решение: граф взаимосвязанных markdown файлов с wikilinks.
Паттерн: INDEX → MOC → node. Каждый узел — одна идея с YAML description и wikilinks в прозе.

### 2. Построен первый skill graph
`.claude/knowledge/telegram-bots/` — граф для Telegram ботов (9 файлов):
- INDEX.md (entry point)
- _moc_safety.md, _moc_handlers.md (кластеры)
- parse-mode.md, try-except-scope.md, notification-ordering.md
- user-data-storage.md, conflict-error.md, conversation-state.md, handler-routing.md

CLAUDE.md обновлён секцией "Knowledge Graphs" с @-ссылкой на INDEX.md.

### 3. Установлено (глобально)

| Что | Где | Статус |
|-----|-----|--------|
| planning-with-files | `~/.claude/skills/planning-with-files/SKILL.md` | ✅ работает |
| PreToolUse хук | `~/.claude/settings.json` | ✅ активен |
| arscontexta plugin | `~/.claude/plugins/...` | ✅ установлен, нужен restart |
| arscontexta marketplace | `known_marketplaces.json` | ✅ |
| planning-with-files marketplace | `known_marketplaces.json` | ✅ |
| anthropics/skills marketplace | ещё нет | ⬜ |

### 4. PreToolUse хук
`~/.claude/settings.json` содержит хук: перед каждым Write/Edit/Bash читает task_plan.md (head -20).
Это реализация "attention manipulation" из planning-with-files — агент не теряет цель.

### 5. Изучены репозитории
- **arscontexta** — 249 research claims, генерирует second brain для агента
- **planning-with-files** — 14k⭐, Manus-style persistent planning
- **anthropics/skills** — официальный репо (pdf, docx, webapp-testing, ralph-loop)
- **daymade/claude-code-skills** — 37+ скиллов
- **awesome-claude-skills** — curated list (tapestry, root-cause-tracing, test-driven-development)

---

## ГЛАВНОЕ: что делать в новой сессии

### ШАГ 1 (немедленно): arscontexta setup
```
/arscontexta:setup
```
Это 20-минутная беседа. Агент задаст 2-4 вопроса о домене и сгенерирует:
- vault (notes/ + inbox/ + ops/ + self/)
- 16 скиллов: /reduce, /reflect, /reweave, /verify, /seed, /ralph...
- 4 хука: session-orient, write-validate, auto-commit, session-capture
- Персональный CLAUDE.md для vault

**Рекомендованный preset: Research** (для Python-разработчика с несколькими проектами)

### ШАГ 2: добавить официальный Anthropic marketplace
```
/plugin marketplace add anthropics/skills
/plugin install example-skills@anthropic-agent-skills
```

### ШАГ 3: ralph-loop
```
/plugin install ralph-loop@claude-plugins-official
```

---

## Ключевой insight (для контекста)

> "LLM attention degrades as context fills. First ~40% of context window is the 'smart zone'."

Три уровня памяти:
- Уровень 1 (context): CLAUDE.md + rules → загружается всегда
- Уровень 2 (task): task_plan.md + findings.md → не в context пока не нужно
- Уровень 3 (vault): arscontexta knowledge base → персистентно между сессиями

**Skill graph vs flat file:** INDEX.md (50 строк) всегда в контексте.
Нужен конкретный узел? Агент читает только его (80 строк).
Vs один большой файл на 300+ строк который всегда загружается полностью.

---

## Файлы к которым стоит обратиться
- `CONCLUSIONS_SKILL_GRAPHS.md` — полный гайд с командами
- `.claude/knowledge/telegram-bots/INDEX.md` — пример skill graph
- `~/.claude/skills/planning-with-files/SKILL.md` — установленный глобальный скилл
