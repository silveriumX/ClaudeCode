# Design System Template

> Шаблон для документирования дизайн-системы для AI (Claude Code, Cursor, etc.)
> Скопируйте и адаптируйте под ваш проект

---

## Инструкция по использованию

1. Скопировать этот файл в корень проекта как `DESIGN_SYSTEM.md`
2. Заполнить все секции актуальными значениями
3. Экспортировать tokens из Figma (Tokens Studio → Export JSON)
4. Поддерживать в актуальном состоянии при изменениях

**Цель:** AI должен понимать вашу дизайн-систему и использовать правильные tokens/компоненты

---

# [Project Name] Design System

**Последнее обновление:** [YYYY-MM-DD]
**Версия:** 1.0.0
**Дизайн файл Figma:** [ссылка]
**Token файл:** `Data/design-tokens.json`

---

## Color Palette

### Primitive Tokens

**Primary Colors:**
- `color-blue-50`: `#EFF6FF` - Lightest blue
- `color-blue-100`: `#DBEAFE`
- `color-blue-500`: `#3B82F6` - Primary brand color
- `color-blue-600`: `#2563EB` - Primary hover
- `color-blue-700`: `#1D4ED8` - Primary active

**Neutral Colors:**
- `color-gray-50`: `#F9FAFB` - Background
- `color-gray-100`: `#F3F4F6` - Background secondary
- `color-gray-700`: `#374151` - Text primary
- `color-gray-900`: `#111827` - Text heading

**Semantic Colors:**
- `color-error`: `#EF4444` (red-500)
- `color-success`: `#10B981` (green-500)
- `color-warning`: `#F59E0B` (amber-500)
- `color-info`: `#3B82F6` (blue-500)

### Semantic Tokens

```
color-primary → color-blue-500
color-primary-hover → color-blue-600
color-primary-active → color-blue-700

color-text-primary → color-gray-900
color-text-secondary → color-gray-700
color-text-muted → color-gray-500

color-background → color-gray-50
color-background-secondary → color-gray-100
color-surface → #FFFFFF
```

### Usage Rules

```
✓ ALWAYS use semantic tokens in components:
  - Primary buttons → color-primary
  - Text → color-text-primary
  - Backgrounds → color-background

✗ NEVER hardcode hex values:
  - ❌ background-color: #3B82F6
  - ✓ background-color: var(--color-primary)
```

---

## Typography

### Font Families

**Primary:** Inter, system-ui, -apple-system, sans-serif
**Monospace:** 'Fira Code', 'Courier New', monospace

### Type Scale

```
text-xs:    12px / 0.75rem   (line-height: 1rem)
text-sm:    14px / 0.875rem  (line-height: 1.25rem)
text-base:  16px / 1rem      (line-height: 1.5rem)
text-lg:    18px / 1.125rem  (line-height: 1.75rem)
text-xl:    20px / 1.25rem   (line-height: 1.75rem)
text-2xl:   24px / 1.5rem    (line-height: 2rem)
text-3xl:   30px / 1.875rem  (line-height: 2.25rem)
text-4xl:   36px / 2.25rem   (line-height: 2.5rem)
```

### Font Weights

```
font-normal:    400
font-medium:    500
font-semibold:  600
font-bold:      700
```

### Usage Examples

```typescript
// Headings
<h1 className="text-4xl font-bold text-gray-900">Page Title</h1>
<h2 className="text-3xl font-semibold text-gray-900">Section</h2>

// Body
<p className="text-base text-gray-700">Paragraph text</p>
<p className="text-sm text-gray-500">Caption text</p>
```

---

## Spacing System

### Base Unit: 4px

```
space-0:   0px
space-1:   4px   (0.25rem)
space-2:   8px   (0.5rem)
space-3:   12px  (0.75rem)
space-4:   16px  (1rem)
space-5:   20px  (1.25rem)
space-6:   24px  (1.5rem)
space-8:   32px  (2rem)
space-10:  40px  (2.5rem)
space-12:  48px  (3rem)
space-16:  64px  (4rem)
space-20:  80px  (5rem)
space-24:  96px  (6rem)
```

### Usage Guidelines

```
Component padding:    space-4 to space-6 (16-24px)
Component gap:        space-4 (16px)
Section spacing:      space-12 to space-16 (48-64px)
Page margins:         space-6 to space-8 (24-32px)
```

### Responsive Spacing

```typescript
// Mobile
<div className="p-space-4 md:p-space-6 lg:p-space-8">

// Vertical rhythm
<div className="space-y-space-4">  // 16px gap between children
```

---

## Layout & Grid

### Breakpoints

