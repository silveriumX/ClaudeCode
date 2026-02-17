# Создание карточек товаров для маркетплейса

> Практический гайд по созданию карточек для Wildberries, Ozon, Яндекс.Маркет

---

## Требования маркетплейсов к изображениям

### Wildberries
```
Формат: PNG, JPEG
Размер: 900x1200px (рекомендуется)
Минимум: 450x600px
Максимум: 8000x8000px
Вес: до 10 МБ
Фон: белый (#FFFFFF) или прозрачный
```

### Ozon
```
Формат: PNG, JPEG
Размер: 1200x1200px (квадрат) или 1200x1600px (вертикальный)
Минимум: 200x200px
Вес: до 10 МБ
Фон: белый (#FFFFFF)
```

### Яндекс.Маркет
```
Формат: JPEG, PNG
Размер: от 600x600px до 8000x8000px
Вес: до 10 МБ
Соотношение: 1:1, 3:4, 4:3
```

---

## Шаблон карточки товара (Figma)

### Базовая структура

```
Frame: ProductCard
├─ Background (Rectangle) - белый фон
├─ ProductImage (Image placeholder)
├─ ProductName (Text)
├─ Price (Text)
├─ OldPrice (Text, зачёркнутый)
├─ Discount (Frame с процентом скидки)
├─ Badge (Frame - "Хит продаж", "Новинка", etc.)
└─ Logo (ваш логотип - опционально)
```

### Размеры для Wildberries (900x1200px)

```
Frame: 900x1200px
├─ Background: 900x1200, fill: #FFFFFF
├─ ProductImage: 800x800, position: x:50, y:50
├─ ProductName: width:800, y:880, font-size:32px
├─ Price: y:950, font-size:48px, bold, color:#000
├─ OldPrice: y:955, font-size:32px, strikethrough, color:#999
├─ Discount: 120x120, position: top-right, radius:60
└─ Logo: 150x50, position: bottom-center
```

---

## Автоматизация через Python

### Скрипт: Экспорт карточек товаров

```python
from pathlib import Path
import requests
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

FIGMA_API_TOKEN = os.getenv("FIGMA_API_TOKEN")
FIGMA_BASE_URL = "https://api.figma.com/v1"

def export_product_cards(
    file_key: str,
    frame_ids: list,
    output_dir: Path,
    format: str = "png",
    scale: int = 2
) -> list:
    """
    Экспортировать карточки товаров из Figma.

    Args:
        file_key: Figma file key
        frame_ids: Список node IDs карточек
        output_dir: Папка для сохранения
        format: png | jpg
        scale: 1-4 (2 = retina)

    Returns:
        Список путей к сохранённым файлам
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Получить URLs для экспорта
    url = f"{FIGMA_BASE_URL}/images/{file_key}"
    headers = {"X-Figma-Token": FIGMA_API_TOKEN}
    params = {
        "ids": ",".join(frame_ids),
        "format": format,
        "scale": str(scale)
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    image_urls = response.json().get("images", {})

    # Скачать изображения
    saved_files = []
    for i, (node_id, image_url) in enumerate(image_urls.items(), 1):
        if not image_url:
            logger.warning(f"No image URL for {node_id}")
            continue

        img_response = requests.get(image_url)
        img_response.raise_for_status()

        # Имя файла: product_001.png, product_002.png, etc.
        filename = f"product_{i:03d}.{format}"
        output_path = output_dir / filename
        output_path.write_bytes(img_response.content)

        saved_files.append(output_path)
        logger.info(f"✓ Экспортирован: {filename}")

    logger.info(f"\n✓ Экспортировано {len(saved_files)} карточек")
    return saved_files


def batch_export_by_pattern(
    file_key: str,
    frame_name_pattern: str,
    output_dir: Path
):
    """
    Экспортировать все frames по паттерну имени.

    Args:
        file_key: Figma file key
        frame_name_pattern: Паттерн имени (например, "ProductCard")
        output_dir: Папка для сохранения
    """
    # Получить структуру файла
    url = f"{FIGMA_BASE_URL}/files/{file_key}"
    headers = {"X-Figma-Token": FIGMA_API_TOKEN}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()

    # Найти все frames с нужным паттерном
    def find_frames(node, frames=[]):
        if node.get("type") == "FRAME" and frame_name_pattern in node.get("name", ""):
            frames.append(node["id"])

        for child in node.get("children", []):
            find_frames(child, frames)

        return frames

    frame_ids = find_frames(data["document"])

    logger.info(f"Найдено {len(frame_ids)} карточек с паттерном '{frame_name_pattern}'")

    if frame_ids:
        export_product_cards(file_key, frame_ids, output_dir)
    else:
        logger.warning("Карточки не найдены")


# Использование
if __name__ == "__main__":
    FILE_KEY = "UQqv5JHrrB1WtU6I7l0xNr"  # NEXR STORE3 Red
    OUTPUT = Path("exports/product_cards")

    # Вариант 1: Экспорт конкретных frames
    frame_ids = ["49:2"]  # Frame "5"
    export_product_cards(FILE_KEY, frame_ids, OUTPUT, format="png", scale=2)

    # Вариант 2: Экспорт всех frames с паттерном
    # batch_export_by_pattern(FILE_KEY, "ProductCard", OUTPUT)
```

