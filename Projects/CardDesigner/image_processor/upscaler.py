"""
Апскейл изображений.
AI-метод (Real-ESRGAN через Replicate) для зон без текста.
Классический метод (Lanczos) для зон с текстом.
"""

import io
import time

from PIL import Image

from . import config


def needs_upscale(image: Image.Image) -> bool:
    """Проверяет, нужен ли апскейл."""
    min_side = min(image.size)
    needs = min_side < config.MIN_RESOLUTION
    if needs:
        print(f"  Resolution {image.size[0]}x{image.size[1]} < {config.MIN_RESOLUTION} - upscale needed")
    else:
        print(f"  Resolution {image.size[0]}x{image.size[1]} >= {config.MIN_RESOLUTION} - upscale not needed")
    return needs


def upscale_classical(image: Image.Image, factor: int = 2) -> Image.Image:
    """Классический апскейл через Lanczos (безопасен для текста)."""
    new_size = (image.size[0] * factor, image.size[1] * factor)
    result = image.resize(new_size, Image.LANCZOS)
    print(f"  OK: Lanczos upscale {factor}x: {image.size[0]}x{image.size[1]} -> {result.size[0]}x{result.size[1]}")
    return result


def upscale_ai(image: Image.Image, factor: int = 2) -> Image.Image:
    """AI-апскейл через Real-ESRGAN (Replicate API)."""
    if not config.REPLICATE_API_TOKEN:
        print("  WARN: Replicate API unavailable, using Lanczos")
        return upscale_classical(image, factor)

    import os
    import replicate

    print(f"  Sending to Real-ESRGAN (Replicate), factor={factor}...")

    token = config.REPLICATE_API_TOKEN or os.environ.get("REPLICATE_API_TOKEN", "")
    client = replicate.Client(api_token=token)

    img_bytes = io.BytesIO()
    if image.mode == "RGBA":
        rgb = Image.new("RGB", image.size, (255, 255, 255))
        rgb.paste(image, mask=image.getchannel("A"))
        rgb.save(img_bytes, format="PNG")
    else:
        image.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    start = time.time()

    try:
        output = client.run(
            config.REALESRGAN_MODEL,
            input={"image": img_bytes, "scale": factor, "face_enhance": False},
        )

        if hasattr(output, 'read'):
            result_bytes = output.read()
        else:
            import urllib.request
            req = urllib.request.Request(str(output), headers={"User-Agent": "CardDesigner/1.0"})
            result_bytes = urllib.request.urlopen(req).read()
        result = Image.open(io.BytesIO(result_bytes))

        elapsed = time.time() - start
        print(f"  OK: AI upscale {factor}x: {image.size[0]}x{image.size[1]} -> {result.size[0]}x{result.size[1]} ({elapsed:.1f}s)")

        if image.mode == "RGBA":
            alpha = image.getchannel("A")
            alpha_upscaled = alpha.resize(result.size, Image.LANCZOS)
            result = result.convert("RGBA")
            result.putalpha(alpha_upscaled)

        return result

    except Exception as e:
        print(f"  ERROR AI upscale: {e}")
        print("  Fallback to Lanczos")
        return upscale_classical(image, factor)


def upscale_image(image: Image.Image, method: str = "ai", factor: int = 2) -> Image.Image:
    """Универсальная функция апскейла."""
    factor = min(factor, config.MAX_UPSCALE_FACTOR)
    if method == "ai":
        return upscale_ai(image, factor)
    else:
        return upscale_classical(image, factor)
