"""
PDF Processor - извлечение текста из PDF файлов
Поддерживает как текстовые PDF, так и сканы (через OCR)
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Tuple
import base64
from io import BytesIO

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Извлекает текст из текстового PDF"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []

    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        if text.strip():
            text_parts.append(f"--- Страница {page_num} ---\n{text}")

    doc.close()
    return "\n\n".join(text_parts)


def is_scanned_pdf(pdf_bytes: bytes) -> bool:
    """Определяет, является ли PDF сканом (без текстового слоя)"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    total_text = ""
    for page in doc:
        total_text += page.get_text()

    doc.close()

    # Если текста очень мало относительно количества страниц - это скан
    avg_chars_per_page = len(total_text) / max(len(doc), 1)
    return avg_chars_per_page < 100  # Меньше 100 символов на страницу = скан


def ocr_pdf(pdf_bytes: bytes) -> str:
    """Распознает текст из отсканированного PDF через OCR"""
    if not OCR_AVAILABLE:
        return "[OCR недоступен. Установите pytesseract и Tesseract-OCR]"

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []

    for page_num, page in enumerate(doc, 1):
        # Конвертируем страницу в изображение
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom для лучшего OCR
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # OCR
        try:
            text = pytesseract.image_to_string(img, lang='rus+eng')
            if text.strip():
                text_parts.append(f"--- Страница {page_num} (OCR) ---\n{text}")
        except Exception as e:
            text_parts.append(f"--- Страница {page_num} ---\n[Ошибка OCR: {e}]")

    doc.close()
    return "\n\n".join(text_parts)


def pdf_to_images_base64(pdf_bytes: bytes, max_pages: int = 20) -> list:
    """
    Конвертирует страницы PDF в base64 изображения для Claude Vision
    Возвращает список base64 строк
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    for page_num, page in enumerate(doc):
        if page_num >= max_pages:
            break

        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        images.append({
            "page": page_num + 1,
            "base64": img_base64,
            "media_type": "image/png"
        })

    doc.close()
    return images


def process_pdf(file_bytes: bytes, filename: str, use_vision: bool = False) -> dict:
    """
    Основная функция обработки PDF

    Args:
        file_bytes: байты PDF файла
        filename: имя файла
        use_vision: использовать Claude Vision вместо текстового извлечения

    Returns:
        dict с результатами обработки
    """
    result = {
        "filename": filename,
        "type": "pdf",
        "text": None,
        "images": None,
        "is_scan": False,
        "pages": 0,
        "method": "text"
    }

    # Получаем количество страниц
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    result["pages"] = len(doc)
    doc.close()

    if use_vision:
        # Используем Vision API - конвертируем в изображения
        result["images"] = pdf_to_images_base64(file_bytes)
        result["method"] = "vision"
        result["text"] = f"[PDF отправлен как {len(result['images'])} изображений для анализа]"
    else:
        # Проверяем, скан это или текстовый PDF
        result["is_scan"] = is_scanned_pdf(file_bytes)

        if result["is_scan"]:
            result["text"] = ocr_pdf(file_bytes)
            result["method"] = "ocr"
        else:
            result["text"] = extract_text_from_pdf(file_bytes)
            result["method"] = "text"

    return result
