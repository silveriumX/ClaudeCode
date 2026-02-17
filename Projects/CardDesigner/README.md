# CardDesigner

Система автоматического создания дизайнерских карточек товаров для маркетплейсов (Ozon, Wildberries).

## Описание

CardDesigner состоит из двух основных компонентов:

### 1. Image Processor
Предобработка изображений товаров:
- Удаление фона
- Нормализация размера и качества
- Обнаружение текста на изображении
- Улучшение качества (enhancer)
- Апскейлинг (опционально)

### 2. Design Composer
Создание финальных карточек:
- Анализ стиля товара
- Генерация AI фона (через Flux)
- Умный layout engine
- Рендеринг с текстом и элементами
- Валидация результата

## Структура

```
CardDesigner/
├── image_processor/      # Обработка изображений
│   ├── pipeline.py       # Основной пайплайн
│   ├── background_remover.py
│   ├── normalizer.py
│   ├── enhancer.py
│   └── upscaler.py
├── design_composer/      # Создание дизайна
│   ├── pipeline.py       # Design pipeline
│   ├── background_generator.py
│   ├── layout_engine.py
│   └── template_renderer.py
├── templates/            # Шаблоны карточек
└── test_output/          # Результаты
```

## Использование

```python
from image_processor import ImageProcessorPipeline
from design_composer import DesignComposerPipeline

# 1. Обработка изображения
processor = ImageProcessorPipeline()
processed_img = processor.process("input.png", "output/")

# 2. Создание карточки
composer = DesignComposerPipeline()
card = composer.create_card(processed_img, card_spec)
```

## Требования

- Python 3.10+
- PIL/Pillow
- AI модели для генерации фонов

## Конфигурация

См. `.env` файл для настройки API ключей генерации фонов.
