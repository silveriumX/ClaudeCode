# Настройка Figma MCP для стабильной работы над дизайнами

> Пошаговая инструкция настройки Model Context Protocol (MCP) для интеграции Figma с Claude Code

**Обновлено:** 15 февраля 2026
**Применимо для:** Claude Code CLI, Windows 11

---

## Что даёт Figma MCP

**Без MCP:** Claude видит Figma только как скриншот/изображение
**С MCP:** Claude читает семантические данные дизайна напрямую:

- Структуру компонентов и их свойства
- Design tokens (цвета, типографика, отступы)
- Спецификации layout (Auto Layout)
- Библиотеку assets
- Code snippets из Dev Mode
- Маппинги Code Connect

**Результат:** 80-90% точность генерации кода (vs 60-70% без MCP)

---

## Предварительные требования

### Системные требования

```bash
# Проверить версию Node.js (требуется 18+)
node --version

# Проверить Claude Code
claude --version
```

Если Node.js не установлен:
```bash
# Скачать с https://nodejs.org/
# Установить LTS версию (20.x или новее)
```

### Figma аккаунт

- Профессиональный или бесплатный аккаунт Figma
- Доступ к файлам для чтения (минимум Viewer)
- Для Code Connect: Editor или Admin права

---

## Шаг 1: Установка Figma MCP сервера

### Вариант A: HTTP MCP сервер (рекомендуется)

```bash
# Добавить Figma MCP через HTTP транспорт
claude mcp add --transport http figma-remote-mcp https://mcp.figma.com/mcp
```

**Что происходит:**
- Claude Code добавляет Figma MCP в конфигурацию
- Сервер размещён на `https://mcp.figma.com/mcp`
- Не требует локальной установки

### Вариант B: Ручное добавление в конфиг

Отредактировать `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "figma": {
      "type": "http",
      "url": "https://mcp.figma.com/mcp"
    }
  }
}
```

---

## Шаг 2: Аутентификация Figma

### 2.1 Перезапустить Claude Code

```bash
# Перезапустить CLI
claude
```

### 2.2 Первое подключение

При первом запросе к Figma MCP увидите сообщение:

```
Figma MCP: disconnected
Press Enter to authenticate...
```

**Действия:**
1. Нажать `Enter`
2. Откроется браузер с запросом OAuth
3. Войти в Figma аккаунт
4. Нажать **"Allow access"**
5. Вернуться в Claude Code

### 2.3 Проверка подключения

```bash
# В Claude Code
/mcp status
```

Должно показать:
```
✓ figma: connected
```

---

## Шаг 3: Подготовка Figma файлов

### 3.1 Структурирование файлов

**Критически важно для качества генерации кода!**

#### Именование (семантическое)

```
✓ ПРАВИЛЬНО:
- CardContainer
- CardTitle
- PrimaryButton
- NavigationHeader

✗ НЕПРАВИЛЬНО:
- Group 5
- Rectangle 3
- Frame 12
- Layer_1
```

#### Auto Layout

```
✓ Использовать Auto Layout для всех контейнеров
✓ Настроить spacing через tokens
✓ Определить направление (horizontal/vertical)
✓ Настроить alignment и padding
```

**Почему важно:** Auto Layout → CSS Flexbox (прямое соответствие)

#### Фреймы vs Группы

```
✓ Использовать Frames (не Groups)
✓ Frame = семантический контейнер
✗ Groups = плоская группировка без структуры
```

### 3.2 Design Tokens

#### Установка Tokens Studio

1. Открыть Figma → Plugins → Browse plugins
2. Найти **"Tokens Studio for Figma"**
3. Установить (264k пользователей, 4.9/5 звёзд)

#### Создание токенов

```
1. Открыть Tokens Studio в Figma
2. Создать primitive tokens:
   - colors/blue-500: #3B82F6
   - spacing/base: 4px
   - typography/heading-1: 32px

3. Создать semantic tokens:
   - colors/primary: {colors.blue-500}
   - spacing/card-padding: {spacing.base} * 4
   - typography/h1: {typography.heading-1}
```

#### Экспорт в JSON

```
1. Tokens Studio → Export
2. Выбрать формат: W3C Design Tokens (2025.10)
3. Сохранить в проект: Data/design-tokens.json
```

**Пример структуры:**
```json
{
  "colors": {
    "primary": {
      "$value": "#3B82F6",
      "$type": "color"
    }
  },
  "spacing": {
    "base": {
      "$value": "4px",
      "$type": "dimension"
    }
  }
}
```

