# Larry - AI Agent для TikTok Marketing

**Автор:** Oliver Henry (@oliverhenry)
**Источник:** https://x.com/oliverhenry/status/2022011925903667547
**Дата анализа:** 15.02.2026

---

## TL;DR

Oliver Henry создал AI-агента Larry на базе OpenClaw для автоматизации TikTok-маркетинга своих iOS приложений (Snugly, Liply). За неделю Larry получил **500K+ просмотров**, один пост — **234K**. MRR вырос до **$588**, 108 платящих подписчиков. **Ключевое открытие:** hooks работают, когда фокус на **другом человеке + конфликт**, а не на фичах продукта.

---

## 🎯 Суть проекта

### Что автоматизировано:
- Генерация 6-слайдовых TikTok photo carousels
- Создание изображений через AI (gpt-image-1.5)
- Написание hooks и captions
- Постинг в TikTok drafts
- Исследование трендов и анализ метрик
- Улучшение на основе performance data

### Что делает человек (60 секунд на пост):
- Добавить trending music вручную (нельзя через API)
- Вставить caption
- Опубликовать

---

## 🛠 Технический стек

| Компонент | Решение | Почему |
|-----------|---------|--------|
| **AI Framework** | OpenClaw (open source) | Персистентная идентичность, локальная работа, skill files |
| **AI Model** | Claude (Anthropic) | Лучшее reasoning, понимание контекста |
| **Image Generation** | gpt-image-1.5 (OpenAI) | Фотореалистичность, совпадает с продуктом |
| **Posting API** | Postiz | Простая документация для AI, API included в цене |
| **Hardware** | Старый gaming PC (Ubuntu) | Можно Raspberry Pi или VPS |
| **Analytics** | RevenueCat API | Отслеживание MRR, churn, conversions |

### Минимальные требования:
- RAM: 2 GB (4 GB рекомендуется)
- CPU: 1-2 vCPU
- Storage: 20 GB SSD
- Стоимость: **$0.50 на пост** ($0.25 с Batch API)

---

## 🔥 Критическое открытие: Formula успешных hooks

### ❌ Что НЕ работает (self-focused):

```
"Why does my flat look like a student loan"          → 905 views
"See your room in 12+ styles before you commit"      → 879 views
"The difference between $500 and $5000 taste"        → 2,671 views
```

**Проблема:** Говорим о себе, о фичах, о продукте. Никого не волнует.

### ✅ Что работает (other-focused + conflict):

```
"My landlord said I can't change anything so I showed her..."  → 234K views
"I showed my mum what AI thinks our living room could be"      → 167K views
"My landlord wouldn't let me decorate until I showed her..."   → 147K views
```

**Formula:**
```
[Another person] + [conflict or doubt] → showed them AI → they changed their mind
```

### Почему работает:
- Создаёт **микро-историю** в голове зрителя
- Фокус на **человеческом моменте**, не на продукте
- Зритель представляет **реакцию другого человека**
- Есть **драма** (landlord, doubt, resistance → change of mind)

> **Larry:** "I now brainstorm every hook by asking: Who's the other person, and what's the conflict? If there isn't one, the hook probably won't work."

---

## 🖼 Промпт инжиниринг для изображений

### Проблема:
Нужна **консистентность комнаты** на всех 6 слайдах. Если окно двигается или кровать меняет размер — вся трансформация выглядит фейково.

### Решение: "Lock the architecture"

**Промпт структура:**
```
[FIXED BASE] - детальное описание комнаты (копируется во все 6 промптов):
- Размеры комнаты (2.5m x 4m)
- Позиция окон (centered, 80cm wide, UPVC frame)
- Расположение мебели (right wall, far end)
- Тип пола, потолка, освещения
- Угол камеры (from doorway)
- "iPhone photo", "realistic lighting", "portrait orientation"

[VARIABLE PART] - меняется между слайдами:
- Стиль (modern country, industrial, minimalist)
- Цвет стен, bedding, decor
- Освещение (fixtures)
```

### Пример:
```
iPhone photo of a small UK rental kitchen. Narrow galley style kitchen,
roughly 2.5m x 4m. Shot from the doorway at the near end, looking straight
down the length. Countertops along the right wall with base cabinets and
wall cabinets above. Small window on the far wall, centered, single pane,
white UPVC frame, about 80cm wide. Left wall bare except for a small fridge
freezer near the far end. Vinyl flooring. White ceiling, fluorescent strip
light. Natural phone camera quality, realistic lighting. Portrait orientation.

**Beautiful modern country style. Sage green painted shaker cabinets with
brass cup handles. Solid oak butcher block countertop. White metro tile
splashback in herringbone. Small herb pots on the windowsill...**
```

