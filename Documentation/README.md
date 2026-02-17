# Documentation Index

Документация для проектов и инструментов в workspace.

---

## Figma + MCP Integration

### Quick Start
**Файл:** `FIGMA_MCP_QUICKSTART.md`

Быстрый старт за 15 минут:
- Установка Figma MCP сервера
- Аутентификация
- Первый компонент из Figma
- Checklist готовности

**Для кого:** Быстрое начало работы, proof of concept

### Full Setup Guide
**Файл:** `FIGMA_MCP_SETUP.md`

Полная пошаговая инструкция:
- Системные требования
- Настройка Figma MCP
- Подготовка Figma файлов (naming, Auto Layout, tokens)
- Code Connect маппинг
- Design system документация
- Python автоматизация
- CI/CD для design tokens
- Workflows по сценариям
- Troubleshooting
- Best practices

**Для кого:** Production setup, команды, enterprise

### Design System Template
**Файл:** `DESIGN_SYSTEM_TEMPLATE.md`

Шаблон для документирования дизайн-системы:
- Color palette (primitive + semantic tokens)
- Typography scale
- Spacing system
- Components API
- Accessibility standards
- AI generation instructions

**Для кого:** Создание DESIGN_SYSTEM.md для проекта

---

## Research Reports

### Figma + Claude Code Workflows
**Файл:** `../Projects/ResearchSystem/data/reports/report_20260215_figma_claude_code_workflows.md`

Глубокий research report (100+ источников):
- Real-world case studies (time savings 30-90%)
- Tools ecosystem (Builder.io, Locofy, v0, Bolt.new)
- Design tokens automation (W3C spec, Tokens Studio)
- Best practices и failure modes
- Альтернативы (Penpot, Framer, UXPin Merge AI)

**Для кого:** Принятие решений, выбор инструментов, архитектура

---

## Quick Reference

### MCP Setup Commands

```bash
# Установить Figma MCP
claude mcp add --transport http figma-remote-mcp https://mcp.figma.com/mcp

# Проверить статус
/mcp status

# Restart Claude Code
claude
```

### Figma Best Practices Checklist

```
✓ Semantic naming (CardContainer, не Group 5)
✓ Auto Layout для контейнеров (Shift+A)
✓ Frames вместо Groups
✓ Component variants для states
✓ Figma variables для colors/spacing
✓ Design tokens экспортированы в JSON
✓ CLAUDE.md/DESIGN_SYSTEM.md создан
```

### AI Prompt Template

```
Generate [Component] from Figma: [link]

Requirements:
- Use design tokens from DESIGN_SYSTEM.md
- TypeScript with types
- Tailwind CSS
- Include all states (hover, active, disabled, loading)
- Semantic HTML + ARIA
- Mobile-first responsive
- Reference [ExistingComponent] pattern
```

---

## Связанные файлы

### Claude Code Configuration
- `.claude/mcp.json` - MCP серверы (Figma, EXA, Context7, Playwright)
- `CLAUDE.md` - Главная документация проекта
- `.claude/rules/` - Автоприменяемые правила

### Design Tokens
- `Data/design-tokens.json` - Экспорт из Figma Tokens Studio
- `DESIGN_SYSTEM.md` - Документация дизайн-системы (создать из template)

### Python Standards
- `.claude/rules/python-standards.md` - Стандарты Python кода
- `.claude/rules/pdf-processing.md` - Работа с PDF

---

## Навигация

### По типу задачи

| Задача | Документ |
|--------|----------|
| Начать работать с Figma MCP | `FIGMA_MCP_QUICKSTART.md` |
| Production setup Figma + AI | `FIGMA_MCP_SETUP.md` |
| Создать design system docs | `DESIGN_SYSTEM_TEMPLATE.md` |
| Изучить best practices | Research report |
| Настроить Python автоматизацию | `FIGMA_MCP_SETUP.md` → Шаг 8 |
| Troubleshooting MCP | `FIGMA_MCP_SETUP.md` → Troubleshooting |

### По уровню опыта

| Уровень | Рекомендация |
|---------|-------------|
| Новичок | Quickstart → First component → Full guide |
| Опытный | Full guide → Design system template → Python automation |
| Enterprise | Research report → Full guide → CI/CD setup |

---

## Обновления

### 2026-02-15
- ✓ Создан FIGMA_MCP_QUICKSTART.md (quick start за 15 мин)
- ✓ Создан FIGMA_MCP_SETUP.md (полная инструкция)
- ✓ Создан DESIGN_SYSTEM_TEMPLATE.md (шаблон дизайн-системы)
- ✓ Добавлен README.md (этот файл)

### Планы
- [ ] Video tutorials (screen recordings)
- [ ] Example projects с Figma files
- [ ] VS Code snippets для быстрой генерации
- [ ] GitHub Actions workflows templates

---

**Maintained by:** AI Workspace Documentation
**Questions?** См. Troubleshooting секции или research report