### 3.3 Компонентная библиотека

#### Создание компонентов с вариантами

```
1. Создать главный компонент (Component)
2. Добавить variants:
   - State: default | hover | active | disabled
   - Size: small | medium | large
   - Type: primary | secondary | outline

3. Использовать Figma variables для цветов/размеров
4. Документировать props в описании компонента
```

#### Состояния компонентов

```
✓ default - базовое состояние
✓ hover - наведение
✓ active - нажатие
✓ disabled - неактивный
✓ loading - загрузка
✓ error - ошибка
✓ empty - пустое состояние
```

**Важно:** AI не угадывает недокументированные состояния!

---

## Шаг 4: Code Connect (маппинг на код)

### 4.1 Установка Code Connect UI

```
1. Figma → Plugins → Browse
2. Найти "Code Connect UI"
3. Установить
```

### 4.2 Маппинг компонентов

```
1. Выбрать компонент в Figma (например, Button)
2. Открыть Code Connect UI
3. Подключить GitHub репозиторий
4. Выбрать файл компонента: src/components/Button.tsx
5. AI предложит маппинг свойств
6. Проверить и подтвердить
```

**Пример маппинга:**
```typescript
// Button.tsx
interface ButtonProps {
  variant: "primary" | "secondary" | "outline"
  size: "sm" | "md" | "lg"
  disabled?: boolean
}

// Figma Component Properties:
// - Type: primary | secondary | outline → variant
// - Size: small | medium | large → size (с преобразованием)
// - State: disabled → disabled
```

### 4.3 Кастомные инструкции

Добавить в Code Connect для компонента:

```markdown
## Button Component Instructions

- Always use flex layout
- Apply colors from design tokens (colors/primary, colors/secondary)
- Include hover and active states with CSS transitions
- Add focus-visible outline for keyboard navigation
- Use semantic button element (not div)
- Add aria-label if no visible text

## Accessibility Requirements
- role="button" if not native button
- aria-disabled for disabled state
- Keyboard support: Enter and Space
```

---

## Шаг 5: Создание CLAUDE.md для дизайн-системы

### 5.1 Создать файл проекта

`CLAUDE.md` или `Documentation/DESIGN_SYSTEM.md`

### 5.2 Шаблон документации

```markdown
# Design System Documentation

## Color Palette

### Primitive Tokens
- `color-blue-500`: #3B82F6 (primary brand)
- `color-gray-700`: #374151 (text primary)
- `color-red-500`: #EF4444 (error)

### Semantic Tokens
- `color-primary`: {color-blue-500}
- `color-text-primary`: {color-gray-700}
- `color-error`: {color-red-500}

## Typography Scale

- `text-xs`: 12px / 1rem
- `text-sm`: 14px / 1.167rem
- `text-base`: 16px / 1.333rem
- `text-lg`: 18px / 1.5rem
- `text-xl`: 20px / 1.667rem

Font family: Inter, system-ui, sans-serif

## Spacing System (8px grid)

- `space-1`: 4px (0.25rem)
- `space-2`: 8px (0.5rem)
- `space-3`: 12px (0.75rem)
- `space-4`: 16px (1rem)
- `space-6`: 24px (1.5rem)
- `space-8`: 32px (2rem)

## Component API

### Button
**Location:** `src/components/Button.tsx`
**Props:**
- `variant`: "primary" | "secondary" | "outline"
- `size`: "sm" | "md" | "lg"
- `disabled`: boolean
- `loading`: boolean

**Figma Component:** Components/Button

### Card
**Location:** `src/components/Card.tsx`
**Props:**
- `variant`: "default" | "elevated" | "outlined"
- `padding`: "sm" | "md" | "lg"

**Figma Component:** Components/Card

## Accessibility Standards

- WCAG 2.1 Level AA compliance
- Color contrast ratio ≥ 4.5:1 for text
- Focus indicators visible
- Semantic HTML structure
- ARIA labels where needed
```

---

## Шаг 6: Первая генерация компонента

### 6.1 Подготовка

1. Открыть Figma файл с компонентом
2. Убедиться что MCP подключён (`/mcp status`)
3. Иметь CLAUDE.md в проекте

### 6.2 Генерация (Option A: Selection)

