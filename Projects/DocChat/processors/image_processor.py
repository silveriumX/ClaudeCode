"""
Image Processor - обработка изображений
Поддерживает отправку в Claude Vision и OCR
"""

import base64
from io import BytesIO
from typing import Dict, Optional

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def get_image_media_type(filename: str) -> str:
    """Определяет MIME тип изображения по расширению"""
    ext = filename.lower().split('.')[-1]
    media_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'bmp': 'image/bmp'
    }
    return media_types.get(ext, 'image/png')


def image_to_base64(image_bytes: bytes, filename: str) -> dict:
    """
    Конвертирует изображение в base64 для Claude Vision
    """
    base64_data = base64.b64encode(image_bytes).decode('utf-8')
    media_type = get_image_media_type(filename)

    return {
        "base64": base64_data,
        "media_type": media_type
    }


def ocr_image(image_bytes: bytes, lang: str = 'rus+eng') -> str:
    """
    Распознает текст на изображении через OCR
    """
    if not OCR_AVAILABLE:
        return "[OCR недоступен. Установите pytesseract и Tesseract-OCR]"

    try:
        img = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip() if text.strip() else "[Текст не обнаружен]"
    except Exception as e:
        return f"[Ошибка OCR: {e}]"


def get_image_info(image_bytes: bytes) -> dict:
    """Получает информацию об изображении"""
    try:
        img = Image.open(BytesIO(image_bytes))
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode
        }
    except:
        return {}


def process_image(file_bytes: bytes, filename: str, use_ocr: bool = False) -> dict:
    """
    Основная функция обработки изображения

    Args:
        file_bytes: байты изображения
        filename: имя файла
        use_ocr: использовать OCR вместо Vision

    Returns:
        dict с результатами обработки
    """
    result = {
        "filename": filename,
        "type": "image",
        "text": None,
        "image_data": None,
        "info": get_image_info(file_bytes),
        "method": "vision"
    }

    if use_ocr:
        # Используем OCR
        result["text"] = ocr_image(file_bytes)
        result["method"] = "ocr"
    else:
        # Готовим для Claude Vision
        result["image_data"] = image_to_base64(file_bytes, filename)
        result["text"] = f"[Изображение {result['info'].get('width', '?')}x{result['info'].get('height', '?')} отправлено для анализа]"

    return result