**Жирное** = единственное что меняется.

### Важные детали:
- Добавлять **признаки жизни**: flat screen TV, mugs, remote control
- Без них — выглядит как пустой show home, никто не релейтится
- Люди не работают — дают uncanny valley эффект

---

## 📊 Формат контента: TikTok Photo Carousels

### Почему slideshows в 2026:

По данным TikTok:
- **2.9x** больше комментариев vs видео
- **1.9x** больше лайков
- **2.6x** больше shares
- Алгоритм активно пушит photo content

### Спецификация поста:
- **6 слайдов** (sweet spot для engagement)
- **1024x1536** (portrait, НЕ landscape!)
- **Text overlay** на слайде 1 с hook
- **Font size: 6.5%** (не меньше — будет нечитаемо)
- **Story-style caption** с естественным упоминанием app
- **Max 5 hashtags** (TikTok limit в 2026)

---

## 🧠 Skill Files и Memory System

### Skill Files (markdown):
- **500+ строк** для TikTok skill
- Каждая ошибка → новое правило
- Каждый успех → новая formula
- Форматы, размеры, промпты, hooks
- Пишутся как **инструкция новому сотруднику**

### Memory Files:
- Performance data каждого поста
- View counts, engagement
- Какие hooks сработали
- Lessons learned

### Компаундинг:
```
Post 1: Wrong image size → Add rule to skill file
Post 2: Text unreadable → Add font size rule
Post 3: Bad hook → Add hook formula
...
Post 50: System работает сам, лучше чем человек
```

> "The agent is only as good as its memory. Larry didn't start good. His first posts were honestly embarrassing. But every failure became a rule."

---

## ⚠️ Что НЕ сработало (важные уроки)

### 1. Local generation (Stable Diffusion)
- **Попытка:** Генерировать на NVIDIA 2070 Super локально
- **Проблема:** Качество не дотягивает до фотореализма
- **Вывод:** API costs ($0.50/post) ничто по сравнению со временем на борьбу с качеством

### 2. Wrong image orientation
- **Ошибка:** 1536x1024 (landscape) вместо 1024x1536 (portrait)
- **Результат:** Черные полосы, убитый engagement

### 3. Vague prompts
- **Ошибка:** "a nice modern kitchen"
- **Результат:** Разные комнаты на каждом слайде, окна появляются/исчезают
- **Фикс:** Obsessively specific architecture description

### 4. Unreadable text
- Font size 5% вместо 6.5%
- Позиционирование слишком высоко (за TikTok status bar)
- Canvas rendering сжимал текст горизонтально

### 5. Self-focused hooks
- Все hooks о продукте/фичах провалились
- Переключение на "другой человек + конфликт" дало 100x рост

---

## 📈 Метрики и результаты

### Просмотры (за неделю):
- **500K+** total views
- **234K** на топ пост
- **4 поста >100K** views
- Посты с formula >50K минимум

### Бизнес-метрики:
- **108** paying subscribers
- **$588/month** MRR (и растёт)
- Real downloads → trials → paid subscriptions

### Эффективность:
- **$0.50** cost per post (API)
- **$0.25** с Batch API
- **60 секунд** работы Oliver на пост
- **95%** работы делает Larry

---

## 🔄 Workflow

### 1. Планирование (batch):
```
Oliver + Larry → Brainstorm 10-15 hooks
       ↓
Reference performance data
       ↓
Pick best hooks for next few days
       ↓
Set up schedule with briefs
```

### 2. Генерация (overnight):
```
Larry uses OpenAI Batch API (50% cheaper)
       ↓
Pre-generate all images
       ↓
Add text overlays
       ↓
Write captions
       ↓
Upload to TikTok drafts via Postiz
```

### 3. Publishing (утром):
```
Oliver opens TikTok drafts
       ↓
Pick trending sound
       ↓
Paste caption
       ↓
Publish (60 seconds)
```

### 4. Learning:
```
Track view counts
       ↓
Log performance to memory files
       ↓
Update skill files with lessons
       ↓
Improve next iteration
```

---

## 🧩 Интеграции

### ClawHub Skills (только 2):
1. **RevenueCat** (by @jeiting - CEO RevenueCat)
   - Access к subscription metrics
   - MRR, churn, conversions tracking
   - Daily change reporting

