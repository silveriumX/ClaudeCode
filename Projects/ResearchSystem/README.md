# ResearchSystem

Система глубоких исследований с использованием AI агентов и множественных источников.

## Описание

ResearchSystem - это фреймворк для проведения комплексных исследований, который:
- Использует множественные источники данных (Exa, Firecrawl, web search)
- Координирует несколько AI агентов для параллельного поиска
- Синтезирует информацию из разных источников
- Генерирует структурированные отчеты

## Компоненты

### Core
- **Research Engine** - основной движок исследований
- **Agent Coordinator** - координация субагентов
- **Source Manager** - управление источниками
- **Report Generator** - создание отчетов

### Источники
- **Exa** - семантический поиск
- **Firecrawl** - глубокий анализ веб-страниц
- **Web Search** - традиционный поиск
- **Local Knowledge Base** - локальная база знаний

## Использование

```python
from research_system import ResearchEngine

# Создать движок
engine = ResearchEngine()

# Провести исследование
report = engine.research(
    query="Как работает технология X?",
    depth="deep",
    sources=["exa", "web", "firecrawl"]
)

# Сохранить отчет
report.save("data/reports/report_YYYYMMDD_topic.md")
```

## Структура

```
ResearchSystem/
├── config/              # Конфигурация
│   ├── mcp.json.example
│   ├── preferences.json.example
│   └── MCP_SETUP.md
├── data/
│   └── reports/         # Отчеты исследований
├── src/                 # Исходный код
└── docs/                # Документация
    ├── ARCHITECTURE.md
    ├── CONCEPTS_GUIDE.md
    └── MCP_UNIVERSAL_GUIDE.md
```

## Требования

- Python 3.10+
- Exa API (для семантического поиска)
- Anthropic API (для AI агентов)
- Firecrawl API (опционально)

## Конфигурация

1. Скопировать примеры конфигов:
   ```bash
   cp config/mcp.json.example config/mcp.json
   cp config/preferences.json.example config/preferences.json
   ```

2. Заполнить API ключи в `.env`

3. См. документацию:
   - `ARCHITECTURE.md` - архитектура системы
   - `CONCEPTS_GUIDE.md` - концепции и подходы
   - `MCP_UNIVERSAL_GUIDE.md` - интеграция с MCP

## Примеры отчетов

См. `data/reports/` для примеров сгенерированных исследований.

## Связанные Skills

- `/research-system` - запуск через Claude Code skill
