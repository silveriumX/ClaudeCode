# 🎯 Swarm Mode - Готовые примеры для копирования

## 📋 Просто скопируйте и используйте эти команды!

---

## 🌟 Базовые примеры

### 1. Первое знакомство со Swarm

```
Привет! Я хочу попробовать swarm режим.
Создай простую демо-команду из 3 агентов и покажи как они взаимодействуют.
Дай каждому агенту простую задачу и покажи результаты.
```

### 2. Создание фичи с нуля

```
Мне нужно добавить форму регистрации пользователей в React приложение.

Создай swarm команду:
- Frontend Dev: компоненты RegisterForm, EmailInput, PasswordInput
- Validator: валидация email и пароля, показ ошибок
- Stylist: стилизация компонентов, responsive design
- Tester: напиши unit тесты для всех компонентов

Работайте параллельно где возможно.
```

### 3. Быстрый код-ревью

```
Проведи код-ревью файлов в папке src/components.

Создай 4 специализированных ревьюера:
1. Security Expert - ищи XSS, injection, auth проблемы
2. Performance Guru - найди медленные операции, лишние рендеры
3. Code Quality - проверь читаемость, DRY, именование
4. Best Practices - React hooks правила, patterns

Каждый пишет отдельный отчет с оценкой 1-10.
```

---

## 🚀 Продвинутые примеры

### 4. Fullstack фича от А до Я

```
Добавь систему комментариев в блог приложение.

Pipeline команда:
1. Research Agent: изучи best practices для comment systems (threading, moderation)
2. Database Architect: спроектируй схему БД для комментариев
3. Backend Dev: создай API endpoints (GET/POST/DELETE /comments)
4. Frontend Dev: компонент CommentList, CommentForm, CommentItem
5. Security Reviewer: проверь XSS защиту, rate limiting
6. Test Engineer: integration тесты для всего flow
7. Documentation: обнови API docs и user guide

Шаги 1-2 последовательно, потом 3-4 параллельно, потом 5-7 параллельно.
```

### 5. Массовый рефакторинг

```
У меня в папке src/legacy 80 компонентов на class-based React.
Нужно конвертировать все в functional components с hooks.

Swarm план:
1. Research Agent: создай migration guide (useState, useEffect замены)
2. Создай swarm из 8 Worker агентов
3. Каждый Worker берет по 10 компонентов из пула
4. После конвертации Worker запускает тесты
5. Quality Checker проверяет каждый результат
6. Если тесты упали - Worker чинит и пробует снова

Запускай!
```

### 6. Исправление багов из GitHub Issues

```
У меня 30 open issues на GitHub в репозитории myproject/repo.

Swarm strategy:
1. Triage Agent: прочитай все issues, распредели по priority (P0-P3)
2. Создай 6 Developer агентов
3. Developers берут issues по приоритету из пула:
   - Воспроизводят баг
   - Пишут failing test
   - Чинят код
   - Проверяют что test проходит
4. Reviewer агент проверяет каждый fix
5. После approve - создать draft PR

Начинаем с P0 issues!
```

---

## 🎨 Специализированные сценарии

### 7. Миграция на TypeScript

```
Конвертируй весь проект с JavaScript на TypeScript.

Команда:
1. Planning Agent: создай стратегию миграции (порядок файлов)
2. Type Definition Agent: создай .d.ts для всех интерфейсов
3. Создай swarm из 10 Conversion агентов:
   - Конвертируй .js → .ts
   - Добавь типы для всех функций
   - Фикси type errors
4. Strict Mode Agent: включи strict mode и чини ошибки
5. Documentation: обнови README с TS инструкциями

Работаем снизу-вверх по дереву зависимостей.
```

### 8. Оптимизация производительности

```
Мое React приложение тормозит. Оптимизируй его.

Performance Team:
1. Profiler Agent:
   - Запусти React DevTools Profiler
   - Найди компоненты с частыми re-renders
   - Найди медленные операции
2. Создай специалистов по проблемам:
   - Memo Expert: добавь React.memo, useMemo, useCallback
   - Bundle Optimizer: code splitting, lazy loading
   - Asset Optimizer: оптимизируй изображения, CSS
   - Network Expert: оптимизируй API calls, caching
3. Benchmark Agent: измерь улучшения до/после

Цель: улучшить Lighthouse score на 30+ баллов.
```

