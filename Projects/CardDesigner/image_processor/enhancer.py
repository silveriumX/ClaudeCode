"""
Улучшение качества изображения с маскированием текстовых зон.
Зоны БЕЗ текста — полная обработка (шарпенинг, цвет, шумоподавление).
Зоны С текстом — только минимальный шарпенинг.
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from . import config


def enhance_image(
    image: Image.Image,
    text_mask: Image.Image | None = None,
) -> Image.Image:
    """
    Улучшает качество изображения, защищая текстовые зоны.

    Args:
        image: PIL Image (RGB или RGBA)
        text_mask: бинарная маска (L), белый = текст. None = нет текста.

    Returns:
        Улучшенное изображение
    """
    has_alpha = image.mode == "RGBA"
    alpha_channel = None

    if has_alpha:
        alpha_channel = image.getchannel("A")
        rgb = image.convert("RGB")
    else:
        rgb = image.convert("RGB")

    # --- Обработка зон БЕЗ текста ---
    enhanced_full = _enhance_full(rgb)

    # --- Обработка зон С текстом (мягкая) ---
    enhanced_text = _enhance_text_safe(rgb)

    # --- Слияние по маске ---
    if text_mask is not None and text_mask.getextrema()[1] > 0:
        # Маска есть и содержит текстовые зоны
        # Масштабируем маску под размер изображения если нужно
        if text_mask.size != rgb.size:
            text_mask = text_mask.resize(rgb.size, Image.LANCZOS)

        result = _blend_by_mask(enhanced_full, enhanced_text, text_mask)
        print("  OK: Quality enhanced (text zones protected)")
    else:
        result = enhanced_full
        print("  OK: Quality enhanced (no text - full processing)")

    # Возвращаем альфа-канал
    if has_alpha and alpha_channel is not None:
        result = result.convert("RGBA")
        # Масштабируем альфу если размер изменился
        if alpha_channel.size != result.size:
            alpha_channel = alpha_channel.resize(result.size, Image.LANCZOS)
        result.putalpha(alpha_channel)

    return result


def _enhance_full(image: Image.Image) -> Image.Image:
    """Полное улучшение для зон без текста."""
    result = image.copy()

    # 1. Шумоподавление (лёгкое)
    if config.DENOISE_STRENGTH > 0:
        result = _denoise(result)

    # 2. Автобаланс белого
    if config.WHITE_BALANCE_AUTO:
        result = _auto_white_balance(result)

    # 3. Насыщенность
    if config.SATURATION_BOOST != 1.0:
        enhancer = ImageEnhance.Color(result)
        result = enhancer.enhance(config.SATURATION_BOOST)

    # 4. Шарпенинг (полный)
    result = result.filter(ImageFilter.UnsharpMask(
        radius=config.SHARPEN_RADIUS,
        percent=config.SHARPEN_PERCENT,
        threshold=config.SHARPEN_THRESHOLD,
    ))

    return result


def _enhance_text_safe(image: Image.Image) -> Image.Image:
    """Мягкое улучшение для зон с текстом — только лёгкий шарпенинг."""
    result = image.copy()

    # Только мягкий шарпенинг — не трогаем цвет и не шумоподавляем
    result = result.filter(ImageFilter.UnsharpMask(
        radius=1,
        percent=config.TEXT_SHARPEN_PERCENT,
        threshold=5,
    ))

    return result


def _blend_by_mask(
    full_enhanced: Image.Image,
    text_enhanced: Image.Image,
    text_mask: Image.Image,
) -> Image.Image:
    """
    Смешивает два изображения по маске.
    Где маска белая (255) — берём text_enhanced.
    Где маска чёрная (0) — берём full_enhanced.
    """
    return Image.composite(text_enhanced, full_enhanced, text_mask)


def _denoise(image: Image.Image) -> Image.Image:
    """Лёгкое шумоподавление через OpenCV bilateral filter."""
    try:
        import cv2
        img_array = np.array(image)
        denoised = cv2.bilateralFilter(
            img_array,
            d=config.DENOISE_STRENGTH,
            sigmaColor=75,
            sigmaSpace=75,
        )
        return Image.fromarray(denoised)
    except ImportError:
        print("  WARN: OpenCV not installed - denoising skipped")
        return image


def _auto_white_balance(image: Image.Image) -> Image.Image:
    """Простой автобаланс белого через растяжение гистограммы."""
    img_array = np.array(image, dtype=np.float32)

    for channel in range(3):
        ch = img_array[:, :, channel]
        p_low = np.percentile(ch, 1)
        p_high = np.percentile(ch, 99)

        if p_high - p_low > 0:
            ch = np.clip((ch - p_low) * 255.0 / (p_high - p_low), 0, 255)
            img_array[:, :, channel] = ch

    return Image.fromarray(img_array.astype(np.uint8))
