"""
Скрипт для извлечения текста из PDF и сжатия PDF файлов
"""
from pathlib import Path
import sys

def extract_text_from_pdf(pdf_path, output_path=None):
    """Извлекает текст из PDF файла"""
    pdf_path = Path(pdf_path)
    try:
        import PyPDF2

        with pdf_path.open('rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = []

            print(f"Обработка {len(pdf_reader.pages)} страниц...")

            for i, page in enumerate(pdf_reader.pages, 1):
                print(f"Страница {i}/{len(pdf_reader.pages)}")
                page_text = page.extract_text()
                text.append(f"\n--- Страница {i} ---\n{page_text}")

            full_text = "\n".join(text)

            if output_path is None:
                output_path = pdf_path.with_suffix('.txt').name
                output_path = pdf_path.parent / f"{pdf_path.stem}_extracted.txt"
            else:
                output_path = Path(output_path)

            output_path.write_text(full_text, encoding='utf-8')

            print(f"\n✓ Текст извлечен: {output_path}")
            print(f"  Размер: {len(full_text)} символов")
            return output_path

    except ImportError:
        print("❌ Библиотека PyPDF2 не установлена")
        print("Установите: pip install PyPDF2")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def compress_pdf(pdf_path, output_path=None, quality=50):
    """Сжимает PDF файл"""
    pdf_path = Path(pdf_path)
    try:
        from PIL import Image
        import PyPDF2
        from pdf2image import convert_from_path

        if output_path is None:
            output_path = pdf_path.parent / f"{pdf_path.stem}_compressed.pdf"
        else:
            output_path = Path(output_path)

        print(f"Конвертация PDF в изображения...")
        images = convert_from_path(str(pdf_path), dpi=150)

        print(f"Сжатие {len(images)} страниц...")
        compressed_images = []

        for i, img in enumerate(images, 1):
            print(f"Сжатие страницы {i}/{len(images)}")
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            compressed_images.append(img)

        # Сохраняем как PDF
        compressed_images[0].save(
            str(output_path),
            save_all=True,
            append_images=compressed_images[1:],
            quality=quality,
            optimize=True
        )

        original_size = pdf_path.stat().st_size / 1024 / 1024
        compressed_size = output_path.stat().st_size / 1024 / 1024

        print(f"\n✓ PDF сжат: {output_path}")
        print(f"  Исходный размер: {original_size:.2f} MB")
        print(f"  Сжатый размер: {compressed_size:.2f} MB")
        print(f"  Сжатие: {(1 - compressed_size/original_size)*100:.1f}%")

        return output_path

    except ImportError as e:
        print(f"❌ Не установлены необходимые библиотеки: {e}")
        print("Установите: pip install PyPDF2 pdf2image Pillow")
        print("Также нужен poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("PDF Обработчик")
    print("=" * 60)

    if len(sys.argv) < 2:
        pdf_path_str = input("\nПуть к PDF файлу: ").strip('"')
        pdf_path = Path(pdf_path_str)
    else:
        pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        print(f"❌ Файл не найден: {pdf_path}")
        sys.exit(1)

    print(f"\nФайл: {pdf_path}")
    print(f"Размер: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

    print("\nВыберите действие:")
    print("1. Извлечь текст (рекомендуется)")
    print("2. Сжать PDF")

    choice = input("\nВаш выбор (1/2): ").strip()

    if choice == "1":
        result = extract_text_from_pdf(pdf_path)
    elif choice == "2":
        result = compress_pdf(pdf_path)
    else:
        print("❌ Неверный выбор")
        sys.exit(1)

    if result:
        print(f"\n✓ Готово!")
    else:
        print(f"\n❌ Не удалось обработать файл")
