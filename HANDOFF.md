# HANDOFF: Figma + Claude Code Workflows для Product Cards

**Дата создания:** 15 февраля 2026
**Статус:** Research завершён, готовы к implementation
**Приоритет:** High - готов к немедленному использованию

---

## 🎯 GOAL: Что мы пытаемся достичь

### Основная цель
Создать автоматизированную систему для генерации product cards (карточек товаров) для маркетплейсов Wildberries, Ozon, Яндекс Маркет с использованием:
- Figma для дизайна
- Design Tokens для консистентности
- Python для batch automation
- Claude Code для AI-assisted development
- Telegram bot для workflow management

### Бизнес-контекст
**Текущая проблема:**
- Создание 100 карточек товаров = 100+ часов ручной работы дизайнера
- Стоимость: 200,000₽ за batch
- Высокий риск несоответствия требованиям модерации (WB отклоняет 40-50% первых загрузок)

**Желаемый результат:**
- Автоматизировать 80-90% работы
- Время генерации 100 карточек: <10 минут
- Стоимость: ~24,000₽ за batch (экономия 88%)
- Прохождение модерации с первого раза

### Технический контекст
**Stack пользователя:**
- Python 3.10+
- python-telegram-bot (Telegram боты)
- gspread (Google Sheets integration)
- PDF processing (reportlab, weasyprint)
- Автоматизация и batch processing

**НЕ дизайнер** - фокус на automation через код.

---

## ✅ CURRENT PROGRESS: Что уже сделано

### 1. Comprehensive Research (ЗАВЕРШЕНО)

**Проведено глубокое исследование:**
- 5 параллельных research agents
- 100+ источников (case studies, документация, GitHub repos)
- Международные и российские кейсы

**Сохранено в:**
`Projects/ResearchSystem/data/reports/report_20260215_figma_claude_code_workflows.md`

**Ключевые находки:**

#### Мировые кейсы
1. **Jane Street:** Designer использует Claude Code больше чем Figma для прототипирования
   - Результат: Improvements за часы вместо недель

2. **ABB Ltd. (Швейцария):** Design tokens для всех продуктов
   - Результат: 100% консистентность, single source of truth

3. **Hotmart & SoFi:** Enterprise design systems с measurable ROI

#### Российские кейсы (WB/Ozon)
1. **Nano Banana PRO:** Visual prompting для инфографики
   - Результат: 80% автоматизация типовых задач

2. **Fabula AI + Masha GPT:** Массовая генерация карточек
   - Результат: 100 часов → 10-15 часов (90% экономия)

3. **WB Academy:** Data-driven оптимизация с ростом CTR и продаж

