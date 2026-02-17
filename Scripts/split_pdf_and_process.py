"""
Разделение PDF на части для обработки через Claude API
"""
import PyPDF2
import os

pdf_path = r"C:\Users\Admin\Downloads\The_Exoskeleton_Mindset.pdf"
output_dir = r"C:\Users\Admin\Downloads\PDF_Parts"

print("="*60)
print("РАЗДЕЛЕНИЕ PDF НА ЧАСТИ")
print("="*60)

# Создаем папку для частей
os.makedirs(output_dir, exist_ok=True)

# Читаем PDF
with open(pdf_path, 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)
    total_pages = len(pdf_reader.pages)

    print(f"\nВсего страниц: {total_pages}")
    print(f"Папка для сохранения: {output_dir}\n")

    # Разделяем на отдельные страницы
    pages_per_part = 1
    part_num = 1

    for i in range(0, total_pages, pages_per_part):
        end_page = min(i + pages_per_part, total_pages)

        # Создаем новый PDF
        pdf_writer = PyPDF2.PdfWriter()

        for page_num in range(i, end_page):
            pdf_writer.add_page(pdf_reader.pages[page_num])

        # Сохраняем часть
        part_filename = f"part_{part_num:02d}_pages_{i+1}-{end_page}.pdf"
        part_path = os.path.join(output_dir, part_filename)

        with open(part_path, 'wb') as output_file:
            pdf_writer.write(output_file)

        file_size = os.path.getsize(part_path) / 1024 / 1024
        print(f"[OK] Создана часть {part_num}: страницы {i+1}-{end_page} ({file_size:.2f} MB)")
        print(f"     {part_path}")

        part_num += 1

print(f"\n{'='*60}")
print(f"Создано частей: {part_num - 1}")
print(f"{'='*60}")
