# 🗺️ Навигационная карта проекта

> **Для AI:** При поиске файлов смотри сначала индексы: `Projects/INDEX.md`, `Scripts/INDEX.md`, `Work/INDEX.md`.

## 🚀 Быстрый старт

### Я хочу...

#### 💻 Работать с кодом
- **Запустить готовый проект** → `Projects/{название}/`
- **Найти скрипт ProxyMA** → `Scripts/ProxyMA/`
- **Найти скрипт Hub** → `Scripts/Hub/`
- **Работать с Google Sheets** → `Scripts/GoogleSheets/`

#### 📖 Читать документацию
- **API документация** → `Documentation/API/`
- **Настройка GitHub** → `Documentation/GitHub/`
- **Работа с Cursor** → `Documentation/Cursor/`
  - **Quality Workflow** → `Documentation/Cursor/QUALITY_WORKFLOW_GUIDE.md` ⭐ NEW
- **Принципы архитектуры** → `Documentation/DECENTRALIZED_ARCHITECTURE_PRINCIPLES.md`

#### ✅ Планировать работу
- **Посмотреть задачи** → `Work/Задачи/Задачи.md`
- **План на сегодня** → `Work/Задачи/План на {дата}.md`
- **Зарплаты** → `Work/Зарплаты/`

#### 🔧 Использовать утилиты
- **Автокоммит** → `Utils/auto_commit.ps1`
- **Работа с VPS** → `Utils/read_vps_file.ps1`

#### 📊 Работать с данными
- **Данные серверов** → `Data/servers_data.{csv|json}`
- **Данные ProxyMA** → `Data/proxyma_data_complete.json`

#### 🎙️ Записи встреч (Fireflies)
- **Список встреч** → `Fireflies/INDEX.md`
- **Встречи по дате** → `Fireflies/2026-01-*.md`

---

## 📂 Структура в один взгляд

```
Cursor/
│
├── 📦 Projects/              ← Готовые проекты
│   ├── CreatorBot
│   ├── VoiceBot
│   ├── USDT_Parser
│   └── WB_Management
│
├── 🔧 Scripts/               ← Рабочие скрипты
│   ├── ProxyMA       (14 файлов)
│   ├── Hub           (5 файлов)
│   ├── Traffic       (7 файлов)
│   ├── GoogleSheets  (2 файла)
│   └── Server        (3 файла)
│
├── 📚 Documentation/         ← Документация
│   ├── API           (5 файлов)
│   ├── GitHub        (10 файлов)
│   ├── Cursor        (2 файла)
│   └── Team          (1 файл)
│
├── 💼 Work/                  ← Рабочие документы
│   ├── Задачи        (9 файлов)
│   ├── Зарплаты      (1 файл)
│   └── Фабрика решений
│
├── 👤 Личное/                ← Личные заметки (объединённая папка)
│   ├── Notes         (заметки с клодом, дневниковые по датам)
│   ├── VoiceNotes    (голосовые, action plan)
│   ├── Психология_и_ментальное
│   ├── Здоровье, Уход_за_кожей, Стиль_и_внешность
│   ├── Идеи_и_желания, Рисование
│   └── INDEX.md, CONTEXT_INDEX.md, LIFE_CONTEXT_SYSTEM.md
│
├── 💾 Data/                  ← Данные
│   └── (3 файла)
│
├── 🎙️ Fireflies/             ← Записи встреч (транскрипты, саммари)
│   └── INDEX.md + встречи по дате
│
└── 🛠️ Utils/                 ← Утилиты
    └── (4 файла)
```

---

## 🎯 Сценарии использования

### Сценарий 1: Новый рабочий день
```
1. Work/Задачи/План на {дата}.md     ← Смотрю план
2. Scripts/{категория}/               ← Запускаю нужные скрипты
3. Work/Задачи/Задачи.md              ← Обновляю статус
```

### Сценарий 2: Работа с API
```
1. Documentation/API/                 ← Читаю документацию
2. Scripts/ProxyMA/                   ← Запускаю скрипты
3. Data/                              ← Проверяю результаты
```

### Сценарий 3: Новый проект
```
1. Projects/{новый_проект}/           ← Создаю папку
2. Documentation/                     ← Документирую
3. Scripts/                           ← Добавляю скрипты (если нужно)
```

### Сценарий 4: Командная работа
```
1. Documentation/GitHub/              ← Читаю инструкции
2. Documentation/Team/                ← Общие документы
3. Work/Задачи/                       ← Синхронизирую задачи
```

---

## 🔥 Горячие файлы

Самые часто используемые файлы для быстрого доступа:

| Файл | Путь | Назначение |
|------|------|------------|
| **Текущие задачи** | `Work/Задачи/Задачи.md` | Список всех задач |
| **План на сегодня** | `Work/Задачи/План на {дата}.md` | Ежедневный план |
| **ProxyMA API** | `Documentation/API/PROXYMA_API_FINAL_REPORT.md` | Итоговая документация API |
| **Google Sheets** | `Documentation/API/GOOGLE_SHEETS_INTEGRATION.md` | Интеграция с таблицами |
| **GitHub Setup** | `Documentation/GitHub/GITHUB_SETUP.md` | Настройка GitHub |
| **Данные серверов** | `Data/servers_data.csv` | База серверов |

---

## 💡 Советы по навигации

✅ **Используйте Ctrl+P** в Cursor для быстрого поиска файлов
✅ **Добавьте в закладки** часто используемые файлы
✅ **Следуйте структуре** при создании новых файлов
✅ **Обновляйте README** при добавлении важных файлов

---

## 🏷️ Соглашения об именовании

- **Проекты**: `PascalCase` (CreatorBot, VoiceBot)
- **Скрипты**: `snake_case` (proxyma_api.py, check_hub.ps1)
- **Документация**: `UPPER_SNAKE_CASE.md` (API_REPORT.md)
- **Планы**: `План на ДД.ММ.ГГГГ.md`

---

**Последнее обновление**: 18.01.2026
