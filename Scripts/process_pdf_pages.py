"""
Разделение сжатого PDF и подготовка к обработке
"""
import PyPDF2
import os

input_pdf = r"C:\Users\Admin\Downloads\The_Exoskeleton_Mindset_compressed.pdf"
output_dir = r"C:\Users\Admin\Downloads\PDF_Compressed_Pages"

print("="*60)
print("РАЗДЕЛЕНИЕ СЖАТОГО PDF")
print("="*60)

os.makedirs(output_dir, exist_ok=True)

with open(input_pdf, 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)
    total_pages = len(pdf_reader.pages)

    print(f"\nВсего страниц: {total_pages}")
    print(f"Папка: {output_dir}\n")

    for i in range(total_pages):
        pdf_writer = PyPDF2.PdfWriter()
        pdf_writer.add_page(pdf_reader.pages[i])

        output_file = os.path.join(output_dir, f"page_{i+1:02d}.pdf")

        with open(output_file, 'wb') as out:
            pdf_writer.write(out)

        size_kb = os.path.getsize(output_file) / 1024
        print(f"[OK] Страница {i+1}: {size_kb:.1f} KB - {output_file}")

print(f"\n{'='*60}")
print(f"Готово! Создано страниц: {total_pages}")
print(f"{'='*60}")
