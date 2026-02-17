"""
Вычисление позиций элементов на карточке.
Чистая математика — без рендеринга.
"""

from PIL import Image

from . import config
from .models import TextContent, CardLayout, LayoutZone


def compute_layout(
    card_width: int,
    card_height: int,
    product_image: Image.Image,
    text: TextContent,
    layout_type: str = "center",
) -> CardLayout:
    """
    Вычисляет позиции всех элементов карточки.

    Args:
        card_width: Ширина карточки
        card_height: Высота карточки
        product_image: RGBA изображение продукта
        text: Текстовый контент
        layout_type: "center" (продукт в центре)

    Returns:
        CardLayout со всеми зонами
    """
    if layout_type == "center":
        return _layout_center(card_width, card_height, product_image, text)
    else:
        return _layout_center(card_width, card_height, product_image, text)


def _layout_center(
    cw: int,
    ch: int,
    product_image: Image.Image,
    text: TextContent,
) -> CardLayout:
    """Layout: продукт по центру, заголовок вверху, цена внизу."""
    pad = config.TEXT_ZONE_PADDING_PX
    pw, ph = product_image.size

    # Получаем bbox контента (не пустых пикселей)
    bbox = _get_content_bbox(product_image)
    if bbox:
        content_w = bbox[2] - bbox[0]
        content_h = bbox[3] - bbox[1]
    else:
        content_w, content_h = pw, ph

    # Зоны для текста: верхняя (title + subtitle) и нижняя (price + badge)
    top_zone_height = 0
    if text.title:
        top_zone_height += int(config.TITLE_FONT_SIZE_PX * 2.5) + 10  # 2 строки
    if text.subtitle:
        top_zone_height += config.SUBTITLE_FONT_SIZE_PX + 15
    if top_zone_height > 0:
        top_zone_height += pad * 2

    bottom_zone_height = 0
    if text.price:
        bottom_zone_height += config.PRICE_FONT_SIZE_PX + 10
    if text.badge_text:
        bottom_zone_height += 50  # Badge height
    if bottom_zone_height > 0:
        bottom_zone_height += pad * 2

    # Bullets — сбоку от продукта или под subtitle
    bullets_height = 0
    if text.bullets:
        bullets_height = len(text.bullets) * (config.BULLET_FONT_SIZE_PX + 8) + pad * 2

    # Доступная область для продукта
    available_h = ch - top_zone_height - bottom_zone_height - pad * 2
    available_w = cw - pad * 2

    max_product_h = int(available_h * config.PRODUCT_MAX_HEIGHT_PCT)
    max_product_w = int(available_w * config.PRODUCT_MAX_WIDTH_PCT)

    # Масштаб продукта — по размеру контента (без прозрачных краёв)
    scale_w = max_product_w / content_w if content_w > 0 else 1.0
    scale_h = max_product_h / content_h if content_h > 0 else 1.0
    product_scale = min(scale_w, scale_h)

    # Размер области продукта = размер контента * масштаб
    scaled_content_w = int(content_w * product_scale)
    scaled_content_h = int(content_h * product_scale)
    # Полный размер изображения масштабируется пропорционально
    scaled_pw = int(pw * product_scale)
    scaled_ph = int(ph * product_scale)

    # Позиция продукта — по центру горизонтально, чуть ниже центра вертикально
    product_center_y = int(ch * config.PRODUCT_VERTICAL_CENTER_PCT)
    product_x = (cw - scaled_pw) // 2
    product_y = product_center_y - scaled_content_h // 2

    # Корректировка: не выходить за зоны текста
    if product_y < top_zone_height + pad:
        product_y = top_zone_height + pad
    if product_y + scaled_ph > ch - bottom_zone_height - pad:
        product_y = ch - bottom_zone_height - pad - scaled_ph

    layout = CardLayout(
        card_width=cw,
        card_height=ch,
        product_scale=product_scale,
    )

    # Зона продукта
    layout.product_zone = LayoutZone(
        name="product",
        x=product_x,
        y=product_y,
        width=scaled_pw,
        height=scaled_ph,
        z_index=10,
    )

    # Заголовок — верхняя часть (2 строки максимум)
    title_h = int(config.TITLE_FONT_SIZE_PX * 2.5) + 10
    if text.title:
        layout.title_zone = LayoutZone(
            name="title",
            x=pad,
            y=pad,
            width=cw - pad * 2,
            height=title_h,
            z_index=20,
        )

    # Подзаголовок — под заголовком
    if text.subtitle:
        title_bottom = pad + (title_h if text.title else 0)
        layout.subtitle_zone = LayoutZone(
            name="subtitle",
            x=pad,
            y=title_bottom + 5,
            width=cw - pad * 2,
            height=config.SUBTITLE_FONT_SIZE_PX + 15,
            z_index=20,
        )

    # Bullets — под subtitle или рядом с продуктом
    if text.bullets:
        bullets_y = top_zone_height + pad if top_zone_height > 0 else pad
        # Если продукт не занимает всю ширину — ставим bullets сбоку
        if scaled_pw < cw * 0.6:
            # Bullets справа от продукта
            bullets_x = product_x + scaled_pw + pad
            bullets_w = cw - bullets_x - pad
            bullets_y = product_y + scaled_ph // 4
        else:
            # Bullets под subtitle
            bullets_x = pad
            bullets_w = cw - pad * 2
            bullets_y = product_y + scaled_ph + pad

        layout.bullets_zone = LayoutZone(
            name="bullets",
            x=bullets_x,
            y=bullets_y,
            width=bullets_w,
            height=bullets_height,
            z_index=20,
        )

    # Цена — нижняя часть
    if text.price:
        layout.price_zone = LayoutZone(
            name="price",
            x=pad,
            y=ch - bottom_zone_height,
            width=cw - pad * 2,
            height=config.PRICE_FONT_SIZE_PX + 20,
            z_index=20,
        )

    # Badge — верхний правый угол
    if text.badge_text:
        badge_w = min(200, cw // 3)
        badge_h = 50
        layout.badge_zone = LayoutZone(
            name="badge",
            x=cw - badge_w - pad,
            y=pad,
            width=badge_w,
            height=badge_h,
            z_index=30,
        )

    print(f"  OK: Layout computed (center)")
    print(f"    Product: {scaled_pw}x{scaled_ph} at ({product_x}, {product_y}), scale={product_scale:.2f}")

    return layout


def _get_content_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Находит bbox непрозрачных пикселей."""
    if image.mode != "RGBA":
        return (0, 0, image.size[0], image.size[1])
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    return bbox
