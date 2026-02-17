"""
Генерация фона для карточки через Flux 1.1 Pro (Replicate API).
Fallback — программный градиент через Pillow.
"""

import io
import os
import time

from PIL import Image, ImageDraw

from . import config
from .models import DesignStyle


def generate_background(
    width: int,
    height: int,
    style: DesignStyle,
    method: str = "flux",
) -> Image.Image:
    """
    Генерирует фон для карточки.

    Args:
        width: Ширина карточки
        height: Высота карточки
        style: Стиль дизайна с промптом и палитрой
        method: "flux", "recraft" или "gradient"

    Returns:
        PIL Image (RGB) — фон
    """
    if method == "gradient" or not config.REPLICATE_API_TOKEN:
        if not config.REPLICATE_API_TOKEN:
            print("  WARN: Replicate API недоступен, используем градиент")
        return _generate_gradient(width, height, style.color_palette)

    if method == "recraft":
        return _generate_recraft(width, height, style)

    return _generate_flux(width, height, style)


def _generate_flux(width: int, height: int, style: DesignStyle) -> Image.Image:
    """Генерация фона через Flux 1.1 Pro."""
    import replicate

    token = config.REPLICATE_API_TOKEN or os.environ.get("REPLICATE_API_TOKEN", "")
    client = replicate.Client(api_token=token)

    # Формируем промпт для фона
    prompt = style.bg_generation_prompt
    if not prompt:
        prompt = "clean minimal product photography background, soft gradient, light neutral colors, no objects, no text, no products, professional studio lighting"

    # Добавляем указание "без продукта"
    if "no product" not in prompt.lower():
        prompt += ", no products, no objects, no text, empty background only"

    print(f"  Generating background via Flux 1.1 Pro...")
    print(f"  Prompt: {prompt[:80]}...")

    start = time.time()

    try:
        # Flux 1.1 Pro принимает aspect_ratio, не width/height напрямую
        # Для 3:4 используем "3:4"
        aspect = f"{width}:{height}"
        # Упрощаем до стандартных
        if width * 4 == height * 3:
            aspect = "3:4"

        output = client.run(
            config.FLUX_MODEL,
            input={
                "prompt": prompt,
                "aspect_ratio": aspect,
                "output_format": "png",
                "safety_tolerance": 5,
            },
        )

        # Скачиваем результат
        if hasattr(output, 'read'):
            result_bytes = output.read()
        elif isinstance(output, list) and len(output) > 0:
            item = output[0]
            if hasattr(item, 'read'):
                result_bytes = item.read()
            else:
                import urllib.request
                req = urllib.request.Request(str(item), headers={"User-Agent": "CardDesigner/1.0"})
                result_bytes = urllib.request.urlopen(req).read()
        else:
            import urllib.request
            req = urllib.request.Request(str(output), headers={"User-Agent": "CardDesigner/1.0"})
            result_bytes = urllib.request.urlopen(req).read()

        result = Image.open(io.BytesIO(result_bytes)).convert("RGB")

        # Ресайзим до точных размеров карточки
        if result.size != (width, height):
            result = result.resize((width, height), Image.LANCZOS)

        elapsed = time.time() - start
        print(f"  OK: Fon sgenerirovan ({elapsed:.1f}s, {width}x{height})")

        return result

    except Exception as e:
        print(f"  ERROR Flux: {e}")
        print(f"  Fallback to gradient")
        return _generate_gradient(width, height, style.color_palette)


def _generate_recraft(width: int, height: int, style: DesignStyle) -> Image.Image:
    """Генерация фона через Recraft V3."""
    import replicate

    token = config.REPLICATE_API_TOKEN or os.environ.get("REPLICATE_API_TOKEN", "")
    client = replicate.Client(api_token=token)

    prompt = style.bg_generation_prompt or "clean minimal background, soft gradient, professional"
    if "no product" not in prompt.lower():
        prompt += ", no products, no text, empty background"

    print(f"  Generating background via Recraft V3...")

    start = time.time()

    try:
        output = client.run(
            config.RECRAFT_MODEL,
            input={
                "prompt": prompt,
                "size": f"{width}x{height}",
            },
        )

        if hasattr(output, 'read'):
            result_bytes = output.read()
        elif isinstance(output, list) and len(output) > 0:
            item = output[0]
            result_bytes = item.read() if hasattr(item, 'read') else __import__('urllib.request').request.urlopen(str(item)).read()
        else:
            result_bytes = output.read() if hasattr(output, 'read') else __import__('urllib.request').request.urlopen(str(output)).read()

        result = Image.open(io.BytesIO(result_bytes)).convert("RGB")
        if result.size != (width, height):
            result = result.resize((width, height), Image.LANCZOS)

        elapsed = time.time() - start
        print(f"  OK: Recraft fon ({elapsed:.1f}s, {width}x{height})")
        return result

    except Exception as e:
        print(f"  ERROR Recraft: {e}")
        return _generate_gradient(width, height, style.color_palette)


def _generate_gradient(
    width: int,
    height: int,
    colors: list[str] | None = None,
) -> Image.Image:
    """Программный градиент как fallback."""
    if not colors or len(colors) < 2:
        colors = ["#f0f4f8", "#d1e3f8"]  # Нежный светло-голубой

    # Парсим цвета
    def hex_to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    c1 = hex_to_rgb(colors[0])
    c2 = hex_to_rgb(colors[1] if len(colors) > 1 else colors[0])

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(c1[0] + (c2[0] - c1[0]) * y / height)
        g = int(c1[1] + (c2[1] - c1[1]) * y / height)
        b = int(c1[2] + (c2[2] - c1[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    print(f"  OK: Gradient fon ({width}x{height})")
    return img
