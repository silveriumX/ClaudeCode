"""
Извлечение текста из PDF с OCR (для PDF-изображений)
"""
import os

pdf_path = r"C:\Users\Admin\Downloads\The_Exoskeleton_Mindset.pdf"
output_path = pdf_path.replace('.pdf', '_text.txt')

print("="*60)
print("ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ PDF С OCR")
print("="*60)
print(f"\nФайл: {pdf_path}\n")

try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image

    # Для Windows может потребоваться указать путь к tesseract
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    print("Конвертация PDF в изображения...")
    images = convert_from_path(pdf_path, dpi=300)

    print(f"Найдено страниц: {len(images)}")
    print("\nРаспознавание текста...")

    all_text = []

    for i, image in enumerate(images, 1):
        print(f"Страница {i}/{len(images)}...", end='\r')

        # OCR распознавание
        text = pytesseract.image_to_string(image, lang='eng')

        if text.strip():
            all_text.append(f"\n{'='*60}\nСТРАНИЦА {i}\n{'='*60}\n\n{text}")

    if all_text:
        full_text = "\n".join(all_text)

        print(f"\n\nСохранение в файл: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)

        print(f"\nГОТОВО!")
        print(f"  Распознано символов: {len(full_text):,}")
        print(f"  Сохранено в: {output_path}")
    else:
        print("\nНе удалось распознать текст")

except ImportError as e:
    print(f"\nНе установлены библиотеки: {e}")
    print("\nУстановите:")
    print("  pip install pdf2image pytesseract Pillow")
    print("\nТакже нужно установить:")
    print("  1. Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
    print("  2. Poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
except Exception as e:
    print(f"\nОшибка: {e}")
