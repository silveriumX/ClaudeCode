"""
Автоматическое извлечение текста из PDF
"""
import sys

# Пробуем разные библиотеки
def extract_with_pypdf2(pdf_path):
    """Извлекает текст используя PyPDF2"""
    try:
        import PyPDF2

        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = []

            print(f"Найдено страниц: {len(pdf_reader.pages)}")

            for i, page in enumerate(pdf_reader.pages, 1):
                print(f"Обработка страницы {i}/{len(pdf_reader.pages)}...", end='\r')
                page_text = page.extract_text()
                if page_text.strip():
                    text.append(f"\n{'='*60}\nСТРАНИЦА {i}\n{'='*60}\n\n{page_text}")

            return "\n".join(text)

    except ImportError:
        print("PyPDF2 не установлен. Установите: pip install PyPDF2")
        return None
    except Exception as e:
        print(f"Ошибка PyPDF2: {e}")
        return None


def extract_with_pdfplumber(pdf_path):
    """Извлекает текст используя pdfplumber (лучше качество)"""
    try:
        import pdfplumber

        text = []
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Найдено страниц: {len(pdf.pages)}")

            for i, page in enumerate(pdf.pages, 1):
                print(f"Обработка страницы {i}/{len(pdf.pages)}...", end='\r')
                page_text = page.extract_text()
                if page_text:
                    text.append(f"\n{'='*60}\nСТРАНИЦА {i}\n{'='*60}\n\n{page_text}")

        return "\n".join(text)

    except ImportError:
        print("pdfplumber не установлен. Установите: pip install pdfplumber")
        return None
    except Exception as e:
        print(f"Ошибка pdfplumber: {e}")
        return None


if __name__ == "__main__":
    pdf_path = r"C:\Users\Admin\Downloads\The_Exoskeleton_Mindset.pdf"
    output_path = pdf_path.replace('.pdf', '_text.txt')

    print("="*60)
    print("ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ PDF")
    print("="*60)
    print(f"\nФайл: {pdf_path}\n")

    # Пробуем pdfplumber (лучше), затем PyPDF2
    text = extract_with_pdfplumber(pdf_path)
    if text is None:
        print("\nПробуем PyPDF2...")
        text = extract_with_pypdf2(pdf_path)

    if text:
        print(f"\n\nСохранение в файл: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)

        print(f"\nГОТОВО!")
        print(f"  Извлечено символов: {len(text):,}")
        print(f"  Сохранено в: {output_path}")
    else:
        print("\nНе удалось извлечь текст")
        print("\nУстановите библиотеки:")
        print("  pip install PyPDF2")
        print("  или")
        print("  pip install pdfplumber")