### 9. SEO и Accessibility аудит

```
Проверь весь сайт на SEO и доступность.

Audit Team:
1. SEO Auditor:
   - Проверь meta tags на всех страницах
   - Найди broken links
   - Проверь sitemap.xml и robots.txt
   - Semantic HTML использование
2. A11y Auditor:
   - ARIA labels
   - Keyboard navigation
   - Screen reader compatibility
   - Color contrast
3. Performance Auditor:
   - Page load speed
   - Core Web Vitals
4. Fixer agents (по одному на каждую проблему)

Создай подробный отчет с приоритетами.
```

### 10. Документация проекта

```
Создай полную документацию для моего проекта.

Documentation Swarm:
1. Architecture Writer:
   - Создай диаграммы архитектуры
   - Опиши data flow
   - Паттерны и принципы
2. API Documenter:
   - OpenAPI/Swagger спецификация
   - Примеры для каждого endpoint
   - Error codes и handling
3. Component Documenter:
   - Storybook stories для UI
   - Props documentation
   - Usage examples
4. Tutorial Writer:
   - Getting Started guide
   - Step-by-step tutorials
   - Common recipes
5. Deployment Guide:
   - Docker setup
   - CI/CD инструкции
   - Environment variables

Все в папку /docs с красивым навигационным README.
```

---

## 🧪 Тестирование

### 11. Полное покрытие тестами

```
Добавь comprehensive test coverage для проекта.

Test Squad:
1. Unit Test Agent: тесты для всех утилитных функций
2. Component Test Agent: React Testing Library тесты для UI
3. Integration Test Agent: тесты для сложных flows
4. E2E Test Agent: Playwright тесты для critical paths
5. Coverage Reporter: генерируй coverage report, найди gaps

Цель: 80%+ coverage для всех типов кода.
```

### 12. Фикс упавших тестов

```
У меня упало 45 тестов после последнего рефакторинга.

Fix Team:
1. Analyzer: группируй тесты по причине падения
2. Создай 5 Fixer агентов
3. Каждый берет группу тестов:
   - Анализирует почему упал
   - Решает: обновить тест или фиксить код
   - Применяет исправление
   - Проверяет что тест проходит
4. Regression Checker: проверяет что не сломалось ничего нового

Быстро!
```

---

## 🎨 Дизайн и UI/UX

### 13. UI Component Library

```
Создай библиотеку переиспользуемых компонентов.

Component Team:
1. Button Component:
   - Variants: primary, secondary, danger, ghost
   - Sizes: sm, md, lg
   - States: default, hover, active, disabled
2. Input Component: с валидацией и ошибками
3. Modal Component: с backdrop, close button
4. Card Component: header, body, footer slots
5. Table Component: sorting, pagination, filtering

Каждому агенту - по компоненту.
Все должны иметь:
- TypeScript types
- Storybook stories
- Unit тесты
- Accessibility support
```

### 14. Темизация приложения

```
Добавь dark/light theme support в приложение.

Theme Team:
1. Design System Agent:
   - Создай color палитры (light/dark)
   - Typography scales
   - Spacing system
2. CSS Variables Agent: настрой CSS custom properties
3. Theme Context Agent: React context для переключения
4. Component Updater Swarm (5 агентов):
   - Обнови все компоненты использовать theme colors
   - Замени хардкод colors на CSS variables
5. Persistence Agent: сохраняй выбранную тему в localStorage

Smooth transitions между темами!
```

---

## 🔧 DevOps и Infrastructure

### 15. CI/CD Pipeline setup

```
Настрой полный CI/CD pipeline для проекта.

DevOps Team:
1. GitHub Actions Agent:
   - Workflow для тестов на PR
   - Workflow для deploy на staging/prod
   - Linting и type checking
2. Docker Agent:
   - Multi-stage Dockerfile
   - Docker Compose для local dev
   - .dockerignore
3. Deployment Agent:
   - Настрой auto-deploy на Vercel/Netlify
   - Environment variables management
4. Monitoring Agent:
   - Setup error tracking (Sentry)
   - Performance monitoring
   - Logs aggregation

Хочу push-to-deploy experience!
```

---

## 📊 Анализ и Мониторинг

### 16. Codebase анализ

