"""
Сжатие PDF через уменьшение разрешения изображений
"""
from pathlib import Path
import subprocess
import sys

def compress_pdf_ghostscript(input_path, output_path, dpi=150):
    """
    Сжатие PDF используя Ghostscript (если установлен)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Проверяем наличие Ghostscript
    gs_paths = [
        Path(r"C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe"),
        Path(r"C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe"),
        Path(r"C:\Program Files\gs\gs10.03.0\bin\gswin64c.exe"),
        Path(r"C:\Program Files\gs\gs10.02.1\bin\gswin64c.exe"),
        Path(r"C:\Program Files (x86)\gs\gs10.04.0\bin\gswin32c.exe"),
        "gswin64c.exe",  # Если в PATH
        "gs",  # Для Linux/Mac
    ]

    gs_exe = None
    for path in gs_paths:
        if isinstance(path, Path):
            if path.exists():
                gs_exe = str(path)
                break
        elif path in ["gswin64c.exe", "gs"]:
            gs_exe = path
            break

    if not gs_exe:
        print("Ghostscript не найден!")
        print("\nУстановите Ghostscript:")
        print("https://ghostscript.com/releases/gsdnld.html")
        return False

    # Команда сжатия
    cmd = [
        gs_exe,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/ebook",  # или /screen для максимального сжатия
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-r{dpi}",
        f"-sOutputFile={output_path}",
        str(input_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"Ошибка Ghostscript: {result.stderr}")
            return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False


def compress_pdf_pillow(input_path, output_path):
    """
    Сжатие PDF через Pillow (требует poppler)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    try:
        from pdf2image import convert_from_path
        from PIL import Image

        print("Конвертация страниц...")
        # Низкое DPI для сжатия
        images = convert_from_path(str(input_path), dpi=150)

        print(f"Сжатие {len(images)} страниц...")
        compressed = []

        for i, img in enumerate(images, 1):
            print(f"  Страница {i}/{len(images)}", end='\r')
            # Конвертируем в RGB и сжимаем
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # Уменьшаем размер если нужно
            img.thumbnail((1200, 1600), Image.Resampling.LANCZOS)
            compressed.append(img)

        print("\nСохранение...")
        compressed[0].save(
            str(output_path),
            save_all=True,
            append_images=compressed[1:],
            quality=50,
            optimize=True,
            format='PDF'
        )

        return True

    except ImportError as e:
        print(f"Не установлены библиотеки: {e}")
        print("\nУстановите: pip install pdf2image Pillow")
        print("И poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
        return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False


if __name__ == "__main__":
    input_pdf = Path(r"C:\Users\Admin\Downloads\The_Exoskeleton_Mindset.pdf")
    output_pdf = Path(r"C:\Users\Admin\Downloads\The_Exoskeleton_Mindset_compressed.pdf")

    print("="*60)
    print("СЖАТИЕ PDF")
    print("="*60)
    print(f"\nИсходный файл: {input_pdf}")

    if not input_pdf.exists():
        print(f"Файл не найден!")
        sys.exit(1)

    original_size = input_pdf.stat().st_size / 1024 / 1024
    print(f"Исходный размер: {original_size:.2f} MB")

    print("\nПопытка 1: Ghostscript...")
    if compress_pdf_ghostscript(input_pdf, output_pdf):
        compressed_size = output_pdf.stat().st_size / 1024 / 1024
        compression_ratio = (1 - compressed_size/original_size) * 100

        print(f"\nГОТОВО!")
        print(f"  Сжатый размер: {compressed_size:.2f} MB")
        print(f"  Сжатие: {compression_ratio:.1f}%")
        print(f"  Файл: {output_pdf}")
    else:
        print("\nПопытка 2: Pillow...")
        if compress_pdf_pillow(input_pdf, output_pdf):
            compressed_size = output_pdf.stat().st_size / 1024 / 1024
            compression_ratio = (1 - compressed_size/original_size) * 100

            print(f"\nГОТОВО!")
            print(f"  Сжатый размер: {compressed_size:.2f} MB")
            print(f"  Сжатие: {compression_ratio:.1f}%")
            print(f"  Файл: {output_pdf}")
        else:
            print("\nНе удалось сжать PDF")
            print("\nРекомендации:")
            print("1. Используйте онлайн-сервис: https://www.ilovepdf.com/compress_pdf")
            print("2. Или: https://www.pdf24.org/ru/compress-pdf")