```
1. В Figma выбрать frame/component
2. В Claude Code:

"Generate React component for my Figma selection.
Use design tokens from CLAUDE.md.
Reference existing Button component in src/components/Button.tsx.
Include hover and loading states."
```

### 6.3 Генерация (Option B: Link)

```
1. В Figma: Right-click → Copy link
2. В Claude Code:

"Convert this Figma design to React component:
https://www.figma.com/design/ABC123/file?node-id=1-2

Use Tailwind CSS with our design tokens.
Match spacing exactly from Auto Layout.
Include all component variants."
```

### 6.4 Генерация (Option C: Drag & Drop)

```
1. Экспортировать frame как PNG
2. Drag PNG в Claude Code conversation
3. Prompt:

"Generate React component matching this design.
Read layout specs from Figma MCP.
Use semantic component names.
Apply our design system from CLAUDE.md."
```

### 6.5 Проверка результата

**Чеклист:**
- [ ] Используются design tokens (не hardcoded values)
- [ ] Semantic HTML (button, header, nav, section)
- [ ] Auto Layout → Flexbox корректно
- [ ] Spacing совпадает с Figma (проверить DevTools)
- [ ] Все variants реализованы
- [ ] Hover/active states присутствуют
- [ ] Accessibility (ARIA, semantic elements)

---

## Шаг 7: CI/CD для Design Tokens (опционально)

### 7.1 Подготовка репозитория

```bash
mkdir design-tokens
cd design-tokens
npm init -y
npm install --save-dev style-dictionary
```

### 7.2 Конфигурация Style Dictionary

`config.json`:
```json
{
  "source": ["tokens/**/*.json"],
  "platforms": {
    "css": {
      "transformGroup": "css",
      "buildPath": "dist/css/",
      "files": [
        {
          "destination": "variables.css",
          "format": "css/variables"
        }
      ]
    },
    "js": {
      "transformGroup": "js",
      "buildPath": "dist/js/",
      "files": [
        {
          "destination": "tokens.js",
          "format": "javascript/es6"
        }
      ]
    }
  }
}
```

### 7.3 GitHub Actions Workflow

`.github/workflows/design-tokens.yml`:
```yaml
name: Build Design Tokens

on:
  push:
    paths:
      - 'tokens/**/*.json'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm install

      - name: Build tokens
        run: npx style-dictionary build

      - name: Commit generated files
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add dist/
          git commit -m "chore: rebuild design tokens" || exit 0
          git push
```

### 7.4 Tokens Studio → GitHub Sync

```
1. Tokens Studio → Settings → Sync providers
2. Добавить GitHub
3. Настроить:
   - Repository: username/design-tokens
   - Branch: main
   - Path: tokens/
4. Enable Auto-sync

Теперь изменения в Figma → автоматически в GitHub → CI/CD → npm
```

---

## Шаг 8: Автоматизация через Python (для batch операций)

### 8.1 Установка библиотек

```bash
pip install requests python-dotenv pathlib
```

### 8.2 Получение Personal Access Token

```
1. Figma → Settings → Personal access tokens
2. Generate new token
3. Scopes: File content (read)
4. ВАЖНО: Скопировать сразу (показывается один раз!)
5. Сохранить в .env
```

`.env`:
```bash
FIGMA_API_TOKEN=figd_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 8.3 Batch экспорт компонентов

`scripts/figma_export.py`:
```python
from pathlib import Path
import requests
import os
from dotenv import load_dotenv
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

FIGMA_API_TOKEN = os.getenv("FIGMA_API_TOKEN")
FIGMA_BASE_URL = "https://api.figma.com/v1"

def get_file_nodes(file_key: str, node_ids: List[str]) -> Dict:
    """
    Получить информацию о nodes из Figma файла.

    Args:
        file_key: Figma file key из URL
        node_ids: Список node IDs для получения

    Returns:
        Данные nodes
    """
    url = f"{FIGMA_BASE_URL}/files/{file_key}/nodes"
    headers = {"X-Figma-Token": FIGMA_API_TOKEN}
    params = {"ids": ",".join(node_ids)}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()

