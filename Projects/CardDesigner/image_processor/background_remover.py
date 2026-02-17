"""
Удаление фона с фото товара.
Использует Replicate API (модель lucataco/remove-bg) — без локальных моделей.
"""

import io
import os
import time
from pathlib import Path

from PIL import Image

from . import config

# Модель + version hash (обязателен для работы)
BG_REMOVE_MODEL = "lucataco/remove-bg:95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1"


def remove_background(image: Image.Image) -> Image.Image:
    """
    Удаляет фон с изображения товара через Replicate API.

    Args:
        image: PIL Image (RGB или RGBA)

    Returns:
        PIL Image (RGBA) с прозрачным фоном
    """
    print("  Background removal via Replicate API...")

    import replicate

    token = config.REPLICATE_API_TOKEN or os.environ.get("REPLICATE_API_TOKEN", "")
    client = replicate.Client(api_token=token)

    # Конвертируем в PNG bytes
    img_bytes = io.BytesIO()
    if image.mode == "RGBA":
        image.convert("RGB").save(img_bytes, format="PNG")
    else:
        image.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    start = time.time()

    try:
        output = client.run(
            BG_REMOVE_MODEL,
            input={"image": img_bytes},
        )

        # output — FileOutput (можно read()) или URL
        if hasattr(output, 'read'):
            result_bytes = output.read()
        else:
            import urllib.request
            req = urllib.request.Request(str(output), headers={"User-Agent": "CardDesigner/1.0"})
            result_bytes = urllib.request.urlopen(req).read()

        result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

        elapsed = time.time() - start
        print(f"  OK: Fon udalen ({elapsed:.1f}s, {result.size[0]}x{result.size[1]})")

        return result

    except Exception as e:
        print(f"  ERROR background removal: {e}")
        raise


def remove_background_from_file(input_path: Path, output_path: Path) -> Path:
    """Удаляет фон из файла и сохраняет результат."""
    image = Image.open(input_path).convert("RGB")
    result = remove_background(image)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, format="PNG")
    return output_path
