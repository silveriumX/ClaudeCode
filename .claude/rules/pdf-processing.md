# PDF Processing Standards

> Стандарты работы с PDF в Python проектах

---

## Установленные библиотеки

```bash
pip install PyPDF2 pypdf pdfplumber pytesseract pdf2image reportlab weasyprint pillow
```

---

## Выбор библиотеки по задаче

| Задача | Библиотека | Когда использовать |
|--------|------------|-------------------|
| Чтение текста из PDF | `pdfplumber` | Текстовые PDF с хорошей структурой |
| Извлечение метаданных | `pypdf` | Информация о документе, количество страниц |
| Объединение/разделение PDF | `pypdf` | Манипуляции со страницами |
| OCR отсканированных PDF | `pytesseract` + `pdf2image` | Когда PDF = изображения |
| OCR со структурой | Vision API (`/ocr-structured-text`) | Сложные документы с таблицами |
| Генерация PDF из данных | `reportlab` | Программное создание PDF |
| HTML → PDF | `weasyprint` | Красивые PDF из HTML/CSS |

---

## 1. Чтение текста из PDF

### Простое извлечение (pdfplumber)

```python
from pathlib import Path
import pdfplumber
from typing import Optional

def extract_pdf_text(pdf_path: Path) -> Optional[str]:
    """
    Извлечь текст из PDF.

    Args:
        pdf_path: Путь к PDF файлу

    Returns:
        Текст документа или None при ошибке
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(
                page.extract_text() or ""
                for page in pdf.pages
            )
        return text
    except Exception as e:
        logger.error(f"Ошибка чтения PDF {pdf_path}: {e}")
        return None
```

### Извлечение с таблицами

```python
def extract_pdf_with_tables(pdf_path: Path) -> dict:
    """Извлечь текст и таблицы из PDF"""
    result = {"text": "", "tables": []}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Текст
            result["text"] += page.extract_text() or ""

            # Таблицы
            tables = page.extract_tables()
            result["tables"].extend(tables)

    return result
```

---

## 2. Метаданные и информация о PDF

### Получение метаданных (pypdf)

```python
from pypdf import PdfReader
from pathlib import Path

def get_pdf_info(pdf_path: Path) -> dict:
    """Получить метаданные PDF"""
    reader = PdfReader(pdf_path)

    return {
        "pages": len(reader.pages),
        "title": reader.metadata.title,
        "author": reader.metadata.author,
        "subject": reader.metadata.subject,
        "creator": reader.metadata.creator,
        "producer": reader.metadata.producer,
        "created": reader.metadata.creation_date,
        "modified": reader.metadata.modification_date,
    }
```

---

## 3. Манипуляции с PDF

### Объединение PDF (pypdf)

```python
from pypdf import PdfWriter, PdfReader
from pathlib import Path
from typing import List

def merge_pdfs(pdf_paths: List[Path], output_path: Path) -> None:
    """Объединить несколько PDF в один"""
    writer = PdfWriter()

    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, 'wb') as output_file:
        writer.write(output_file)

    logger.info(f"Объединено {len(pdf_paths)} PDF → {output_path}")
```

### Разделение PDF

```python
def split_pdf(pdf_path: Path, output_dir: Path) -> List[Path]:
    """Разделить PDF на отдельные страницы"""
    output_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(pdf_path)
    output_files = []

    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)

        output_path = output_dir / f"page_{i:03d}.pdf"
        with open(output_path, 'wb') as f:
            writer.write(f)

        output_files.append(output_path)

    return output_files
```

### Извлечение диапазона страниц

```python
def extract_pages(
    pdf_path: Path,
    output_path: Path,
    start: int,
    end: int
) -> None:
    """Извлечь страницы с start по end (включительно)"""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_num in range(start - 1, end):  # 0-indexed
        writer.add_page(reader.pages[page_num])

    with open(output_path, 'wb') as f:
        writer.write(f)
```

---

## 4. OCR для отсканированных PDF

### Подготовка (требуется Tesseract)

**Windows:**
```bash
# Скачать: https://github.com/UB-Mannheim/tesseract/wiki
# Установить Tesseract-OCR
# Добавить в PATH: C:\Program Files\Tesseract-OCR
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-rus
```

### OCR через pytesseract

```python
from pdf2image import convert_from_path
import pytesseract
from pathlib import Path
from typing import Optional
import os

def ocr_pdf(pdf_path: Path, lang: str = 'rus+eng') -> Optional[str]:
    """
    OCR отсканированного PDF.

    Args:
        pdf_path: Путь к PDF
        lang: Язык распознавания (rus, eng, rus+eng)

    Returns:
        Распознанный текст
    """
    # Windows: указать путь к tesseract если не в PATH
    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = (
            r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )

    try:
        # Конвертировать PDF → изображения
        images = convert_from_path(pdf_path)

        # OCR каждой страницы
        text_parts = []
        for i, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image, lang=lang)
            text_parts.append(f"--- Страница {i} ---\n{text}")
            logger.debug(f"OCR страница {i}/{len(images)}")

        return "\n\n".join(text_parts)

    except Exception as e:
        logger.error(f"Ошибка OCR для {pdf_path}: {e}")
        return None
```

### OCR со структурой (Vision API)

Для сложных документов с таблицами, формулами, многоколоночным текстом:

```python
# Использовать скилл /ocr-structured-text
# Он сохраняет структуру блоков, таблиц, параграфов
```

---

## 5. Генерация PDF из данных

### Простой PDF (reportlab)

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path