```
Проанализируй весь codebase и дай рекомендации.

Analysis Team:
1. Code Complexity Agent:
   - Найди слишком сложные функции (cyclomatic complexity)
   - Длинные файлы (>500 lines)
   - Deep nesting (>4 levels)
2. Dependency Agent:
   - Outdated packages
   - Security vulnerabilities
   - Unused dependencies
3. Performance Agent:
   - Heavy файлы в bundle
   - Unnecessary re-renders
   - Memory leaks suspects
4. Best Practices Agent:
   - Анти-паттерны
   - Code smells
   - Tech debt

Подробный отчет с приоритизацией fixes.
```

---

## 🎓 Обучение и Onboarding

### 17. Onboarding документация для новых разработчиков

```
Создай comprehensive onboarding guide для новых девов.

Onboarding Team:
1. Setup Guide Writer:
   - Prerequisites (Node, Git, IDE)
   - Clone and install steps
   - Environment setup
   - First run
2. Architecture Guide Writer:
   - Project structure explained
   - Key concepts и patterns
   - Where to find what
3. Contributing Guide Writer:
   - Git workflow (branches, PRs)
   - Code style guide
   - Testing requirements
   - Review process
4. FAQ Collector:
   - Common issues и решения
   - Development tips
   - Debugging guide

Сделай так, чтобы новый дев мог начать за 1 день!
```

---

## 💡 Креативные применения

### 18. Генерация тестовых данных

```
Создай realistic test data для приложения.

Data Generation Swarm:
1. Users Generator: 1000 fake users (разные страны, демография)
2. Posts Generator: 5000 блог постов (разные темы, длины)
3. Comments Generator: 20000 комментариев (realistic threads)
4. Products Generator: 500 товаров (разные категории, prices)
5. Orders Generator: 3000 заказов (realistic order patterns)

Используй faker.js. Все в seed.json файлы.
```

### 19. Интернационализация (i18n)

```
Добавь мультиязычность в приложение.

i18n Team:
1. Setup Agent: настрой i18next, создай структуру папок
2. Extractor Agent: найди все хардкод строки в коде
3. Translation Files Creator Swarm (один агент на язык):
   - English (en.json)
   - Spanish (es.json)
   - German (de.json)
   - French (fr.json)
   - Russian (ru.json)
4. Component Updater Swarm: замени строки на t('key')
5. Language Switcher: компонент для переключения языка

Поддержка plurals и date formatting!
```

### 20. Миграция State Management

```
Мигрируй приложение с Redux на Zustand.

Migration Team:
1. Analyzer: составь список всех Redux слайсов
2. Store Converter Swarm (по агенту на слайс):
   - Конвертируй reducer → Zustand store
   - Сохрани ту же логику
3. Component Updater Swarm:
   - Замени useSelector → use<Store>
   - Замени useDispatch → прямые вызовы actions
4. Middleware Handler: перенеси middleware логику
5. Testing Agent: проверь что все работает как раньше

Постепенная миграция, не ломая существующий код!
```

---

## 🎯 Шпаргалка по выбору паттерна

| Ситуация | Паттерн | Пример команды |
|----------|---------|----------------|
| Нужны разные мнения | Parallel Review | "Проверь код параллельно: security, performance, quality" |
| Зависимые шаги | Pipeline | "Pipeline: research → design → implement → test" |
| Много похожих задач | Swarm | "Swarm из 5 агентов для рефакторинга 50 файлов" |
| Нужна инфа сначала | Research + Action | "Изучи best practices, потом реализуй" |
| Комплексная фича | Specialist Team | "Frontend, Backend, Testing агенты для auth системы" |

---

## 🚀 Быстрый старт (30 секунд)

1. **Запустите**: `claude-swarm.bat`
2. **Скажите**: "Создай демо swarm команду с 3 агентами"
3. **Смотрите**: Как агенты работают параллельно
4. **Выберите**: Любой пример из этого файла
5. **Копируйте**: Команду в Claude Code
6. **Наблюдайте**: Магию swarm режима! ✨

---

## 💬 Нужна помощь?

Просто спросите Claude:
```
"Покажи мне пример swarm команды для [ваша задача]"
"Какой паттерн лучше для [ваш сценарий]?"
"Объясни как работает [название паттерна]"
```

**Swarm Mode делает невозможное возможным! 🌊**
