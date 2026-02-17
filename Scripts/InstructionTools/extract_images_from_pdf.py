#!/usr/bin/env python3
"""
Скрипт для извлечения изображений из PDF файла.

Использование:
    python extract_images_from_pdf.py input.pdf [output_folder]

Требования:
    pip install pymupdf pillow
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Проверка установленных зависимостей."""
    missing = []

    try:
        import fitz  # PyMuPDF
    except ImportError:
        missing.append("pymupdf")

    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")

    if missing:
        print(f"Отсутствуют библиотеки: {', '.join(missing)}")
        print(f"Установите их командой: pip install {' '.join(missing)}")
        return False
    return True


def extract_images(pdf_path: str, output_folder: str = None) -> list:
    """
    Извлекает изображения из PDF файла.

    Args:
        pdf_path: Путь к PDF файлу
        output_folder: Папка для сохранения (по умолчанию: images/ рядом с PDF)

    Returns:
        Список путей к извлечённым изображениям
    """
    import fitz
    from PIL import Image
    import io

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"Файл не найден: {pdf_path}")
        return []

    # Определяем папку для вывода
    if output_folder is None:
        output_folder = pdf_path.parent / "images"
    else:
        output_folder = Path(output_folder)

    output_folder.mkdir(parents=True, exist_ok=True)

    extracted_files = []
    image_counter = 1

    print(f"Открываю: {pdf_path}")
    doc = fitz.open(str(pdf_path))

    for page_num, page in enumerate(doc, start=1):
        image_list = page.get_images()

        if image_list:
            print(f"Страница {page_num}: найдено {len(image_list)} изображений")

        for img_index, img in enumerate(image_list):
            xref = img[0]

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Конвертируем в PNG для единообразия
                img_pil = Image.open(io.BytesIO(image_bytes))

                # Пропускаем слишком маленькие изображения (иконки и т.д.)
                if img_pil.width < 50 or img_pil.height < 50:
                    continue

                # Формируем имя файла
                filename = f"step{image_counter}_page{page_num}.png"
                filepath = output_folder / filename

                # Сохраняем как PNG
                img_pil.save(str(filepath), "PNG")
                extracted_files.append(str(filepath))

                print(f"  Сохранено: {filename} ({img_pil.width}x{img_pil.height})")
                image_counter += 1

            except Exception as e:
                print(f"  Ошибка извлечения изображения: {e}")

    doc.close()

    print(f"\nИтого извлечено: {len(extracted_files)} изображений")
    print(f"Сохранены в: {output_folder}")

    return extracted_files


def generate_markdown_links(image_paths: list) -> str:
    """Генерирует Markdown ссылки на изображения."""
    lines = []
    for path in image_paths:
        filename = Path(path).name
        lines.append(f"![Описание](./images/{filename})")
    return "\n\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nПример:")
        print("  python extract_images_from_pdf.py document.pdf")
        print("  python extract_images_from_pdf.py document.pdf ./output_images")
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None

    extracted = extract_images(pdf_path, output_folder)

    if extracted:
        print("\n--- Markdown ссылки для вставки ---\n")
        print(generate_markdown_links(extracted))


if __name__ == "__main__":
    main()
