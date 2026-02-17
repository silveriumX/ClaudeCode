#!/usr/bin/env python3
"""
Подготовка документа для работы в Cursor.

Конвертирует PDF, DOCX, Google Docs в текст + извлекает картинки.

Использование:
    python prepare_document.py document.pdf
    python prepare_document.py document.docx
    python prepare_document.py "C:\путь\к\файлу.pdf"

Результат:
    ./output/
    ├── content.txt      # Текст для вставки в Cursor
    ├── content.md       # Markdown версия (если возможно)
    └── images/          # Извлечённые картинки
        ├── img_001.png
        └── ...
"""

import sys
import os
from pathlib import Path
import shutil


def check_dependencies():
    """Проверка зависимостей."""
    missing = []

    try:
        import fitz  # PyMuPDF
    except ImportError:
        missing.append("pymupdf")

    try:
        from docx import Document
    except ImportError:
        missing.append("python-docx")

    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")

    if missing:
        print(f"Установите библиотеки: pip install {' '.join(missing)}")
        return False
    return True


def process_pdf(pdf_path: Path, output_dir: Path):
    """Обработка PDF файла."""
    import fitz
    from PIL import Image
    import io

    print(f"Обрабатываю PDF: {pdf_path.name}")

    doc = fitz.open(str(pdf_path))

    # Извлекаем текст
    text_parts = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            text_parts.append(f"--- Страница {page_num} ---\n{text}")

    full_text = "\n\n".join(text_parts)

    # Сохраняем текст
    text_file = output_dir / "content.txt"
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f"  Текст сохранён: {text_file}")

    # Извлекаем картинки
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    image_count = 0
    for page_num, page in enumerate(doc, start=1):
        for img_index, img in enumerate(page.get_images()):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                img_pil = Image.open(io.BytesIO(image_bytes))

                # Пропускаем маленькие картинки
                if img_pil.width < 50 or img_pil.height < 50:
                    continue

                image_count += 1
                filename = f"img_{image_count:03d}_page{page_num}.png"
                filepath = images_dir / filename

                img_pil.save(str(filepath), "PNG")
                print(f"  Картинка: {filename} ({img_pil.width}x{img_pil.height})")

            except Exception as e:
                pass

    doc.close()

    print(f"\nИзвлечено: {len(text_parts)} страниц текста, {image_count} картинок")
    return full_text, image_count


def process_docx(docx_path: Path, output_dir: Path):
    """Обработка DOCX файла."""
    from docx import Document
    from PIL import Image
    import io

    print(f"Обрабатываю DOCX: {docx_path.name}")

    doc = Document(str(docx_path))

    # Извлекаем текст с учётом структуры
    text_parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            # Определяем заголовки
            if para.style.name.startswith('Heading'):
                level = para.style.name.replace('Heading ', '')
                try:
                    level = int(level)
                    text_parts.append('#' * level + ' ' + text)
                except:
                    text_parts.append(text)
            else:
                text_parts.append(text)

    full_text = "\n\n".join(text_parts)

    # Сохраняем как txt
    text_file = output_dir / "content.txt"
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(full_text)

    # Сохраняем как md
    md_file = output_dir / "content.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(full_text)

    print(f"  Текст сохранён: {text_file}")
    print(f"  Markdown сохранён: {md_file}")

    # Извлекаем картинки
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    image_count = 0
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            try:
                image_data = rel.target_part.blob
                img_pil = Image.open(io.BytesIO(image_data))

                if img_pil.width < 50 or img_pil.height < 50:
                    continue

                image_count += 1
                filename = f"img_{image_count:03d}.png"
                filepath = images_dir / filename

                if img_pil.mode in ('RGBA', 'P'):
                    img_pil = img_pil.convert('RGB')
                img_pil.save(str(filepath), "PNG")

                print(f"  Картинка: {filename} ({img_pil.width}x{img_pil.height})")

            except Exception as e:
                pass

    print(f"\nИзвлечено: {len(text_parts)} параграфов, {image_count} картинок")
    return full_text, image_count


def create_cursor_prompt(output_dir: Path, image_count: int):
    """Создаёт готовый промпт для Cursor."""

    images_dir = output_dir / "images"
    image_files = sorted(images_dir.glob("*.png")) if images_dir.exists() else []

    prompt = """# Готово для Cursor!

## Шаг 1: Скопируйте текст

Откройте файл `content.txt` и скопируйте весь текст.

## Шаг 2: В Cursor Chat напишите

```
Переработай эту инструкцию по стандарту.

Текст инструкции:
[ВСТАВЬТЕ ТЕКСТ ИЗ content.txt]

"""

    if image_files:
        prompt += f"""Картинки ({len(image_files)} шт.) в папке images/:
"""
        for img in image_files:
            prompt += f"- {img.name}\n"

        prompt += """
Прикрепите картинки в чат (перетащите) и попросите:
"Расставь эти картинки по шагам инструкции"
```

## Шаг 3: Прикрепите картинки

Перетащите картинки из папки `images/` в окно чата Cursor.
"""
    else:
        prompt += """```

(Картинок не найдено)
"""

    prompt += """
---

## Полный путь к файлам:

"""
    prompt += f"- Текст: {output_dir / 'content.txt'}\n"
    if (output_dir / 'content.md').exists():
        prompt += f"- Markdown: {output_dir / 'content.md'}\n"
    prompt += f"- Картинки: {output_dir / 'images'}\n"

    # Сохраняем промпт
    prompt_file = output_dir / "README_CURSOR.md"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)

    return prompt_file


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nПримеры:")
        print("  python prepare_document.py instruction.pdf")
        print("  python prepare_document.py instruction.docx")
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"Файл не найден: {input_path}")
        sys.exit(1)

    # Создаём папку для результатов
    output_dir = input_path.parent / f"{input_path.stem}_prepared"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    print(f"\n{'='*50}")
    print(f"Подготовка документа для Cursor")
    print(f"{'='*50}\n")

    # Обрабатываем в зависимости от типа
    ext = input_path.suffix.lower()

    if ext == '.pdf':
        text, img_count = process_pdf(input_path, output_dir)
    elif ext in ['.docx', '.doc']:
        text, img_count = process_docx(input_path, output_dir)
    else:
        print(f"Неподдерживаемый формат: {ext}")
        print("Поддерживаются: .pdf, .docx")
        sys.exit(1)

    # Создаём инструкцию
    readme = create_cursor_prompt(output_dir, img_count)

    print(f"\n{'='*50}")
    print(f"ГОТОВО!")
    print(f"{'='*50}")
    print(f"\nРезультаты в папке: {output_dir}")
    print(f"\nОткройте {readme.name} для инструкций")
    print(f"\nИли просто:")
    print(f"  1. Скопируйте текст из content.txt")
    print(f"  2. Вставьте в Cursor Chat")
    print(f"  3. Перетащите картинки из images/")


if __name__ == "__main__":
    main()