def create_simple_pdf(output_path: Path, title: str, lines: list) -> None:
    """Создать простой текстовый PDF"""
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Заголовок
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, title)

    # Текст
    c.setFont("Helvetica", 12)
    y = height - 100

    for line in lines:
        c.drawString(50, y, line)
        y -= 20

        # Новая страница если не помещается
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - 50

    c.save()
    logger.info(f"PDF создан: {output_path}")
```

### HTML → PDF (weasyprint)

```python
from weasyprint import HTML, CSS
from pathlib import Path

def html_to_pdf(
    html_content: str,
    output_path: Path,
    css_path: Optional[Path] = None
) -> None:
    """
    Конвертировать HTML в PDF.

    Args:
        html_content: HTML строка
        output_path: Путь для сохранения PDF
        css_path: Опциональный путь к CSS файлу
    """
    stylesheets = []
    if css_path and css_path.exists():
        stylesheets.append(CSS(filename=str(css_path)))

    HTML(string=html_content).write_pdf(
        output_path,
        stylesheets=stylesheets
    )

    logger.info(f"HTML → PDF: {output_path}")
```

---

## 6. Batch обработка

### Обработка папки с PDF

```python
from pathlib import Path
from typing import Callable, List
import logging

def process_pdf_folder(
    input_dir: Path,
    output_dir: Path,
    processor: Callable[[Path, Path], None],
    pattern: str = "*.pdf"
) -> List[Path]:
    """
    Обработать все PDF в папке.

    Args:
        input_dir: Папка с исходными PDF
        output_dir: Папка для результатов
        processor: Функция обработки (input_path, output_path) -> None
        pattern: Паттерн для поиска файлов

    Returns:
        Список обработанных файлов
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    processed = []

    for pdf_path in input_dir.glob(pattern):
        try:
            output_path = output_dir / pdf_path.name
            processor(pdf_path, output_path)
            processed.append(output_path)
            logger.info(f"✓ {pdf_path.name}")
        except Exception as e:
            logger.error(f"✗ {pdf_path.name}: {e}")

    logger.info(f"Обработано: {len(processed)}/{len(list(input_dir.glob(pattern)))}")
    return processed
```

### Пример использования

```python
from pathlib import Path

# Извлечь текст из всех PDF
def extract_processor(input_path: Path, output_path: Path) -> None:
    text = extract_pdf_text(input_path)
    if text:
        output_path = output_path.with_suffix('.txt')
        output_path.write_text(text, encoding='utf-8')

process_pdf_folder(
    Path("input_pdfs"),
    Path("extracted_text"),
    extract_processor
)
```

---

## 7. Обработка ошибок

### Типичные проблемы и решения

```python
import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError

def safe_pdf_extract(pdf_path: Path) -> Optional[str]:
    """Безопасное извлечение с fallback"""

    # Попытка 1: pdfplumber (лучшее качество)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}, trying pypdf...")

    # Попытка 2: pypdf (более стабильный)
    try:
        reader = PdfReader(pdf_path)
        return "\n".join(page.extract_text() for page in reader.pages)
    except PdfReadError as e:
        logger.error(f"PDF повреждён: {e}")
        return None
    except Exception as e:
        logger.error(f"Не удалось прочитать PDF: {e}")
        return None
```

---

## Чеклист для работы с PDF

- [ ] Используется `pathlib.Path` для путей
- [ ] Настроено логирование
- [ ] Обработка ошибок (try/except)
- [ ] Проверка существования файла перед обработкой
- [ ] Кодировка UTF-8 для сохранения текста
- [ ] Для OCR: проверка установки Tesseract
- [ ] Для больших PDF: обработка по страницам (не всё в памяти)
- [ ] Cleanup временных файлов после обработки

---

## Примеры использования

### Telegram-бот с PDF обработкой

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
import pdfplumber
from pathlib import Path
import logging

async def handle_pdf(update: Update, context) -> None:
    """Обработать PDF от пользователя"""
    document = update.message.document

    if not document.file_name.endswith('.pdf'):
        await update.message.reply_text("Отправьте PDF файл")
        return

    # Скачать PDF
    file = await document.get_file()
    pdf_path = Path(f"temp/{document.file_id}.pdf")
    pdf_path.parent.mkdir(exist_ok=True)
    await file.download_to_drive(pdf_path)

    # Извлечь текст
    await update.message.reply_text("Обрабатываю PDF...")
    text = extract_pdf_text(pdf_path)

    if text:
        # Отправить результат (максимум 4096 символов)
        if len(text) > 4000:
            text = text[:4000] + "...\n[Текст обрезан]"
        await update.message.reply_text(f"Текст из PDF:\n\n{text}")
    else:
        await update.message.reply_text("Не удалось извлечь текст")

    # Удалить временный файл
    pdf_path.unlink()
```

### Обработка счетов-фактур

```python
from pathlib import Path
import pdfplumber
import re
from typing import Optional

def extract_invoice_data(pdf_path: Path) -> Optional[dict]:
    """Извлечь данные из счёта-фактуры"""
    text = extract_pdf_text(pdf_path)
    if not text:
        return None

    # Регулярки для извлечения данных
    invoice_data = {
        "number": re.search(r'Счёт[- ]фактура\s*№\s*(\S+)', text),
        "date": re.search(r'от\s+(\d{2}\.\d{2}\.\d{4})', text),
        "amount": re.search(r'Итого:\s*(\d[\d\s]*\.?\d{2})', text),
    }

    return {
        k: v.group(1) if v else None
        for k, v in invoice_data.items()
    }
```

---

## Связанные скиллы

- `/ocr-structured-text` — OCR с сохранением структуры документа (Vision API)
- `/config-env-portability` — Для конфигурации путей к Tesseract
- `/unicode-fixer` — Если проблемы с кодировкой в извлечённом тексте
