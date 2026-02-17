# Как использовать Claude Vision: полное руководство

## Часть 1: Настройка и базовое использование

### Что нужно для работы

✅ **Да, достаточно только API Anthropic:**
1. Ключ API от Anthropic (https://console.anthropic.com/)
2. Библиотека `anthropic` для Python (или прямые HTTP-запросы)
3. Всё. Никаких дополнительных сервисов.

**Установка:**
```bash
pip install anthropic
```

**Получение API-ключа:**
1. Зарегистрируйтесь на https://console.anthropic.com/
2. Settings → API Keys → Create Key
3. Сохраните ключ (показывается один раз!)
4. Первые $5 бесплатно для тестирования

---

## Часть 2: Работа с изображениями

### Вариант 1: Локальное изображение (base64)

```python
import anthropic
import base64
from pathlib import Path

# Инициализация клиента
client = anthropic.Anthropic(
    api_key="sk-ant-api03-..."  # ваш ключ
)

# Загрузка и кодирование изображения
image_path = Path("product_photo.jpg")
image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")

# Запрос к Claude
message = client.messages.create(
    model="claude-sonnet-4-20250514",  # или claude-opus-4-6
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",  # или image/png, image/webp, image/gif
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Опиши этот товар. Какие характеристики видны на изображении?"
                }
            ],
        }
    ],
)

print(message.content[0].text)
```

### Вариант 2: Изображение по URL

```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://example.com/product.jpg",
                    },
                },
                {
                    "type": "text",
                    "text": "Что это за товар?"
                }
            ],
        }
    ],
)
```

### Вариант 3: Через Files API (для многократного использования)

**Шаг 1: Загрузить файл**
```python
# Загрузка файла в Files API
with open("product.jpg", "rb") as f:
    file_response = client.files.create(
        file=f,
        purpose="user_uploaded"
    )

file_id = file_response.id  # Сохраните для повторного использования
print(f"File uploaded: {file_id}")
```

**Шаг 2: Использовать file_id в запросах**
```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "file",
                        "file_id": file_id,
                    },
                },
                {
                    "type": "text",
                    "text": "Извлеки характеристики товара."
                }
            ],
        }
    ],
)
```

**Преимущества Files API:**
- Загружаете один раз, используете много раз
- Не нужно каждый раз кодировать base64
- Экономия на времени и трафике

---

## Часть 3: Работа с PDF и документами

### ✅ Claude поддерживает PDF нативно!

**Форматы:**
- PDF (до 100 страниц, до 32MB)
- DOCX, CSV, TXT, HTML, ODT, RTF, EPUB, JSON, XLSX

**Возможности с PDF:**
- Извлечение текста
- Анализ таблиц и графиков
- Понимание визуального контента (диаграммы, схемы)
- Перевод документов
- Преобразование в структурированные форматы

### Способы передачи PDF

#### Способ 1: PDF по URL

```python
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",  # для PDF используем "document", не "image"
                    "source": {
                        "type": "url",
                        "url": "https://example.com/specifications.pdf",
                    },
                },
                {
                    "type": "text",
                    "text": "Извлеки все технические характеристики из этого PDF в формате JSON."
                }
            ],
        }
    ],
)
```

#### Способ 2: Локальный PDF (base64)

```python
import base64
from pathlib import Path

# Загрузка и кодирование PDF
pdf_path = Path("product_specs.pdf")
pdf_data = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")

message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Проанализируй этот документ и извлеки ключевые данные."
                }
            ],
        }
    ],
)
```

#### Способ 3: PDF через Files API

```python
# Загрузка PDF
with open("manual.pdf", "rb") as f:
    file_response = client.files.create(
        file=f,
        purpose="user_uploaded"
    )

# Использование
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "file",
                        "file_id": file_response.id,
                    },
                },
                {
                    "type": "text",
                    "text": "Какие основные инструкции в этом руководстве?"
                }
            ],
        }
    ],
)
```

---

## Часть 4: Извлечение структурированных данных

### Для товарных карточек: получение JSON

```python
import json

# Промпт для структурированного вывода
prompt = """Проанализируй это фото товара и извлеки характеристики в формате JSON:

{
  "category": "тип товара (например: пылесос, чайник, утюг)",
  "brand": "бренд (если виден)",
  "model": "модель (если видна)",
  "power_w": число или null (мощность в ваттах),
  "power_pa": число или null (всасывание в Па, для пылесосов),
  "voltage": число или null (напряжение в вольтах),
  "capacity_ml": число или null (объём в мл),
  "runtime_min": число или null (время работы в минутах),
  "accessories_count": число или null (количество насадок/аксессуаров),
  "features": ["список применений или особенностей"],
  "visible_text": "весь текст, который видно на товаре или упаковке"
}

Отвечай ТОЛЬКО валидным JSON, без дополнительных комментариев."""

image_data = base64.b64encode(Path("vacuum.jpg").read_bytes()).decode()

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data,
                    },
                },
                {"type": "text", "text": prompt}
            ],
        }
    ],
)

# Парсинг JSON из ответа
response_text = message.content[0].text
product_data = json.loads(response_text)
print(product_data)
```

### Улучшенная версия: через Tool Use (гарантия JSON)

```python
# Определяем tool (схему данных)
tools = [
    {
        "name": "extract_product_specs",
        "description": "Извлекает характеристики товара из изображения",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Категория товара"
                },
                "brand": {
                    "type": "string",
                    "description": "Бренд"
                },
                "power_w": {
                    "type": "number",
                    "description": "Мощность в ваттах"
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список применений или особенностей"
                }
            },
            "required": ["category"]
        }
    }
]

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Извлеки характеристики этого товара используя tool extract_product_specs."
                }
            ],
        }
    ],
)

# Claude вернёт tool_use с гарантированной структурой
for block in message.content:
    if block.type == "tool_use":
        product_specs = block.input
        print(json.dumps(product_specs, indent=2, ensure_ascii=False))
```

---

## Часть 5: Продвинутые сценарии

### Несколько изображений за раз

```python
# Можно передавать до 20 изображений (claude.ai) или 100 (API)
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image1_data}},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image2_data}},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image3_data}},
                {
                    "type": "text",
                    "text": "Сравни эти три товара. Какой лучше по характеристикам?"
                }
            ],
        }
    ],
)
```

### Комбинация изображения + PDF

```python
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": product_photo_data}
                },
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": manual_pdf_data}
                },
                {
                    "type": "text",
                    "text": "Сравни товар на фото с описанием в PDF. Соответствуют ли характеристики?"
                }
            ],
        }
    ],
)
```

### Prompt Caching (для многократных запросов к одному документу)

```python
# Для экономии при повторных запросах к одному PDF/изображению
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                    "cache_control": {"type": "ephemeral"}  # Кэшировать этот документ
                },
                {"type": "text", "text": "Вопрос 1: Какая гарантия?"}
            ],
        }
    ],
)

# Второй запрос к тому же документу — будет использован кэш
message2 = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                    "cache_control": {"type": "ephemeral"}
                },
                {"type": "text", "text": "Вопрос 2: Какая мощность?"}
            ],
        }
    ],
)
# Второй запрос будет дешевле благодаря кэшу!
```

---

## Часть 6: Лимиты и стоимость

### Лимиты

| Параметр | Значение |
|----------|----------|
| Размер одного изображения | до 8000×8000 px (рекомендуется ~1200×1600) |
| Размер PDF | до 32MB |
| Количество страниц PDF | до 100 (текст+изображения), 1000+ (только текст) |
| Изображений в одном запросе | до 100 (API), до 20 (claude.ai) |
| Размер всего запроса | 32MB |

### Стоимость (Claude 3.5 Sonnet)

**Изображения:**
- ~1 Мп изображение ≈ 1600 токенов
- Цена: $3 за 1M входных токенов
- **1 фото ≈ $0.0048**

**PDF:**
- Текст: 1500-3000 токенов на страницу
- Каждая страница как изображение: +1600 токенов
- Пример: PDF на 10 страниц ≈ 20,000-30,000 токенов ≈ $0.06-0.09

**Кэширование:**
- При повторных запросах к закэшированному контенту — скидка 90%

---

## Часть 7: Обработка ошибок и best practices

### Обработка ошибок

```python
from anthropic import APIError, APIConnectionError, RateLimitError

try:
    message = client.messages.create(...)
except RateLimitError as e:
    print(f"Превышен лимит запросов: {e}")
    # Подождать и повторить
except APIConnectionError as e:
    print(f"Ошибка соединения: {e}")
    # Повторить запрос
except APIError as e:
    print(f"API ошибка: {e}")
```

### Best Practices

**Для изображений:**
1. ✅ Размещайте изображения **перед** текстом в content
2. ✅ Используйте чёткие, неразмытые фото
3. ✅ Убедитесь, что текст на фото читаем (не слишком мелкий)
4. ✅ Оптимизируйте размер: ~1200×1600 px достаточно
5. ✅ Используйте Files API для повторно используемых изображений

**Для PDF:**
1. ✅ Размещайте PDF перед вопросами
2. ✅ Используйте стандартные шрифты
3. ✅ Убедитесь, что PDF не зашифрован
4. ✅ Для больших документов (>100 страниц) делите на части
5. ✅ Включайте Prompt Caching для повторных вопросов

**Для структурированных данных:**
1. ✅ Используйте Tool Use для гарантии JSON-схемы
2. ✅ Явно указывайте формат в промпте
3. ✅ Добавляйте примеры желаемого вывода (few-shot)
4. ✅ Просите «отвечай ТОЛЬКО JSON, без комментариев»

---

## Часть 8: Готовый скрипт для товарных карточек

```python
#!/usr/bin/env python3
"""
Анализ фото товара через Claude Vision.
Извлечение характеристик в JSON.
"""

import json
import base64
from pathlib import Path
from anthropic import Anthropic

def analyze_product_image(image_path: Path, api_key: str) -> dict:
    """
    Анализирует фото товара и извлекает характеристики.

    Args:
        image_path: путь к фото товара
        api_key: ключ Anthropic API

    Returns:
        dict с характеристиками товара
    """
    client = Anthropic(api_key=api_key)

    # Загрузка изображения
    image_data = base64.b64encode(image_path.read_bytes()).decode()
    media_type = f"image/{image_path.suffix.lstrip('.')}"

    # Схема JSON
    schema_example = {
        "category": "тип товара",
        "brand": "бренд",
        "model": "модель",
        "power_w": "мощность Вт (число или null)",
        "power_pa": "всасывание Па (число или null)",
        "voltage": "напряжение В (число или null)",
        "capacity_ml": "объём мл (число или null)",
        "runtime_min": "время работы мин (число или null)",
        "accessories_count": "количество насадок (число или null)",
        "features": ["список применений"],
        "visible_text": "весь видимый текст на товаре"
    }

    prompt = f"""Проанализируй это фото товара.

Извлеки ВСЕ технические характеристики, которые можно прочитать или определить по изображению.

Верни результат в формате JSON по этой схеме:
{json.dumps(schema_example, indent=2, ensure_ascii=False)}

ВАЖНО:
- Если характеристика не видна — ставь null
- visible_text должен содержать весь текст, который видно на товаре/упаковке
- features — список применений или ключевых особенностей
- Отвечай ТОЛЬКО валидным JSON, без markdown блоков"""

    # Запрос к Claude
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt}
                ],
            }
        ],
    )

    # Парсинг JSON
    response_text = message.content[0].text.strip()

    # Удаляем markdown блоки если есть
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    return json.loads(response_text)


# Пример использования
if __name__ == "__main__":
    API_KEY = "sk-ant-api03-..."  # ваш ключ

    # Анализ одного фото
    result = analyze_product_image(
        image_path=Path("vacuum_cleaner.jpg"),
        api_key=API_KEY
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Сохранение результата
    output_path = Path("product_specs.json")
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nСохранено в {output_path}")
```

---

## Часть 9: Альтернативные способы использования

### Через curl (без Python)

```bash
# Кодирование изображения
IMAGE_BASE64=$(cat product.jpg | base64)

# Запрос
curl https://api.anthropic.com/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [{
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "'"$IMAGE_BASE64"'"
          }
        },
        {
          "type": "text",
          "text": "Что это за товар?"
        }
      ]
    }]
  }'
```

### Через TypeScript/JavaScript

```typescript
import Anthropic from "@anthropic-ai/sdk";
import fs from "fs";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const imageData = fs.readFileSync("product.jpg").toString("base64");

const message = await anthropic.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 1024,
  messages: [
    {
      role: "user",
      content: [
        {
          type: "image",
          source: {
            type: "base64",
            media_type: "image/jpeg",
            data: imageData,
          },
        },
        {
          type: "text",
          text: "Опиши этот товар.",
        },
      ],
    },
  ],
});

console.log(message.content[0].text);
```

---

## Итого: что достаточно для Claude Vision

✅ **Всё, что нужно:**
1. API-ключ Anthropic (бесплатные $5 для начала)
2. Библиотека `anthropic` (Python) или прямые HTTP-запросы
3. Изображения/PDF в base64 или URL

❌ **НЕ нужно:**
- Google Cloud Vision API
- Дополнительные сервисы
- Другие подписки

**Работает из коробки** для:
- Изображений (JPEG, PNG, GIF, WebP)
- PDF (до 100 страниц)
- Других документов (DOCX, CSV, TXT, HTML, XLSX и т.д.)

**Документация:**
- https://docs.anthropic.com/en/docs/build-with-claude/vision
- https://docs.anthropic.com/en/docs/build-with-claude/pdf-support
