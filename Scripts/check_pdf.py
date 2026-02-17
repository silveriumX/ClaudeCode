"""
Диагностика PDF файла
"""
import PyPDF2

pdf_path = r"C:\Users\Admin\Downloads\The_Exoskeleton_Mindset.pdf"

print("="*60)
print("ДИАГНОСТИКА PDF")
print("="*60)
print(f"\nФайл: {pdf_path}\n")

with open(pdf_path, 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)

    print(f"Всего страниц: {len(pdf_reader.pages)}")

    # Проверяем первые 3 страницы
    for i in range(min(3, len(pdf_reader.pages))):
        page = pdf_reader.pages[i]
        text = page.extract_text()

        print(f"\n--- Страница {i+1} ---")
        print(f"Длина текста: {len(text)} символов")

        if text.strip():
            # Показываем первые 200 символов
            preview = text[:200].replace('\n', ' ')
            print(f"Превью: {preview}...")
        else:
            print("ТЕКСТ НЕ НАЙДЕН (возможно, это изображение)")

            # Проверяем, есть ли изображения
            if '/XObject' in page['/Resources']:
                xObject = page['/Resources']['/XObject'].get_object()
                images_count = sum(1 for obj in xObject if xObject[obj]['/Subtype'] == '/Image')
                print(f"Найдено изображений: {images_count}")

print("\n" + "="*60)
