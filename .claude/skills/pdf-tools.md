# PDF Tools

> Быстрые операции с PDF файлами

---

## Когда использовать

- Извлечь текст из PDF
- Объединить/разделить PDF
- Получить метаданные PDF
- OCR отсканированных документов
- Создать PDF из данных
- Batch обработка папки с PDF

---

## Примеры вызова

```
"Извлеки текст из document.pdf"
"Объедини все PDF из папки invoices"
"Раздели large.pdf на отдельные страницы"
"Сделай OCR для scanned.pdf"
"Создай PDF отчёт из этих данных"
"/pdf-tools"
```

---

## Доступные операции

### 1. Извлечение текста

**Входные данные:**
- Путь к PDF файлу или папке с PDF
- (опционально) Выходная папка для текстовых файлов

**Что делает:**
- Извлекает текст из PDF через pdfplumber
- Сохраняет в .txt файлы с кодировкой UTF-8
- Для папки - обрабатывает все PDF

**Пример:**
```python
# Один файл
extract_pdf_text(Path("document.pdf"))

# Папка
process_pdf_folder(
    Path("input_pdfs"),
    Path("extracted_text"),
    extract_processor
)
```

---

### 2. Объединение PDF

**Входные данные:**
- Список путей к PDF файлам (или паттерн, например "reports/*.pdf")
- Путь для сохранения объединённого PDF

**Что делает:**
- Объединяет все PDF в один
- Сохраняет порядок файлов

**Пример:**
```python
merge_pdfs(
    [Path("part1.pdf"), Path("part2.pdf")],
    Path("combined.pdf")
)
```

---

### 3. Разделение PDF

**Входные данные:**
- Путь к PDF файлу
- Выходная папка для страниц

**Что делает:**
- Разделяет PDF на отдельные страницы
- Именует файлы: page_001.pdf, page_002.pdf, ...

**Пример:**
```python
split_pdf(Path("document.pdf"), Path("pages/"))
```

---

### 4. Извлечение диапазона страниц

**Входные данные:**
- Путь к PDF
- Номер начальной страницы
- Номер конечной страницы
- Путь для сохранения

**Что делает:**
- Извлекает указанные страницы в новый PDF

**Пример:**
```python
extract_pages(
    Path("book.pdf"),
    Path("chapter.pdf"),
    start=10,
    end=25
)
```

---

### 5. Метаданные PDF

**Входные данные:**
- Путь к PDF файлу

**Что делает:**
- Извлекает метаданные (автор, название, дата создания, количество страниц)
- Выводит в удобном формате

**Пример:**
```python
info = get_pdf_info(Path("document.pdf"))
print(f"Страниц: {info['pages']}")
print(f"Автор: {info['author']}")
```

---

### 6. OCR отсканированных PDF

**Входные данные:**
- Путь к отсканированному PDF
- (опционально) Язык распознавания (rus, eng, rus+eng)

**Что делает:**
- Конвертирует PDF в изображения
- Распознаёт текст через Tesseract OCR
- Сохраняет результат в текстовый файл

**Требования:**
- Установлен Tesseract OCR
- Windows: https://github.com/UB-Mannheim/tesseract/wiki

**Пример:**
```python
text = ocr_pdf(Path("scanned.pdf"), lang='rus+eng')
```

---

### 7. Создание PDF из текста

**Входные данные:**
- Заголовок
- Список строк текста
- Путь для сохранения

**Что делает:**
- Создаёт PDF с текстом
- Автоматическое разбиение на страницы

**Пример:**
```python
create_simple_pdf(
    Path("report.pdf"),
    "Отчёт за январь",
    ["Доход: 100000", "Расход: 50000", "Прибыль: 50000"]
)
```

---

### 8. HTML → PDF

**Входные данные:**
- HTML контент (строка)
- Путь для сохранения
- (опционально) Путь к CSS файлу

**Что делает:**
- Конвертирует HTML в PDF с сохранением стилей
- Использует weasyprint

**Пример:**
```python
html = """
<html>
<body>
<h1>Отчёт</h1>
<p>Содержание отчёта...</p>
</body>
</html>
"""
html_to_pdf(html, Path("report.pdf"))
```

---

## Batch обработка

Для обработки нескольких PDF одновременно используется функция `process_pdf_folder`:

```python
def my_processor(input_path: Path, output_path: Path):
    # Твоя логика обработки
    text = extract_pdf_text(input_path)
    output_path.with_suffix('.txt').write_text(text, encoding='utf-8')

process_pdf_folder(
    Path("input/"),
    Path("output/"),
    my_processor,
    pattern="*.pdf"
)
```

---

## Интеграция с другими инструментами

### Telegram бот

```python
# Пользователь отправляет PDF → извлекаем текст → отправляем обратно
async def handle_pdf(update: Update, context):
    # Скачать PDF
    file = await update.message.document.get_file()
    pdf_path = Path(f"temp/{file.file_id}.pdf")
    await file.download_to_drive(pdf_path)

    # Обработать
    text = extract_pdf_text(pdf_path)

    # Отправить результат
    await update.message.reply_text(text[:4000])

    # Cleanup
    pdf_path.unlink()
```

### Google Drive

```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Скачать PDF из Drive
request = drive_service.files().get_media(fileId=file_id)
with open('temp.pdf', 'wb') as f:
    downloader = MediaIoBaseDownload(f, request)
    downloader.next_chunk()

# Обработать
text = extract_pdf_text(Path('temp.pdf'))

# Загрузить результат обратно
media = MediaFileUpload('result.txt', mimetype='text/plain')
drive_service.files().create(body={'name': 'result.txt'}, media_body=media)
```

---

## Обработка ошибок

Все функции должны:
- Логировать ошибки через `logger.error()`
- Возвращать `None` при ошибке (не бросать исключения)
- Проверять существование файлов перед обработкой
- Использовать `try/except` для внешних библиотек

**Пример безопасной обработки:**

```python
def safe_extract(pdf_path: Path) -> Optional[str]:
    """Извлечь текст с fallback на разные библиотеки"""
    if not pdf_path.exists():
        logger.error(f"Файл не найден: {pdf_path}")
        return None

    # Попытка 1: pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Попытка 2: pypdf
    try:
        reader = PdfReader(pdf_path)
        return "\n".join(page.extract_text() for page in reader.pages)
    except Exception as e:
        logger.error(f"pypdf failed: {e}")
        return None
```

---

## Чеклист выполнения

При работе с PDF AI должен:

- [ ] Проверить существование входных файлов
- [ ] Настроить логирование
- [ ] Использовать `pathlib.Path` для путей
- [ ] Создать выходные папки если не существуют
- [ ] Обработать ошибки (try/except)
- [ ] Использовать правильную библиотеку для задачи:
  - Текст → `pdfplumber`
  - Метаданные → `pypdf`
  - Манипуляции → `pypdf`
  - OCR → `pytesseract` + `pdf2image`
  - Генерация → `reportlab` или `weasyprint`
- [ ] Сохранять текст в UTF-8
- [ ] Удалять временные файлы
- [ ] Логировать прогресс и результаты

---

## Связанные компоненты

- **Rule:** `.claude/rules/pdf-processing.md` — детальные стандарты
- **Skill:** `/ocr-structured-text` — сложный OCR через Vision API
- **Rule:** `.claude/rules/python-standards.md` — общие стандарты Python