---

## Workflow: От данных к карточкам

### Шаг 1: Подготовить данные товаров

**Google Sheets / Excel:**
```
| ID  | Название                | Цена  | Старая цена | Скидка | Фото URL              |
|-----|-------------------------|-------|-------------|--------|-----------------------|
| 001 | Футболка мужская       | 1290  | 1990        | 35%    | https://...img1.jpg   |
| 002 | Джинсы женские         | 2490  | 3490        | 29%    | https://...img2.jpg   |
| 003 | Кроссовки спортивные   | 3990  | 5990        | 33%    | https://...img3.jpg   |
```

### Шаг 2: Создать шаблон в Figma

1. Frame 900x1200px (Wildberries)
2. Placeholder для фото
3. Text fields: {название}, {цена}, {старая_цена}
4. Discount badge: {скидка}

### Шаг 3: Автоматизация (опции)

**Вариант A: Automator Plugin**
1. Установить Automator
2. Импортировать CSV
3. Автоматически создать варианты
4. Экспортировать batch

**Вариант B: Python скрипт**
1. Прочитать Google Sheets
2. Для каждого товара:
   - Создать frame в Figma (или дублировать шаблон)
   - Вставить данные
   - Экспортировать PNG

**Вариант C: Figma Variables (новая фича)**
1. Создать variables для текста
2. Связать с data source
3. Режим bulk edit
4. Batch export

---

## Размеры для всех маркетплейсов

### Универсальный размер (подходит везде):
```
1200x1600px (3:4)
- Wildberries: ✓
- Ozon: ✓
- Яндекс.Маркет: ✓
- Alibaba: ✓
```

### Оптимизация по платформе:

**Wildberries:**
- Main image: 900x1200px
- Additional: 900x1200px (до 30 шт)

**Ozon:**
- Main: 1200x1200px (квадрат)
- 360°: 1200x1200px (от 5 до 70 шт)
- Infographic: 1200x1600px

**Яндекс.Маркет:**
- Main: 1200x1200px или 1200x1600px
- Additional: те же размеры

---

## Чеклист карточки товара

### Обязательные элементы:
- [ ] Фото товара на белом фоне
- [ ] Название товара (читаемо)
- [ ] Цена (крупно, контрастно)
- [ ] Размер изображения соответствует требованиям

### Опциональные элементы:
- [ ] Старая цена (зачёркнутая)
- [ ] Процент скидки (badge)
- [ ] Логотип бренда
- [ ] "Хит продаж" / "Новинка" (badge)
- [ ] Размерная сетка (для одежды)
- [ ] Состав ткани (для одежды)

### Технические требования:
- [ ] Формат: PNG или JPEG
- [ ] Размер: 900x1200 или 1200x1200
- [ ] Вес: < 10 МБ
- [ ] DPI: 72 (для web)
- [ ] Color mode: RGB

---

## Инструменты для автоматизации

### Figma Plugins для карточек товаров:

1. **Automator** - batch операции
2. **Content Reel** - вставка изображений
3. **Google Sheets Sync** - синхронизация данных
4. **Figma to HTML** - если нужен web (НЕ для маркетплейса)

### Python библиотеки:

1. **figmapy** - работа с Figma API
2. **gspread** - чтение Google Sheets
3. **Pillow** - обработка изображений
4. **requests** - HTTP запросы

---

## FAQ

### Q: Сколько карточек можно создать за раз?
**A:**
- Вручную: 5-10/час
- Automator plugin: 100+/час
- Python автоматизация: 1000+/час

### Q: Можно ли автоматически загружать на маркетплейс?
**A:** Да, через API:
- Wildberries API
- Ozon Seller API
- Яндекс.Маркет API

### Q: Нужен ли дизайнер?
**A:**
- Шаблон - да (один раз)
- Наполнение - нет (автоматизация)

### Q: Какой формат лучше - PNG или JPEG?
**A:**
- PNG - если нужна прозрачность или высокое качество
- JPEG - для обычных фото (меньше вес)

---

## Примеры готовых решений

### Шаблон карточки Wildberries (900x1200):
```
Background: #FFFFFF
Product photo: 800x800, centered top
Name: 32px, bold, black, centered
Price: 48px, bold, black
Old price: 32px, strikethrough, gray
Discount badge: top-right corner, 120x120, red circle
```

### Шаблон Ozon (1200x1200):
```
Background: #FFFFFF
Product photo: 1000x1000, centered
Name: below photo, 36px
Price: 52px, blue (#005BFF)
```

---

**Следующий шаг:** Определите объём карточек → выберу оптимальный инструмент