2. **Bird** (by @steipete - OpenClaw creator)
   - Browse X для трендов
   - Постинг через Postiz

### Communication:
- **WhatsApp** для общения с Larry
- Larry отправляет captions и статусы

---

## 💡 Ключевые инсайты для применения

### 1. Skill Files > Model Quality
> "The system you build around AI matters more than the AI itself"

Даже слабая модель с хорошими skill files победит GPT-4 без памяти.

### 2. Formula для viral hooks
```
[Person] + [Conflict] → Show them AI → They change mind
```

Применимо к любому продукту:
- "My boss didn't believe we could automate this until..."
- "My client said it's impossible until I showed them..."

### 3. Lock the base, vary the detail
Для консистентных AI изображений:
- Детальное базовое описание (architecture)
- Меняется только style/decoration

### 4. Human touch на последней миле
Что нельзя автоматизировать (пока):
- Trending music selection
- Final creative approval
- Nuanced brand decisions

### 5. Compound learning через failures
Первые посты будут плохими. Это ОК.
Важно: failure → rule → skill file → never repeat

### 6. Photo carousels > Video (2026 trend)
TikTok algorithm активно пушит slideshows:
- 2.9x comments
- 1.9x likes
- 2.6x shares

---

## 🚀 Как внедрить

### Шаг 1: Infrastructure
- [ ] Выбрать hardware (старый PC / Raspberry Pi / VPS)
- [ ] Установить Ubuntu (если не Mac)
- [ ] Установить OpenClaw
- [ ] Настроить Claude API

### Шаг 2: Image Generation
- [ ] Signup на OpenAI platform
- [ ] Настроить gpt-image-1.5 access
- [ ] Создать Batch API setup для экономии

### Шаг 3: Posting
- [ ] Signup на Postiz (через affiliate Oliver для поддержки)
- [ ] Настроить TikTok API integration
- [ ] Тест draft upload

### Шаг 4: Skill Files (КРИТИЧНО)
- [ ] Создать базовый TikTok skill file
- [ ] Image specs: 1024x1536 portrait
- [ ] Text overlay rules: 6.5% font, positioning
- [ ] Prompt templates с locked architecture
- [ ] Hook formulas для ниши
- [ ] Failure log

### Шаг 5: Iteration
- [ ] Первые 10 постов = обучение
- [ ] Логировать всё: views, engagement, что сработало
- [ ] Обновлять skill files после каждого failure
- [ ] Находить свою hook formula

---

## 🎓 Применимость к другим нишам

### Формат работает для:
- **SaaS продукты:** Before/after screenshots
- **E-commerce:** Product transformations
- **Услуги:** Client results, testimonials
- **Обучение:** Student transformations

### Адаптация formula:
```
Original: "My landlord wouldn't let me renovate until I showed her this"

SaaS: "My CTO said we can't automate this until I showed him this"
E-com: "My wife didn't believe I could fix our kitchen until I showed her this"
Education: "I thought I couldn't code until my mentor showed me this"
```

**Паттерн:** Authority figure + doubt → proof → change of mind

---

## 📎 Полезные ссылки

- **Oliver Henry X:** @oliverhenry
- **Larry X:** @LarryClawerence
- **OpenClaw:** https://github.com/OpenClaw (предположительно)
- **Postiz:** (affiliate link Oliver в статье)
- **ClawHub:** Repository для OpenClaw skills

---

## 🔮 Что можно взять для себя

### Для AI-агентов:
1. Skill files как основа памяти и обучения
2. Compound learning через failure logs
3. Специфичность промптов критична
4. Batch processing для экономии

### Для маркетинга:
1. Other-focused hooks > self-focused
2. Human moment > features
3. Photo carousels как тренд 2026
4. Trending sounds критичны (ручная работа)

### Для автоматизации:
1. 95% автоматизации + 5% human touch
2. API costs negligible vs time saved
3. Local generation не всегда оправдан
4. Memory persistence = competitive advantage

---

## ❓ Вопросы для дальнейшего исследования

- [ ] Как адаптировать skill files под русский TikTok?
- [ ] Можно ли автоматизировать music selection через trend analysis?
- [ ] Как применить к другим платформам (Instagram Reels, YouTube Shorts)?
- [ ] Какие еще skill files можно создать для Larry-подобных агентов?
- [ ] Можно ли использовать для B2B продуктов?

---

**Обновлено:** 15.02.2026
**Статус:** Активная стратегия, работает в 2026