```
sm:  640px   (Mobile landscape, small tablet)
md:  768px   (Tablet portrait)
lg:  1024px  (Tablet landscape, small desktop)
xl:  1280px  (Desktop)
2xl: 1536px  (Large desktop)
```

### Container Widths

```
Mobile:     100% (full width)
Tablet:     720px max
Desktop:    1140px max
Wide:       1280px max
```

### Grid System

```typescript
// 12-column grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-6">
  {/* Items */}
</div>

// Flexbox layout
<div className="flex flex-col md:flex-row gap-space-4">
  {/* Items */}
</div>
```

---

## Border Radius

```
rounded-none:   0px
rounded-sm:     2px   (0.125rem)
rounded:        4px   (0.25rem)
rounded-md:     6px   (0.375rem)
rounded-lg:     8px   (0.5rem)
rounded-xl:     12px  (0.75rem)
rounded-2xl:    16px  (1rem)
rounded-full:   9999px (pill shape)
```

### Usage

```
Buttons:        rounded-lg (8px)
Cards:          rounded-xl (12px)
Inputs:         rounded-md (6px)
Badges:         rounded-full
Modal:          rounded-2xl (16px)
```

---

## Shadows

### Shadow Scale

```css
shadow-sm:    0 1px 2px 0 rgb(0 0 0 / 0.05)
shadow:       0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)
shadow-md:    0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)
shadow-lg:    0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)
shadow-xl:    0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)
```

### Usage

```
Cards:          shadow-md
Dropdowns:      shadow-lg
Modals:         shadow-xl
Buttons hover:  shadow-sm
```

---

## Components

### Button

**Location:** `src/components/Button.tsx`

**Figma Component:** `Components/Button`

**Props:**
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  icon?: React.ReactNode
  children: React.ReactNode
  onClick?: () => void
}
```

**Variants:**
- `primary`: Blue background, white text (call-to-action)
- `secondary`: Gray background, dark text (secondary actions)
- `outline`: Transparent with border (tertiary actions)
- `ghost`: Transparent no border (inline actions)

**States:**
- `default`: Base appearance
- `hover`: Slightly darker background
- `active`: Pressed appearance
- `disabled`: 50% opacity, no pointer events
- `loading`: Spinner icon, disabled

**Usage:**
```typescript
<Button variant="primary" size="md" onClick={handleSubmit}>
  Submit
</Button>

<Button variant="outline" size="sm" loading>
  Loading...
</Button>
```

---

### Card

**Location:** `src/components/Card.tsx`

**Figma Component:** `Components/Card`

**Props:**
```typescript
interface CardProps {
  variant?: 'default' | 'elevated' | 'outlined'
  padding?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}
```

**Variants:**
- `default`: White background, shadow-md
- `elevated`: White background, shadow-lg
- `outlined`: Border, no shadow

**Usage:**
```typescript
<Card variant="elevated" padding="lg">
  <h3 className="text-xl font-semibold">Card Title</h3>
  <p className="text-gray-600 mt-space-2">Content</p>
</Card>
```

---

### Input

**Location:** `src/components/Input.tsx`

**Figma Component:** `Components/Input`

**Props:**
```typescript
interface InputProps {
  type?: 'text' | 'email' | 'password' | 'number'
  placeholder?: string
  label?: string
  error?: string
  disabled?: boolean
  value: string
  onChange: (value: string) => void
}
```

**States:**
- `default`: Gray border
- `focus`: Blue border, outline ring
- `error`: Red border, error message below
- `disabled`: Gray background, cursor not-allowed

**Usage:**
```typescript
<Input
  label="Email"
  type="email"
  placeholder="you@example.com"
  value={email}
  onChange={setEmail}
  error={emailError}
/>
```

---

## Accessibility Standards

### WCAG 2.1 Level AA Requirements

**Color Contrast:**
- Normal text (< 18px): ≥ 4.5:1
- Large text (≥ 18px): ≥ 3:1
- Interactive elements: ≥ 3:1

**Keyboard Navigation:**
- All interactive elements accessible via Tab
- Visible focus indicators (outline ring)
- Logical tab order

**Semantic HTML:**
```html
✓ Use <button> for buttons (not <div>)
✓ Use <nav> for navigation
✓ Use <header>, <main>, <footer>
✓ Use <h1>-<h6> in order
✓ Use <label> for form inputs
```

**ARIA Labels:**
```typescript
// Icon buttons need labels
<button aria-label="Close modal">
  <XIcon />
</button>

// Loading states
<div role="status" aria-live="polite">
  Loading...
</div>