#### Figma Community Resources
- [150+ Free Product Card Design](https://www.figma.com/community/file/1063006730597410035)
- [Шаблон Rich-контент WB + Ozon](https://www.figma.com/community/file/1476256480206228529)
- [WB/Ozon Card Preview](https://www.figma.com/community/file/1128576602487159614)
- [Мокапы маркетплейсов](https://www.figma.com/community/file/1482832335263496269)

### 2. Tokens Studio - Объяснено

**Что это:**
- Figma plugin для управления design tokens
- 264,000+ пользователей
- Экспорт в JSON для использования в коде

**Зачем нужно:**
```
Без токенов:
- Дизайнер меняет цвет в Figma
- Разработчик НЕ ЗНАЕТ об изменении
- Результат: разные цвета в дизайне и коде

С токенами:
- Дизайнер меняет токен в Figma
- Tokens Studio → автоматически обновляет GitHub
- CI/CD → генерирует новый tokens.json
- Код подтягивает изменения
- Результат: синхронизация автоматическая
```

**Установка:**
1. Figma → Resources (Shift+I) → Plugins
2. Поиск: "Tokens Studio for Figma"
3. Install/Run

### 3. Критические выводы из исследования

#### Вывод 1: Design System Maturity > Tool Choice
- Teams с mature design systems: 80-90% accuracy
- Teams без design systems: 60-70% accuracy
- **Инструмент усиливает систему, но не заменяет её**

#### Вывод 2: 80/20 Rule
- 80% времени дизайнера = routine tasks (автоматизируемо)
- 20% времени = creative work (требует человека)
- **Фокус на автоматизации 80%**

#### Вывод 3: AI для Прототипирования, Люди для Production
- AI отлично: variations on a theme
- Люди отлично: creating the theme
- **Best workflow:** Human → AI → Human → Production

#### Вывод 4: Tokens = Non-Negotiable для Scale
- Без токенов: Ребрендинг = 2-4 недели + 200,000₽
- С токенами: Ребрендинг = 1 час + 5,000₽
- **Экономия: 195,000₽ + 3.5 недели**

#### Вывод 5: Russian Market = Unique Constraints
**Wildberries:**
- Format: JPG only (PNG rejected)
- Size: 900x1200px (3:4 vertical)
- Text: Только русский
- Модерация: Очень строгая (отклоняют 40-50%)

**Ozon:**
- Format: JPG, PNG
- Size: 1200x1200px (1:1 square preferred)
- Text: Только русский
- Модерация: Средняя строгость

**НЕЛЬЗЯ просто взять international template - нужна адаптация.**

### 4. Рекомендованный Stack (определён)

```
Design:
├─ Figma Community templates (не создавать с нуля)
├─ Tokens Studio (Python-friendly JSON export)
└─ WB/Ozon mockups для validation

Automation:
├─ Python ProductCardGenerator class
├─ FigmaPy для API (optional)
└─ Telegram bot для workflow

Data:
├─ Google Sheets (master product list)
├─ gspread для integration
└─ JSON tokens для styling

Output:
├─ Multi-marketplace (WB/Ozon/Yandex)
├─ Batch processing (100+ cards)
└─ CI/CD ready (GitHub Actions potential)
```

### 5. План действий на 2 недели (создан)

**Week 1: Setup Foundation**
- Day 1-2: Design Tokens (Tokens Studio setup, базовые токены, export JSON)
- Day 3-4: Template Setup (download Community template, customize, 3 variants)
- Day 5: Python Script v1 (ProductCardGenerator class)
- Day 6-7: Batch Processing (Google Sheets integration, 10+ cards test)

**Week 2: Production Ready**
- Day 8-9: Multi-Marketplace (WB/Ozon/Yandex support)
- Day 10-11: Telegram Bot Integration (workflow automation)
- Day 12-14: Testing & Iteration (100 test cards, модерация validation)

**Deliverables:**
- Tokens система работает
- 100+ cards generated successfully
- Прошли модерацию WB/Ozon
- Telegram bot автоматизирует workflow
- Time per batch: <10 min (vs 100+ manual)

---

## ✅ WHAT WORKED: Подходы которые succeeded

### 1. Comprehensive Research Approach
**Что сделали:**
- 5 параллельных Task agents для разных направлений:
  1. Figma to Code workflows
  2. Plugins и автоматизация
  3. Design Systems + AI
  4. Реальные user cases
  5. Альтернативные инструменты

**Почему сработало:**
- Полное покрытие темы за 1 сессию
- Реальные кейсы с измеримыми результатами
- Баланс теории и практики

### 2. Focus на Практические Примеры
**Что сделали:**
- Нашли конкретные кейсы с ROI:
  - Nano Banana PRO: 80% automation
  - Fabula AI: 90% time savings
  - ABB Ltd: 100% consistency

**Почему сработало:**
- Измеримые результаты (не абстракции)
- Специфика для WB/Ozon (не generic советы)
- Ready-to-use workflows

### 3. Адаптация под Контекст Пользователя
**Что сделали:**
- Учли tech stack (Python 3.10+, Telegram, Google Sheets)
- Признали, что пользователь НЕ дизайнер
- Рекомендовали automation через код (его сила)

**Почему сработало:**
- Рекомендации aligned с его skills
- Играют на его сильные стороны (automation, Python)
- Realistic expectations

### 4. Готовые Resources
**Что предоставили:**
- Figma Community templates (не нужно создавать с нуля)
- Конкретные ссылки на инструменты
- Code examples (Python ProductCardGenerator)

**Почему сработало:**
- Низкий barrier to entry
- Можно начать немедленно
- Проверенные решения

---

## ❌ WHAT DIDN'T WORK: Подходы которые failed

### 1. WebFetch для некоторых источников
**Что пытались:**
- Fetch детальных case studies (Smallstep, Medium articles)

**Почему не сработало:**
- 403 errors (защита от scraping)

**Решение:**
- Использовали WebSearch вместо WebFetch
- Получили достаточно информации из search results

### 2. Попытка найти "идеальный case study"
**Что пытались:**
- Искали один comprehensive case study со всеми деталями

**Почему не сработало:**
- Таких единичных case studies не существует
- Информация распределена по множеству источников

**Решение:**
- Синтезировали информацию из 100+ источников
- Создали comprehensive отчёт самостоятельно

---

## 🚀 NEXT STEPS: Чёткие action items

### Immediate Actions (Сегодня/Завтра)

#### 1. Установить Tokens Studio Plugin
```
□ Открыть Figma (figma.com или desktop app)
□ Resources → Plugins → Поиск "Tokens Studio for Figma"
□ Install
□ Запустить плагин (правый клик → Plugins → Tokens Studio)
```

**Зачем:** Foundation для всей системы токенов

---

#### 2. Создать Базовые Design Tokens
```
□ В Tokens Studio создать группы:

  Colors:
  ├─ primary: #007BFF
  ├─ secondary: #6B7280
  ├─ background: #FFFFFF
  ├─ text: #1F2937
  └─ price-highlight: #EF4444

  Spacing:
  ├─ small: 8px
  ├─ medium: 16px
  ├─ large: 24px
  └─ xlarge: 32px

  Typography:
  ├─ title-size: 18px
  ├─ price-size: 24px
  └─ body-size: 16px

□ Export → JSON → Сохранить как tokens.json
□ Проверить структуру JSON
```

**Deliverable:** `tokens.json` файл с токенами

---

#### 3. Download Figma Community Template
```
□ Открыть: https://www.figma.com/community/file/1063006730597410035
□ Duplicate в свой Figma account
□ Или: https://www.figma.com/community/file/1476256480206228529 (WB/Ozon специфичный)
□ Изучить структуру template
```

**Зачем:** Не создавать дизайн с нуля, использовать проверенные templates

---

### Week 1 Actions (Days 1-7)

#### Day 1-2: Tokens Setup + Template Customization
```
□ Customize template с твоими tokens
□ Create 3 variants:
  ├─ WB: 900x1200px (3:4 vertical)
  ├─ Ozon: 1200x1200px (1:1 square)
  └─ Yandex: 1200x1200px (1:1 square)
□ Test export (JPG quality 90-95%, file size validation)
```

**Deliverable:** 3 template файла готовы

---

#### Day 3-5: Python Script v1
```
□ Создать ProductCardGenerator.py:

  class ProductCardGenerator:
      def __init__(self, tokens_path: Path):
          # Load tokens.json

      def get_token(self, path: str):
          # Extract token value

      def generate_wb_card(self, product: Dict, output: Path):
          # Generate 900x1200 JPG for WB

      def generate_ozon_card(self, product: Dict, output: Path):
          # Generate 1200x1200 for Ozon

      def batch_generate(self, products: List[Dict], marketplace: str, output_dir: Path):
          # Batch processing

□ Test с 1 product
□ Validate output (size, format, quality)
```

**Deliverable:** Working Python script генерирует 1 card

---

#### Day 6-7: Google Sheets Integration + Batch Test
```
□ Setup gspread authentication
□ Create load_products_from_sheets() function
□ Test Google Sheets → Python → Card generation
□ Batch test с 10 products
□ Measure performance (time per card)
```

**Deliverable:** Script генерирует 10+ cards за <5 min

---

### Week 2 Actions (Days 8-14)

#### Day 8-9: Multi-Marketplace Support
```
□ Implement все 3 marketplace formats
□ Validation function для модерация requirements:
  ├─ WB: JPG only, 900x1200, Russian text
  ├─ Ozon: JPG preferred, 1200x1200
  └─ Yandex: JPG, 1200x1200
□ Test export для каждого marketplace
```

**Deliverable:** Multi-marketplace generation working

---

#### Day 10-11: Telegram Bot Workflow
```
□ Create bot с python-telegram-bot
□ Implement commands:
  ├─ /generate_cards [count] - Generate batch
  ├─ /status - Check generation status
  └─ Inline buttons: Approve/Reject
□ Integration с ProductCardGenerator
□ Deploy bot (VPS или local)
```

**Deliverable:** Working Telegram bot для workflow automation

---

#### Day 12-14: Production Testing
```
□ Generate 100 test cards
□ Upload 10 to WB (test real moderation)
□ Upload 10 to Ozon
□ Collect feedback:
  ├─ Moderation pass rate
  ├─ Quality issues
  └─ Time measurements
□ Fix identified issues
□ Document final workflow
```

**Deliverable:** Production-ready system с documented workflow

---

### Success Metrics (Как измерить успех)

**Technical Metrics:**
```
✓ Tokens система load успешно в Python
✓ 100+ cards generated без errors
✓ All 3 marketplace formats work
✓ Moderation pass rate >90% (WB/Ozon)
```

**Business Metrics:**
```
✓ Time per batch: <10 min (baseline: 100+ hours)
✓ Cost per batch: <30,000₽ (baseline: 200,000₽)
✓ Time savings: >90%
✓ Cost savings: >85%
```

**User Experience Metrics:**
```
✓ Telegram bot responds <30 seconds
✓ Workflow requires <5 clicks
✓ No technical knowledge needed for manager
```

---

## 📁 KEY FILES & RESOURCES

### Created Files
1. **Research Report:**
   `Projects/ResearchSystem/data/reports/report_20260215_figma_claude_code_workflows.md`
   - 100+ источников
   - Реальные кейсы с метриками
   - Step-by-step workflows
   - Best practices и anti-patterns

2. **This Handoff:**
   `HANDOFF.md`
   - Контекст диалога
   - План действий
   - Next steps

### External Resources (Figma Community)
- [150+ Product Card Templates](https://www.figma.com/community/file/1063006730597410035)
- [WB + Ozon Rich-контент](https://www.figma.com/community/file/1476256480206228529)
- [WB/Ozon Card Preview](https://www.figma.com/community/file/1128576602487159614)
- [Marketplace Mockups](https://www.figma.com/community/file/1482832335263496269)

### Code Examples (To Create)
```
ProductCardGenerator.py        # Main class (to be created)
tokens.json                    # Design tokens export (to be created)
telegram_bot.py                # Workflow automation (to be created)
requirements.txt               # Dependencies (to be created)
```

### Dependencies (Install when ready)
```bash
pip install pillow              # Image processing
pip install gspread             # Google Sheets
pip install google-auth         # Google authentication
pip install python-telegram-bot # Telegram bot
pip install python-dotenv       # Environment variables
```

---

## 🎯 RECOMMENDED STARTING POINT

**Если начинаешь с нуля (новая сессия):**

1. **Прочитай Research Report:**
   `Projects/ResearchSystem/data/reports/report_20260215_figma_claude_code_workflows.md`
   - Понять context и best practices

2. **Начни с Day 1 плана:**
   - Установить Tokens Studio
   - Создать базовые токены
   - Export JSON

3. **Если застрял - обратись к:**
   - Секция "What Worked" (проверенные подходы)
   - Секция "Critical Выводы" (ключевые принципы)
   - Code examples в Research Report

4. **Используй ready resources:**
   - Не создавай дизайн с нуля
   - Download Community templates
   - Customize через tokens

---

## 💡 CRITICAL REMINDERS

### 1. Design System First
> "Design System Maturity > Tool Choice"

Не спеши с инструментами. Сначала создай структуру:
- Tokens
- Naming conventions
- Template

Потом automation будет легко.

### 2. Focus на Automation (твоя сила)
> "Ты Python expert, не дизайнер"

Играй на своих сильных сторонах:
- Batch processing
- API integration
- Telegram bots
- Google Sheets automation

### 3. Start Small, Scale Fast
> "1 template + 100 variations > 100 unique designs"

Week 1: 1 perfect template
Week 2: Generate 100+ cards автоматически

### 4. Russian Market Constraints
> "WB отклоняют 40-50% первых загрузок"

**ВСЕГДА проверяй:**
- WB: JPG, 900x1200, vertical, Russian only
- Ozon: 1200x1200, square preferred
- Use mockups для validation BEFORE upload

### 5. Measure Everything
> "Что не измеряешь - не улучшаешь"

Track:
- Time per batch (baseline vs automated)
- Moderation pass rate
- Cost savings
- Quality issues

---

## 🔄 CONTEXT RESTORATION (для следующей сессии)

**Чтобы восстановить контекст, скажи Claude:**

> "Прочитай HANDOFF.md и Projects/ResearchSystem/data/reports/report_20260215_figma_claude_code_workflows.md. Мы работаем над автоматизацией product cards для WB/Ozon. Текущий статус: [укажи где остановился]. Помоги мне с [конкретная задача]."

**Примеры:**

> "Прочитай HANDOFF.md. Я на Day 3 плана - создаю Python script. Покажи пример ProductCardGenerator class."

> "Прочитай HANDOFF.md. Установил Tokens Studio, создал токены. Как теперь интегрировать с Python?"

> "Прочитай HANDOFF.md и research report. Нужна помощь с модерацией WB - карточки отклоняют. Что проверить?"

---

## 📞 QUICK REFERENCE

### Key Concepts
- **Design Tokens:** Variables для дизайна (colors, spacing, typography)
- **Tokens Studio:** Figma plugin для управления токенами
- **Batch Processing:** Генерация 100+ cards автоматически из 1 template
- **Multi-Marketplace:** Support для WB/Ozon/Yandex (разные форматы)

### Critical Numbers
- **Time savings:** 100 hours → 10 min (99% reduction)
- **Cost savings:** 200,000₽ → 24,000₽ (88% reduction)
- **Automation level:** 80-90% tasks automated
- **WB moderation:** 40-50% rejection rate (first upload without validation)

### Tech Stack (Confirmed)
```
Python 3.10+
├─ Pillow (image processing)
├─ gspread (Google Sheets)
├─ python-telegram-bot (workflow)
└─ Design tokens (JSON)

Figma
├─ Tokens Studio plugin
├─ Community templates
└─ WB/Ozon mockups
```

---

## ✅ STATUS CHECK (Current State)

**Completed:**
- ✅ Comprehensive research (100+ sources)
- ✅ Best practices identified
- ✅ Workflows documented
- ✅ Plan created (2 weeks)
- ✅ Stack determined
- ✅ Resources collected

**In Progress:**
- ⏳ Nothing (waiting for implementation start)

**Blocked:**
- ❌ None

**Ready to Start:**
- ✅ All information gathered
- ✅ Plan ready
- ✅ Resources available
- ✅ **Можно начинать Day 1**

---

## 🎬 IMMEDIATE NEXT ACTION

**Прямо сейчас:**

1. Open Figma
2. Install Tokens Studio plugin
3. Create 5 basic tokens (colors)
4. Export tokens.json
5. Проверь, что JSON валидный

**Time estimate:** 30 minutes

**After that:** Continue to Day 1-2 из плана

---

**HANDOFF COMPLETE**
**Готов к продолжению в новой сессии**

---

_Создано: 15 февраля 2026_
_Последнее обновление: 15 февраля 2026_
_Версия: 1.0_