def export_images(
    file_key: str,
    node_ids: List[str],
    output_dir: Path,
    format: str = "png",
    scale: int = 2
) -> List[Path]:
    """
    Экспортировать frames как изображения.

    Args:
        file_key: Figma file key
        node_ids: Node IDs для экспорта
        output_dir: Папка для сохранения
        format: png | jpg | svg | pdf
        scale: 1-4 (для растровых форматов)

    Returns:
        Пути к сохранённым файлам
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Получить URLs для экспорта
    url = f"{FIGMA_BASE_URL}/images/{file_key}"
    headers = {"X-Figma-Token": FIGMA_API_TOKEN}
    params = {
        "ids": ",".join(node_ids),
        "format": format,
        "scale": str(scale)
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    image_urls = response.json().get("images", {})

    # Скачать изображения
    saved_files = []
    for node_id, image_url in image_urls.items():
        if not image_url:
            logger.warning(f"No image URL for node {node_id}")
            continue

        img_response = requests.get(image_url)
        img_response.raise_for_status()

        output_path = output_dir / f"{node_id}.{format}"
        output_path.write_bytes(img_response.content)

        saved_files.append(output_path)
        logger.info(f"Exported: {output_path}")

    return saved_files

# Использование
if __name__ == "__main__":
    FILE_KEY = "ABC123456789"  # Из Figma URL
    NODE_IDS = ["1:2", "1:3", "1:4"]  # Node IDs компонентов

    output = Path("exports/components")

    files = export_images(
        file_key=FILE_KEY,
        node_ids=NODE_IDS,
        output_dir=output,
        format="png",
        scale=2
    )

    logger.info(f"Exported {len(files)} components")
```

**Использование:**
```bash
python scripts/figma_export.py
```

---

## Шаг 9: Workflows по сценариям

### Сценарий 1: Генерация нового компонента

```
1. Дизайнер создаёт компонент в Figma
2. Использует Auto Layout + semantic naming
3. Сохраняет с вариантами (states, sizes)
4. Developer получает уведомление
5. Claude Code:
   "Generate React component for [component name] from Figma.
   Use existing patterns from src/components/.
   Include all variants and states."
6. Review и commit
```

**Timeline:** 10 минут → production-ready компонент

### Сценарий 2: Генерация страницы из mockup

```
1. Designer создаёт high-fidelity mockup
2. Использует существующие компоненты
3. Developer:
   "Generate page component from this Figma link:
   [paste link]

   Use these existing components:
   - Header from src/components/Header.tsx
   - Button from src/components/Button.tsx
   - Card from src/components/Card.tsx

   Match responsive breakpoints from CLAUDE.md.
   Use Tailwind CSS."
4. Iteration: responsiveness, state management
```

**Timeline:** 30 минут базовая имплементация → 2-3 часа production

### Сценарий 3: Batch создание product cards

```
1. Designer создаёт template компонента
2. Tokens Studio для batch generation:
   - Automator plugin: создать 100 вариантов с данными
   - Или Python script с Figma API
3. Claude Code генерирует React компонент
4. Данные из API/database для dynamic rendering
```

**Timeline:** Template 2 часа → automation 30 мин → component 10 мин

### Сценарий 4: Обновление дизайн-системы

```
1. Designer обновляет tokens в Tokens Studio
2. Auto-sync → GitHub
3. CI/CD (GitHub Actions) rebuilds tokens
4. npm publish новой версии design-tokens
5. Developer: npm update design-tokens
6. Claude Code:
   "Update components to use new token values.
   Check CLAUDE.md for updated color-primary."
```

**Timeline:** Автоматически (минуты от Figma → production)

---

## Troubleshooting

### Проблема: MCP показывает "disconnected"

**Решение:**
```bash
# Проверить статус
/mcp status

# Если disconnected:
# 1. Restart Claude Code
claude

# 2. Re-authenticate
# При запросе нажать Enter → Allow в браузере

# 3. Проверить .claude/mcp.json
# Должен быть:
{
  "mcpServers": {
    "figma": {
      "type": "http",
      "url": "https://mcp.figma.com/mcp"
    }
  }
}
```

### Проблема: AI генерирует hardcoded values вместо tokens

**Причины:**
1. Tokens не экспортированы из Figma
2. CLAUDE.md не содержит token mappings
3. Prompt не указывает использовать tokens

**Решение:**
```markdown
# В CLAUDE.md добавить explicit mapping:

## Design Token Usage Rules

ALWAYS use these tokens (never hardcode):
- Colors: Use `var(--color-primary)` NOT `#3B82F6`
- Spacing: Use `space-4` class NOT `padding: 16px`
- Typography: Use `text-base` class NOT `font-size: 16px`

# В prompt добавить:
"Use design tokens from CLAUDE.md for ALL colors and spacing.
Never use hardcoded hex values or pixel values."
```

### Проблема: Layout не совпадает с Figma

**Причины:**
1. Auto Layout не настроен в Figma
2. AI неправильно интерпретирует spacing
3. Figma использует Groups вместо Frames

**Решение:**
```
1. В Figma:
   - Заменить Groups → Frames
   - Добавить Auto Layout (Shift+A)
   - Настроить padding и spacing через tokens

2. В prompt:
   "Match layout EXACTLY from Figma Auto Layout.
   Use Flexbox with these exact values:
   - flex-direction: [horizontal/vertical]
   - gap: [value from Figma]
   - padding: [value from Figma]"
```

### Проблема: Missing imports или non-existent libraries

**Причины:**
1. AI галлюцинирует библиотеки
2. Не знает структуру проекта

**Решение:**
```
# В CLAUDE.md документировать:

## Project Structure

### Component Imports
```typescript
// Buttons
import { Button } from '@/components/Button'
import { IconButton } from '@/components/IconButton'

// Layout
import { Container } from '@/components/Container'
import { Grid } from '@/components/Grid'
```

### Allowed Libraries
- Styling: Tailwind CSS (utility classes)
- Icons: lucide-react
- UI Components: Our custom components (no external UI libs)
```

### Проблема: Figma API rate limit

**Ошибка:**
```
429 Too Many Requests
```

**Решение:**
```python
import time
from typing import Callable

def with_retry(func: Callable, max_retries: int = 3):
    """Retry with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** attempt
                logger.warning(f"Rate limited, waiting {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
    raise Exception(f"Failed after {max_retries} retries")

# Использование
result = with_retry(lambda: get_file_nodes(file_key, node_ids))
```

---

## Best Practices

### 1. Структура Figma файлов

```
✓ Semantic naming (CardContainer, не Group 5)
✓ Auto Layout для всех контейнеров
✓ Frames, не Groups
✓ Component variants для states
✓ Figma variables для colors/spacing
✓ Consistent naming convention
```

### 2. Design Tokens Management

```
✓ W3C Design Tokens format (2025.10)
✓ Two-tier: Primitive + Semantic tokens
✓ Git as source of truth (не Figma)
✓ CI/CD для автоматической синхронизации
✓ Versioning через npm/GitHub releases
```

### 3. Prompt Engineering

**Плохо:**
```
"Convert this Figma design to React"
```

**Хорошо:**
```
"Convert this Figma frame to React component.

Context:
- Use design tokens from CLAUDE.md (colors, spacing)
- Reference Button component in src/components/Button.tsx
- Match responsive breakpoints (sm: 640px, md: 768px, lg: 1024px)
- Include loading and error states
- Follow accessibility guidelines (ARIA labels, semantic HTML)

Tech stack:
- React 18 with TypeScript
- Tailwind CSS for styling
- No external UI libraries
```

### 4. Post-Generation Checklist

```
После генерации ВСЕГДА проверить:

✓ Design Tokens
  - Используются tokens, не hardcoded values
  - Правильный mapping (primary → blue-500)

✓ Responsiveness
  - Breakpoints совпадают с дизайном
  - Mobile-first подход
  - Тестирование на 375px, 768px, 1440px

✓ Accessibility
  - Semantic HTML (button, nav, header, section)
  - ARIA labels где нужно
  - Keyboard navigation (Tab, Enter, Space)
  - Focus indicators visible
  - Color contrast ≥ 4.5:1

✓ Performance
  - Нет лишних re-renders
  - Lazy loading для images
  - Code splitting если компонент тяжёлый

✓ Edge Cases
  - Loading states
  - Error states
  - Empty states
  - Long content (text overflow)
```

### 5. Code Review Guidelines

```
Reviewer должен проверить:

1. Design Fidelity
   - Layout совпадает pixel-perfect (DevTools overlay)
   - Spacing по 8px grid
   - Typography sizes и line-heights

2. Code Quality
   - TypeScript types корректны
   - Props documented (JSDoc comments)
   - Reusable logic extracted
   - No code duplication

3. Accessibility
   - WAVE browser extension: 0 errors
   - Keyboard testing: все интеракции доступны
   - Screen reader testing: логичный порядок

4. Integration
   - Imports существуют и правильны
   - Design tokens applied correctly
   - Fits existing patterns
```

---

## Автоматизация Workflows

### GitHub Actions для Figma→Code

`.github/workflows/figma-sync.yml`:
```yaml
name: Sync Figma Components

on:
  workflow_dispatch:
    inputs:
      component_name:
        description: 'Component to generate'
        required: true

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install Claude Code
        run: npm install -g @claude/code

      - name: Generate component
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude "Generate ${{ github.event.inputs.component_name }}
                  component from Figma using MCP.
                  Save to src/components/${{ github.event.inputs.component_name }}.tsx"

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          commit-message: "feat: add ${{ github.event.inputs.component_name }} component from Figma"
          branch: figma/${{ github.event.inputs.component_name }}
          title: "Add ${{ github.event.inputs.component_name }} component"
```

### VS Code Task для quick generation

`.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Generate Figma Component",
      "type": "shell",
      "command": "claude",
      "args": [
        "Generate React component from Figma selection. Use design system from CLAUDE.md. Save to src/components/${input:componentName}.tsx"
      ],
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ],
  "inputs": [
    {
      "id": "componentName",
      "type": "promptString",
      "description": "Component name (PascalCase)"
    }
  ]
}
```

---

## Метрики успеха

### Измеряйте ROI

```markdown
## Metrics to Track