// Form errors
<input aria-invalid={!!error} aria-describedby="error-message" />
<span id="error-message">{error}</span>
```

---

## Animation & Transitions

### Timing Functions

```css
ease-linear:     cubic-bezier(0, 0, 1, 1)
ease-in:         cubic-bezier(0.4, 0, 1, 1)
ease-out:        cubic-bezier(0, 0, 0.2, 1)
ease-in-out:     cubic-bezier(0.4, 0, 0.2, 1)
```

### Duration

```
duration-75:    75ms   (instant feedback)
duration-100:   100ms  (micro-interactions)
duration-150:   150ms  (hover states)
duration-200:   200ms  (default transitions)
duration-300:   300ms  (modal open/close)
```

### Usage

```typescript
// Button hover
<button className="transition-colors duration-200 hover:bg-blue-600">

// Modal fade in
<div className="transition-opacity duration-300 ease-in-out">
```

---

## Icons

### Icon System: Lucide React

**Package:** `lucide-react`

**Sizes:**
```
icon-sm:  16px
icon-md:  20px
icon-lg:  24px
icon-xl:  32px
```

**Usage:**
```typescript
import { ChevronRight, Check, X } from 'lucide-react'

<ChevronRight size={20} className="text-gray-500" />
<Check size={16} className="text-green-500" />
```

**Accessibility:**
```typescript
// Decorative icons (no ARIA needed)
<ChevronRight aria-hidden="true" />

// Meaningful icons (add label)
<button aria-label="Close">
  <X size={20} />
</button>
```

---

## Responsive Design

### Mobile-First Approach

```typescript
// Start with mobile, add breakpoints
<div className="
  p-space-4          // mobile: 16px padding
  md:p-space-6       // tablet: 24px padding
  lg:p-space-8       // desktop: 32px padding
">
```

### Common Patterns

```typescript
// Stack on mobile, row on desktop
<div className="flex flex-col md:flex-row gap-space-4">

// 1 column mobile, 2 tablet, 3 desktop
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">

// Hide on mobile, show on desktop
<div className="hidden md:block">

// Full width mobile, constrained desktop
<div className="w-full lg:w-1/2">
```

---

## Code Style Guidelines

### Component Structure

```typescript
import React from 'react'
import { cn } from '@/lib/utils'  // classname utility

interface ComponentProps {
  // Props with comments
  variant?: 'primary' | 'secondary'
  /** Content to display */
  children: React.ReactNode
}

/**
 * Component description
 *
 * @example
 * <Component variant="primary">Text</Component>
 */
export function Component({
  variant = 'primary',
  children
}: ComponentProps) {
  return (
    <div className={cn(
      'base-classes',
      variant === 'primary' && 'variant-classes'
    )}>
      {children}
    </div>
  )
}
```

### Naming Conventions

```
Components:     PascalCase    (Button, Card, InputField)
Props:          camelCase     (onClick, isDisabled)
CSS Classes:    kebab-case    (button-primary, card-elevated)
Tokens:         kebab-case    (color-primary, space-4)
Files:          PascalCase    (Button.tsx, Card.tsx)
```

---

## AI Generation Instructions

### For Claude Code / Cursor

**ALWAYS:**
- Use design tokens from this document (NEVER hardcode values)
- Reference existing components by file path
- Include TypeScript types
- Add accessibility attributes (ARIA, semantic HTML)
- Follow mobile-first responsive design
- Include all component states (hover, active, disabled, loading)

**NEVER:**
- Hardcode colors, spacing, or font sizes
- Use `<div>` with onClick (use `<button>`)
- Skip ARIA labels on icon buttons
- Import non-existent libraries
- Generate components without TypeScript

**Example Prompt:**
```
Generate [Component Name] component matching Figma design:
[paste link]

Requirements:
- Use design tokens from DESIGN_SYSTEM.md
- TypeScript with strict types
- Tailwind CSS for styling
- Include hover, active, disabled states
- Semantic HTML with ARIA labels
- Mobile-first responsive
- Reference existing Button component pattern
```

---

## Token File Export

**Location:** `Data/design-tokens.json`

**Format:** W3C Design Tokens (2025.10)

**Example:**
```json
{
  "colors": {
    "primary": {
      "$value": "#3B82F6",
      "$type": "color",
      "description": "Primary brand color"
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

**Sync:** Figma (Tokens Studio) ↔ GitHub ↔ Code

---

## Changelog

### Version 1.0.0 (YYYY-MM-DD)
- Initial design system documentation
- Core components: Button, Card, Input
- Design tokens: colors, spacing, typography
- Accessibility guidelines

---

**Maintained by:** [Team Name]
**Questions?** [Contact / Slack channel]
**Design review:** [Figma link to design system file]
