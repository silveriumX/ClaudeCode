# Инструменты для переработки инструкций

Набор скриптов для автоматизации работы с инструкциями.

---

## Установка зависимостей

```bash
cd Scripts/InstructionTools
pip install -r requirements.txt
```

---

## Инструменты

### 1. extract_images_from_pdf.py

Извлекает изображения из PDF файла.

**Использование:**

```bash
# Извлечь в папку images/ рядом с PDF
python extract_images_from_pdf.py document.pdf

# Извлечь в указанную папку
python extract_images_from_pdf.py document.pdf ./output_images
```

**Результат:**
- Изображения сохраняются как `step1_page1.png`, `step2_page1.png` и т.д.
- Выводит готовые Markdown ссылки для вставки

---

### 2. extract_images_from_docx.py

Извлекает изображения из .docx файла (экспорт из Google Docs).

**Использование:**

```bash
# Извлечь изображения
python extract_images_from_docx.py document.docx

# Извлечь изображения + текст в Markdown
python extract_images_from_docx.py document.docx --text

# Указать папку для изображений
python extract_images_from_docx.py document.docx ./output_images
```

**Результат:**
- Изображения сохраняются как `step1_img.png`, `step2_img.png` и т.д.
- С флагом `--text` также создаётся .md файл с текстом

---

## Установка Pandoc (для конвертации в PDF)

Pandoc нужен для конвертации Markdown → PDF.

### Windows

1. Скачайте установщик: https://pandoc.org/installing.html
2. Или через Chocolatey:

```powershell
choco install pandoc
```

### Использование Pandoc

```bash
# Базовая конвертация
pandoc instruction.md -o instruction.pdf

# С поддержкой русского языка
pandoc instruction.md -o instruction.pdf --pdf-engine=xelatex -V mainfont="Arial"

# С оглавлением
pandoc instruction.md -o instruction.pdf --toc
```

---

## Альтернатива: VS Code расширение

Если не хотите устанавливать Pandoc:

1. Установите расширение "Markdown PDF" в VS Code/Cursor
2. Откройте .md файл
3. `Ctrl+Shift+P` → "Markdown PDF: Export (pdf)"

---

## Workflow переработки инструкции

```
1. Получить PDF/Google Doc
       ↓
2. Извлечь изображения (extract_images_from_pdf.py)
       ↓
3. Загрузить PDF в Cursor чат
       ↓
4. Попросить переработать по стандарту
       ↓
5. Вставить ссылки на изображения
       ↓
6. Конвертировать в PDF (опционально)
```

---

**Дата создания:** 22.01.2026
