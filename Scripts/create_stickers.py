"""
Генератор наклеек для Wildberries в зелёных и синих тонах
На основе оригинального дизайна из Figma
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_sticker(
    output_path: Path,
    color_scheme: str = "green",
    quantity: str = "4 шт",
    size: tuple = (1748, 550)
):
    """
    Создать наклейку с градиентом и текстом.

    Args:
        output_path: Путь для сохранения PNG
        color_scheme: "green", "blue", или "red-yellow"
        quantity: Текст количества (например, "4 шт", "6 шт")
        size: Размер изображения (width, height)
    """
    width, height = size

    # Создать изображение
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Цветовые схемы
    colors = {
        "green": {
            "gradient_start": (0, 200, 81),      # Яркий зелёный
            "gradient_end": (0, 150, 60),        # Темнее зелёный
            "glow": (0, 255, 100, 200)           # Яркое зелёное свечение
        },
        "blue": {
            "gradient_start": (0, 123, 255),     # Яркий синий
            "gradient_end": (0, 90, 200),        # Темнее синий
            "glow": (100, 150, 255, 200)         # Яркое синее свечение
        },
        "red-yellow": {
            "gradient_start": (255, 199, 0),     # Желтый
            "gradient_end": (255, 100, 0),       # Оранжево-красный
            "glow": (255, 220, 100, 200)         # Желтое свечение
        }
    }

    scheme = colors.get(color_scheme, colors["green"])

    # Нарисовать градиентный фон (линейный)
    for x in range(width):
        # Градиент слева направо
        ratio = x / width

        if ratio < 0.3:
            # Левая часть - полный цвет
            color = scheme["gradient_start"]
        elif ratio > 0.7:
            # Правая часть - полный цвет
            color = scheme["gradient_start"]
        else:
            # Середина - затухание
            fade = (ratio - 0.3) / 0.4  # 0 to 1
            alpha = int(255 * (1 - fade))
            color = (*scheme["gradient_start"], alpha)

        draw.line([(x, 0), (x, height)], fill=color, width=1)

    # Добавить радиальное свечение (эллипс слева)
    glow_size = 300
    glow_x = 250
    glow_y = height // 2

    # Создать отдельный слой для свечения
    glow_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # Нарисовать эллипс с градиентом
    for i in range(3):
        radius = glow_size - (i * 60)
        alpha = 100 - (i * 30)
        glow_color = (*scheme["glow"][:3], alpha)

        bbox = [
            glow_x - radius,
            glow_y - radius,
            glow_x + radius,
            glow_y + radius
        ]
        glow_draw.ellipse(bbox, fill=glow_color)

    # Применить blur для мягкого свечения
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=30))

    # Объединить слои
    img = Image.alpha_composite(img, glow_layer)

    # Добавить тень для бэйджа
    badge_width = 400
    badge_height = 180
    badge_x = width - badge_width - 80
    badge_y = (height - badge_height) // 2

    # Тень
    shadow_offset = 8
    shadow_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.rounded_rectangle(
        [badge_x + shadow_offset, badge_y + shadow_offset,
         badge_x + badge_width + shadow_offset, badge_y + badge_height + shadow_offset],
        radius=15,
        fill=(0, 0, 0, 80)
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=10))
    img = Image.alpha_composite(img, shadow_layer)

    # Белый бэйдж с количеством
    badge_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge_layer)
    badge_draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
        radius=15,
        fill=(255, 255, 255, 250)
    )
    img = Image.alpha_composite(img, badge_layer)

    # Добавить текст количества
    try:
        # Попробовать найти жирный шрифт
        font_path = "C:/Windows/Fonts/arialbd.ttf"  # Arial Bold
        if not Path(font_path).exists():
            font_path = "C:/Windows/Fonts/arial.ttf"

        font = ImageFont.truetype(font_path, 120)
    except:
        logger.warning("Не удалось загрузить шрифт, используется стандартный")
        font = ImageFont.load_default()

    # Нарисовать текст на финальном изображении
    final_draw = ImageDraw.Draw(img)

    # Получить размер текста
    bbox = final_draw.textbbox((0, 0), quantity, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Центрировать текст в бэйдже
    text_x = badge_x + (badge_width - text_width) // 2
    text_y = badge_y + (badge_height - text_height) // 2 - 10

    final_draw.text((text_x, text_y), quantity, fill=(0, 0, 0, 255), font=font)

    # Сохранить
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, 'PNG')
    logger.info(f"Наклейка сохранена: {output_path}")


# Использование
if __name__ == "__main__":
    output_dir = Path("../exports/stickers")

    logger.info("Генерация наклеек для Wildberries...")

    # Зелёная - 4 шт
    create_sticker(
        output_dir / "nakleiyka-4sht-green.png",
        color_scheme="green",
        quantity="4 шт"
    )

    # Синяя - 6 шт
    create_sticker(
        output_dir / "nakleiyka-6sht-blue.png",
        color_scheme="blue",
        quantity="6 шт"
    )

    # Оригинал для сравнения
    create_sticker(
        output_dir / "nakleiyka-original.png",
        color_scheme="red-yellow",
        quantity="NEXR"
    )

    logger.info("\nГотово! Наклейки сохранены в: exports/stickers/")
    logger.info("\nФайлы:")
    logger.info("  - nakleiyka-4sht-green.png (Зелёная, 4 шт)")
    logger.info("  - nakleiyka-6sht-blue.png (Синяя, 6 шт)")
    logger.info("  - nakleiyka-original.png (Оригинал)")
