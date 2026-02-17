# Design System

**Последнее обновление:** 15.02.2026
**Проект:** CloudeCode Workspace

---

## Colors

### Primary Colors
- `color-primary`: `#3B82F6` (blue-500)
- `color-primary-hover`: `#2563EB` (blue-600)
- `color-primary-active`: `#1D4ED8` (blue-700)

### Neutral Colors
- `color-text-primary`: `#111827` (gray-900)
- `color-text-secondary`: `#374151` (gray-700)
- `color-text-muted`: `#6B7280` (gray-500)
- `color-background`: `#F9FAFB` (gray-50)
- `color-surface`: `#FFFFFF`

### Semantic Colors
- `color-success`: `#10B981` (green-500)
- `color-error`: `#EF4444` (red-500)
- `color-warning`: `#F59E0B` (amber-500)

### Usage Rule
```
✓ ALWAYS use tokens: bg-color-primary
✗ NEVER hardcode: bg-[#3B82F6]
```

---

## Typography

### Font Family
**Primary:** Inter, system-ui, -apple-system, sans-serif

### Type Scale
```
text-sm:    14px / 0.875rem  (line-height: 1.25rem)
text-base:  16px / 1rem      (line-height: 1.5rem)
text-lg:    18px / 1.125rem  (line-height: 1.75rem)
text-xl:    20px / 1.25rem   (line-height: 1.75rem)
text-2xl:   24px / 1.5rem    (line-height: 2rem)
```

### Font Weights
```
font-normal:    400
font-medium:    500
font-semibold:  600
font-bold:      700
```

---

## Spacing (8px grid)

```
space-2:   8px   (0.5rem)
space-4:   16px  (1rem)
space-6:   24px  (1.5rem)
space-8:   32px  (2rem)
space-12:  48px  (3rem)
```

### Usage
```
Component padding:  space-4 to space-6 (16-24px)
Component gap:      space-4 (16px)
Section spacing:    space-12 (48px)
```

---

## Layout

### Breakpoints
```
sm:  640px   (Mobile landscape)
md:  768px   (Tablet)
lg:  1024px  (Desktop)
xl:  1280px  (Large desktop)
```

### Responsive Pattern
```typescript
// Mobile-first
<div className="p-space-4 md:p-space-6 lg:p-space-8">
```

---

## Border Radius

```
rounded-md:   6px   (inputs)
rounded-lg:   8px   (buttons)
rounded-xl:   12px  (cards)
```

---

## Components

### Button
**Location:** `src/components/Button.tsx` (если есть)

**Props:**
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  children: React.ReactNode
}
```

**Variants:**
- `primary`: Blue background (call-to-action)
- `secondary`: Gray background (secondary action)
- `outline`: Transparent with border

**States:**
- `default`: Base
- `hover`: Darker background
- `active`: Pressed
- `disabled`: 50% opacity

---

## Accessibility

### Requirements
- WCAG 2.1 Level AA
- Color contrast ≥ 4.5:1 for text
- Semantic HTML (button, nav, header)
- ARIA labels for icon buttons
- Keyboard navigation (Tab, Enter, Space)

---

## AI Generation Instructions

### For Claude Code

**ALWAYS:**
- Use design tokens from this file
- Include TypeScript types
- Add semantic HTML
- Include ARIA labels where needed
- Mobile-first responsive (sm, md, lg breakpoints)
- Include all states (hover, active, disabled)

**NEVER:**
- Hardcode colors (#3B82F6) → use color-primary
- Hardcode spacing (16px) → use space-4
- Use div for buttons → use button element
- Skip TypeScript types
- Skip ARIA labels on icon buttons

**Example Prompt:**
```
Generate [Component] from Figma: [link]

Use design tokens from DESIGN_SYSTEM.md.
TypeScript with strict types.
Tailwind CSS classes.
Include hover/active/disabled states.
Semantic HTML + ARIA labels.
Mobile-first responsive.
```

---

**Next:** Expand this file as design system grows
**Template:** See `Documentation/DESIGN_SYSTEM_TEMPLATE.md` for full version