### Time Savings
- Время до MCP: Design handoff + implementation
- Время после MCP: Design handoff + implementation
- Target: 50-80% reduction

### Code Quality
- TypeScript errors: 0
- ESLint warnings: < 5 per component
- Lighthouse Accessibility: 100

### Design Fidelity
- Pixel-perfect match: ≥ 95%
- Token usage: 100% (0 hardcoded values)
- Responsive coverage: mobile + tablet + desktop

### Developer Experience
- Time to first render: < 10 min
- Iterations needed: ≤ 3
- Manual adjustments: < 20% of code
```

### Пример отчёта

```
# MCP Implementation Results (Month 1)

## Components Generated: 24

### Time Savings
- Before MCP: 4-6 hours per component
- After MCP: 30-60 minutes per component
- Savings: ~80% (96 hours saved)

### Quality Metrics
- Token adherence: 95% (5% hardcoded values fixed in review)
- Accessibility score: 98 average (Lighthouse)
- Design fidelity: 92% pixel-perfect (8% minor spacing adjustments)

### Developer Feedback
- "Dramatically faster iteration"
- "Reduced back-and-forth with designers"
- "More time for complex logic vs UI boilerplate"
```

---

## Дальнейшее развитие

### Краткосрочное (1-2 недели)

- [ ] Настроить Figma MCP
- [ ] Создать первые 5 компонентов через MCP
- [ ] Установить Tokens Studio
- [ ] Задокументировать дизайн-систему (CLAUDE.md)
- [ ] Code Connect для core компонентов

### Среднесрочное (1 месяц)

- [ ] CI/CD для design tokens (GitHub Actions)
- [ ] Автоматизация через Python (batch exports)
- [ ] Design system maturity: 20+ компонентов
- [ ] Обучение команды (workshop)
- [ ] Метрики и ROI tracking

### Долгосрочное (квартал)

- [ ] Полное покрытие дизайн-системы
- [ ] Автоматические e2e тесты для UI
- [ ] Visual regression testing (Percy/Chromatic)
- [ ] Документация best practices
- [ ] Оценка альтернатив (Penpot, UXPin Merge AI)

---

## Связанные ресурсы

### Документация

- [Figma MCP Server Docs](https://developers.figma.com/docs/figma-mcp-server/)
- [W3C Design Tokens Spec](https://www.designtokens.org/tr/2025.10/format/)
- [Tokens Studio Documentation](https://docs.tokens.studio)
- [Claude Code Documentation](https://claude.com/claude-code/docs)

### Инструменты

- [Tokens Studio Plugin](https://www.figma.com/@tokens-studio)
- [Code Connect UI Plugin](https://www.figma.com/@figma)
- [Style Dictionary](https://amzn.github.io/style-dictionary/)
- [Automator for Figma](https://automator.design/)

### Внутренние ресурсы

- `Projects/ResearchSystem/data/reports/report_20260215_figma_claude_code_workflows.md` - Полный research report
- `.claude/skills/README.md` - Каталог скиллов
- `CLAUDE.md` - Главная документация проекта
- `.claude/rules/python-standards.md` - Python стандарты

---

**Последнее обновление:** 15 февраля 2026
**Версия:** 1.0
**Автор:** Claude Code Setup Guide

**Вопросы?** См. Troubleshooting секцию или полный research report.
