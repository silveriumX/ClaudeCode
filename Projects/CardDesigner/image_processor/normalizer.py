"""
Нормализация изображения: центрирование, паддинг, финальный размер.
НЕ обрезает и НЕ растягивает товар.
"""

from PIL import Image

from . import config


def normalize_image(
    image: Image.Image,
    padding_percent: float | None = None,
    target_min_size: int | None = None,
) -> Image.Image:
    """
    Нормализует изображение: центрирует товар и добавляет padding.

    Args:
        image: PIL Image (RGBA с прозрачным фоном)
        padding_percent: процент padding от размера (0.0-0.5)
        target_min_size: минимальный размер большей стороны

    Returns:
        Нормализованное изображение (RGBA)
    """
    if padding_percent is None:
        padding_percent = config.DEFAULT_PADDING_PERCENT
    if target_min_size is None:
        target_min_size = config.TARGET_MIN_SIZE

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # 1. Находим bounding box непрозрачных пикселей
    bbox = _get_content_bbox(image)
    if bbox is None:
        print("  WARN: No content found - returning original")
        return image

    x_min, y_min, x_max, y_max = bbox
    content_w = x_max - x_min
    content_h = y_max - y_min

    # 2. Вырезаем содержимое
    content = image.crop((x_min, y_min, x_max, y_max))

    # 3. Рассчитываем размер холста с padding
    pad_x = int(content_w * padding_percent)
    pad_y = int(content_h * padding_percent)

    canvas_w = content_w + pad_x * 2
    canvas_h = content_h + pad_y * 2

    # 4. Проверяем минимальный размер
    max_side = max(canvas_w, canvas_h)
    if max_side < target_min_size:
        scale = target_min_size / max_side
        canvas_w = int(canvas_w * scale)
        canvas_h = int(canvas_h * scale)
        content = content.resize(
            (int(content_w * scale), int(content_h * scale)),
            Image.LANCZOS,
        )
        content_w, content_h = content.size
        pad_x = (canvas_w - content_w) // 2
        pad_y = (canvas_h - content_h) // 2

    # 5. Создаём холст и центрируем
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    paste_x = (canvas_w - content_w) // 2
    paste_y = (canvas_h - content_h) // 2
    canvas.paste(content, (paste_x, paste_y), content)

    print(f"  OK: Normalized {image.size[0]}x{image.size[1]} -> {canvas_w}x{canvas_h} (padding: {padding_percent:.0%})")

    return canvas


def _get_content_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    """
    Находит bounding box непрозрачного содержимого.

    Returns:
        (x_min, y_min, x_max, y_max) или None если всё прозрачное
    """
    if image.mode != "RGBA":
        return (0, 0, image.size[0], image.size[1])

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()

    if bbox is None:
        return None

    return bbox
