"""
Слияние AI-обработанных и текстовых зон.
Плавное слияние через feathered mask для мягких краёв.
"""

from PIL import Image, ImageFilter


def merge_zones(
    ai_enhanced: Image.Image,
    text_safe: Image.Image,
    text_mask: Image.Image,
    feather_radius: int = 5,
) -> Image.Image:
    """
    Сливает AI-обработанную и безопасную для текста версии.

    Args:
        ai_enhanced: версия с полным AI-улучшением
        text_safe: версия с мягкой обработкой (текст не тронут)
        text_mask: маска текстовых зон (L, белый = текст)
        feather_radius: радиус размытия маски для плавного перехода

    Returns:
        Объединённое изображение
    """
    # Убеждаемся что все одного размера
    target_size = ai_enhanced.size

    if text_safe.size != target_size:
        text_safe = text_safe.resize(target_size, Image.LANCZOS)

    if text_mask.size != target_size:
        text_mask = text_mask.resize(target_size, Image.LANCZOS)

    # Feather маску для мягких краёв перехода
    feathered_mask = text_mask.filter(
        ImageFilter.GaussianBlur(radius=feather_radius)
    )

    # Composite: где маска белая → text_safe, где чёрная → ai_enhanced
    result = Image.composite(text_safe, ai_enhanced, feathered_mask)

    print(f"  OK: Zones merged (feather: {feather_radius}px)")

    return result
