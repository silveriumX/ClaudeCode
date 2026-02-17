# Figma MCP Quick Start

> Быстрый старт для начала работы с Figma MCP за 15 минут

**Для полной инструкции см.** `FIGMA_MCP_SETUP.md`

---

## 5 шагов до первого компонента

### 1. Установить Figma MCP (2 мин)

```bash
# Добавить Figma MCP сервер
claude mcp add --transport http figma-remote-mcp https://mcp.figma.com/mcp

# Перезапустить Claude Code
claude
```

### 2. Аутентифицировать (1 мин)

```bash
# Проверить статус
/mcp status

# Если disconnected → нажать Enter → Allow в браузере
```

### 3. Подготовить Figma (5 мин)

**Критически важно:**
```
✓ Именовать frames семантически (CardContainer, не Group 5)
✓ Использовать Auto Layout (Shift+A) для контейнеров
✓ Frames вместо Groups
✓ Figma variables для цветов/spacing
```

### 4. Создать CLAUDE.md (5 мин)

Минимальная версия:
```markdown
# Design System

## Colors
- `color-primary`: #3B82F6
- `color-text`: #374151

## Spacing (8px grid)
- `space-2`: 8px
- `space-4`: 16px
- `space-6`: 24px

## Typography
- `text-base`: 16px
- `text-lg`: 18px

## Components
- Button: `src/components/Button.tsx`
- Card: `src/components/Card.tsx`
```

### 5. Сгенерировать первый компонент (2 мин)

В Claude Code:
```
"Generate React component from this Figma link:
[paste Figma link]

Use design tokens from CLAUDE.md.
Include TypeScript types.
Add hover states."
```

---

## Пример результата

**Input (Figma):**
- Button component с variants (primary/secondary)
- Auto Layout настроен
- Semantic naming

**Output (Claude Code):**
```typescript
import React from 'react'

interface ButtonProps {
  variant?: 'primary' | 'secondary'
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
}

export function Button({
  variant = 'primary',
  children,
  onClick,
  disabled
}: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        px-space-4 py-space-2 rounded-lg
        transition-colors duration-200
        ${variant === 'primary'
          ? 'bg-color-primary hover:bg-blue-600 text-white'
          : 'bg-gray-200 hover:bg-gray-300 text-gray-800'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {children}
    </button>
  )
}
```

---

## Checklist готовности

Перед production use убедитесь:

- [ ] Figma MCP connected (`/mcp status` показывает ✓)
- [ ] CLAUDE.md создан с design tokens
- [ ] Figma файлы используют semantic naming
- [ ] Auto Layout настроен
- [ ] Первый компонент успешно сгенерирован и работает
- [ ] Token values совпадают Figma ↔ Code

---

## Типичные ошибки

### ❌ MCP disconnected
```bash
# Решение:
claude  # restart
# Нажать Enter при "Press Enter to authenticate"
```

### ❌ Hardcoded values вместо tokens
```
# В prompt добавить:
"Use design tokens from CLAUDE.md.
NEVER use hardcoded hex colors or pixel values."
```

### ❌ Layout не совпадает
```
# В Figma:
- Добавить Auto Layout (Shift+A)
- Заменить Groups → Frames (правый клик → Frame selection)
```

---

## Следующие шаги

1. **Установить Tokens Studio plugin** (для управления tokens)
2. **Настроить Code Connect** (маппинг компонентов на код)
3. **Создать 5-10 core компонентов** через MCP
4. **Документировать дизайн-систему** (расширить CLAUDE.md)
5. **Setup CI/CD для tokens** (GitHub Actions)

**Полная инструкция:** `Documentation/FIGMA_MCP_SETUP.md`

---

**Время до первого результата:** 15 минут
**Время до production-ready setup:** 1-2 дня
**ROI:** 50-80% time savings (согласно research)
