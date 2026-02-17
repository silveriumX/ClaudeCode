# Отчёт EXA: режим Swarm для Cursor

**Дата:** 29.01.2026
**Задача:** изучение режима Swarm / параллельных агентов для Cursor (поиск через EXA).

---

## Основные выводы

### 1. Cursor 2.0 (октябрь 2025): Parallel Agents + worktrees

- **До 8 агентов параллельно** на одну задачу; выбирается лучший результат (Best-of-N).
- **Изоляция через Git worktrees** (или удалённые машины) — каждый агент в своей копии репозитория, без конфликтов правок.
- **Composer** — модель Cursor, ~4× быстрее аналогов, типичный ход агента < 30 сек.
- **Стоимость:** параллельный запуск даёт примерно +25–35% токенов к одному агенту.
- Официально: [cursor.com/changelog/2-0](https://cursor.com/changelog/2-0), [cursor.com/blog/2-0](https://cursor.com/blog/2-0).

### 2. Cursor 2.4 (январь 2026): Subagents

- **Subagents** — отдельные специализированные агенты, которым родительский Agent делегирует части задачи.
- Работают **параллельно**, у каждого свой контекст; можно настраивать промпты, инструменты и модели.
- Режимы: **Foreground** (родитель ждёт ответ) и **Background** (родитель не ждёт, субагент работает в фоне).
- Встроенные субагенты: Explore (поиск по коду), Bash (shell), Browser (MCP).
- Кастомные: файлы в `.cursor/agents/` (наш orchestrator, testing-agent, financebot-* и т.д.).
- Форум: [Cursor 2.4: Subagents](https://forum.cursor.com/t/cursor-2-4-subagents/149403), [Cursor 2.4: Subagents, Skills and Image Generation](https://forum.cursor.com/t/cursor-2-4-subagents-skills-and-image-generation/149399).

### 3. Plan Mode в фоне

- **Plan Mode in Background** — план можно строить в фоне или с параллельными агентами, чтобы получить несколько планов на выбор.
- Changelog 2.0: «plan with parallel agents to have multiple plans to review».

### 4. Background Agents (облако)

- Агенты могут работать в облаке в фоне; уведомления по завершении или при необходимости подтверждения.
- В Privacy Mode на уровне организации фоновые агенты и «память» могут быть ограничены.

### 5. «Swarm» в публикациях

- Термин **«Swarm mode»** в Cursor IDE в документации не зафиксирован; по смыслу ему соответствуют:
  - **Subagents** (делегирование + параллель/фон),
  - **Parallel Agents** (worktrees, Best-of-N).
- В новостях (Yahoo Tech, 2026): эксперимент Cursor с «swarm of AI agents» (сотни агентов — planners, workers, judges) для автономной сборки браузера; это отдельный эксперимент, не штатный режим IDE.

### 6. Сравнение с Claude Code

- **Claude Code:** последовательная оркестрация специализированных агентов; Swarm — параллельные субагенты (TeammateTool, Delegate, фон).
- **Cursor:** параллель за счёт (1) Best-of-N в worktrees и (2) Subagents (делегирование, Foreground/Background). Разделение ролей — через кастомные агенты в `.cursor/agents/`.

---

## Источники (EXA)

| URL | Суть |
|-----|------|
| cursor.com/changelog/2-0 | Multi-agents, worktrees, Plan in Background |
| cursor.com/blog/2-0 | Composer, до 8 агентов, worktrees |
| cursor.com/docs/context/subagents | Subagents, Foreground/Background |
| forum.cursor.com/t/cursor-2-4-subagents/149403 | Анонс Subagents 2.4 |
| jduncan.io/blog/2025-11-01-cursor-parallel-agents | Cursor 2.0: 8 агентов, worktrees, сравнение с sequential |
| devops.com (Cursor 2.0) | Multi-agent workflows, worktrees |
| medium.com (Building Autonomous Multi-Agent...) | Background Agents API, webhooks, «Swarm»-подобная автоматизация |
| skywork.ai (Cursor AI Review 2025) | Background agents, уведомления, ограничения в Privacy Mode |

---

## Рекомендации для нашего репозитория

1. **SWARM_MODE_CURSOR.md** — оставить как есть: Subagents + Background и Parallel Agents (worktrees) покрывают «Swarm» в Cursor.
2. При появлении новых анонсов Cursor 2.4+ — проверять [cursor.com/changelog](https://cursor.com/changelog) и [forum.cursor.com](https://forum.cursor.com) на темы Subagents, Background, Parallel Agents.
3. Наши агенты в `.cursor/agents/` уже являются кастомными Subagents; делегирование и фон задаются через инструкции родительскому агенту (как в SWARM_MODE_CURSOR.md).
