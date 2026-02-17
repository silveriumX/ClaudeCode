# Agentic Vision в Gemini 3 Flash: руководство для медицинской системы

> Сводка по результатам поиска (Exa, официальная документация Google). Применение к системе сохранения и разбора анализов MedicalDocBot.

---

## 1. Что такое Agentic Vision

**Agentic Vision** — новая возможность **Gemini 3 Flash** (январь 2026), которая превращает анализ изображений из «одного взгляда» в **агентный цикл**: Think → Act → Observe.

### Цикл работы

1. **Think** — модель строит план по запросу и изображению.
2. **Act** — генерирует и выполняет **Python-код**: обрезка, масштабирование, аннотации, подсчёты, визуализация.
3. **Observe** — результат (новое изображение или данные) возвращается в контекст, модель проверяет и даёт итоговый ответ.

Итог: ответы опираются на **визуальные доказательства** (zoom в детали, разметка, расчёты по картинке), а не на «угадывание». На бенчмарках по vision даёт стабильный прирост качества **5–10%** при включённом code execution.

**Источники:**
[Introducing Agentic Vision in Gemini 3 Flash (Google Blog)](https://blog.google/innovation-and-ai/technology/developers-tools/agentic-vision-gemini-3-flash/), [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3), [Code execution (images)](https://ai.google.dev/gemini-api/docs/code-execution).

---

## 2. Зачем это медицинской системе анализов

Для системы сохранения и разбора анализов (как MedicalDocBot) Agentic Vision даёт:

| Задача | Как помогает Agentic Vision |
|--------|----------------------------|
| **Мелкий текст на фото анализов** | Модель сама «зумирует» и перечитывает участки (серийные номера, значения в таблицах). |
| **Таблицы и цифры** | Вместо «угадывания» сумм/норм — выполнение Python (pandas/numpy), подсчёт, сравнение с референсами. |
| **Разметка и аннотации** | Рисование bounding box, подписей, стрелок на изображении (например, «зона отклонения от нормы»). |
| **Визуальная математика** | Графики по данным с фото (matplotlib в code execution), нормализация, сравнение с предыдущими анализами. |
| **Сложные бланки/сканеры** | Пошаговый план: обрезка областей → OCR/анализ каждой → сбор структурированного результата. |

Связь с медицинским контекстом: семейство **Med-Gemini** (на базе Gemini) уже используется для рентгенов, гистологии, офтальмологии, дерматологии, генерации отчётов и VQA по медицинским изображениям ([arXiv:2405.03162](https://arxiv.org/abs/2405.03162)). Agentic Vision в Gemini 3 Flash усиливает именно **точность и обоснованность** ответов по изображениям за счёт code execution.

---

## 3. Как включить и использовать в API

### 3.1 Модель и инструменты

- **Модель:** `gemini-3-flash-preview`.
- **Включить:** инструмент **Code Execution** (и при необходимости Thinking).

В документации это называется **Visual Thinking**: модель может писать и выполнять Python для манипуляций с изображениями.

### 3.2 Пример (Python): анализ изображения с Code Execution

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_GEMINI_API_KEY")

# Изображение: файл или bytes (например, загруженный документ/фото анализа)
with open("path/to/medical_scan.jpg", "rb") as f:
    image_bytes = f.read()

image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=[
        image_part,
        "По этому изображению анализа крови: 1) извлеки все числовые показатели и единицы измерения. "
        "2) Если нужно, увеличь участки с мелким текстом и перечитай. "
        "3) Верни структурированный список: показатель, значение, единица, норма (если видна)."
    ],
    config=types.GenerateContentConfig(
        tools=[types.Tool(code_execution=types.ToolCodeExecution())],
    ),
)

# Разбор ответа: текст, код, результат выполнения, возможные изображения
for part in response.candidates[0].content.parts:
    if part.text:
        print("Text:", part.text)
    if part.executable_code:
        print("Code:", part.executable_code.code)
    if part.code_execution_result:
        print("Execution:", part.code_execution_result.output)
    if getattr(part, "as_image", None) and part.as_image() is not None:
        # Аннотированное/обрезанное изображение от модели
        img = part.as_image()
        # сохранить или отправить пользователю
        pass
```

### 3.3 Явные подсказки для медицинских сценариев

- Zoom читается моделью **неявно** (мелкие детали).
- Для остального лучше явно просить в промпте:
  - «Напиши код, чтобы обрезать область с таблицей и извлечь числа».
  - «Нарисуй рамки вокруг каждого показателя и подпиши значение».
  - «Построй график по данным из таблицы на изображении».

### 3.4 Разрешение для медицинских изображений

Для максимального качества по изображениям в Gemini 3 можно задать **media_resolution** (в v1alpha): например `media_resolution_high` (до 1120 токенов на изображение). Для PDF-документов часто достаточно `media_resolution_medium`. Подробнее: [Gemini 3 Developer Guide — Media resolution](https://ai.google.dev/gemini-api/docs/gemini-3).

### 3.5 Structured Output + Code Execution

Gemini 3 позволяет комбинировать **Structured Output** (JSON-схема) с инструментами, включая Code Execution. Для медицинской системы удобно задать схему ответа (показатель, значение, единица, флаг «норма/не норма») и получать стабильный JSON после агентного разбора изображения.

---

## 4. Интеграция с MedicalDocBot

Текущий MedicalDocBot: загрузка документов в Drive, запись метаданных в Google Таблицу, Telegram.

Возможные шаги по использованию Agentic Vision:

1. **После загрузки файла пользователем**
   - Если тип — изображение (фото анализа, скан бланка): отправить изображение в Gemini 3 Flash с включённым Code Execution.
   - Промпт завить от типа документа: «анализ крови», «биохимия», «общий анализ мочи», «рентген» и т.д.

2. **Сохранение результата разбора**
   - Лист «Документы» уже есть; можно добавить лист «Разбор» или колонки: «Извлечённые показатели (JSON)», «Краткое заключение», «Дата разбора».
   - Или сохранять структурированный разбор в отдельном листе/документе в Drive.

3. **Безопасность и согласие**
   - Медицинские данные: явное согласие пользователя на «разбор документов ИИ», хранение только в вашем Drive/проекте, соблюдение политик Google Cloud/Vertex (при использовании Vertex AI).

4. **Диспетчеризация модели**
   - Для «только сохранить» — текущий поток без Gemini.
   - Для «сохранить и разобрать» — вызов Gemini 3 Flash с Code Execution + запись результата в таблицу/Drive.

---

## 5. Полезные ссылки

| Ресурс | Назначение |
|--------|------------|
| [Agentic Vision (Google Blog)](https://blog.google/innovation-and-ai/technology/developers-tools/agentic-vision-gemini-3-flash/) | Обзор и примеры (zoom, аннотации, визуальная математика). |
| [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3) | Модели, thinking_level, media_resolution, Thought Signatures. |
| [Code execution (в т.ч. images)](https://ai.google.dev/gemini-api/docs/code-execution) | Включение Code Execution, Visual Thinking, примеры с изображениями. |
| [Vision API (images)](https://ai.google.dev/gemini-api/docs/vision) | Передача изображений (inline, File API), форматы, лимиты. |
| [Vertex AI — Gemini 3 Flash](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash) | Использование в Google Cloud (контракты, BAA при необходимости). |
| [Med-Gemini (arXiv)](https://arxiv.org/abs/2405.03162) | Медицинские возможности семейства Gemini (рентген, гистология, отчёты). |

---

## 6. Краткий чеклист для внедрения

- [ ] Ключ API Gemini (Google AI Studio) или проект Vertex AI.
- [ ] Выбор модели: `gemini-3-flash-preview` с инструментом `code_execution`.
- [ ] Промпты под типы документов (анализы, скан бланка, рентген и т.д.).
- [ ] Схема хранения результата разбора (таблица/лист/JSON в Drive).
- [ ] Обработка частей ответа: `text`, `executable_code`, `code_execution_result`, вывод как изображение (аннотации).
- [ ] Для продакшена: учёт лимитов, стоимости токенов, политики и согласия на обработку медицинских данных.

Этот файл можно использовать как единую точку входа для проектирования и реализации разбора анализов и документов через Agentic Vision в Gemini 3 Flash.
