"""
Детекция текстовых зон на товаре через Claude Vision API.
Без локальных моделей — всё через API.
"""

import base64
import io
import json
from dataclasses import dataclass, field

import anthropic
from PIL import Image, ImageDraw, ImageFilter

from . import config


@dataclass
class TextRegion:
    """Одна текстовая область."""
    x: int
    y: int
    width: int
    height: int
    text: str


@dataclass
class TextDetectionResult:
    """Результат детекции текста."""
    regions: list[TextRegion] = field(default_factory=list)
    text_mask: Image.Image | None = None
    has_text: bool = False

    @property
    def detected_texts(self) -> list[str]:
        return [r.text for r in self.regions]

    @property
    def count(self) -> int:
        return len(self.regions)


def detect_text_regions(image: Image.Image) -> TextDetectionResult:
    """Находит текстовые области на товаре через Claude Vision."""
    if not config.ANTHROPIC_API_KEY:
        print("  WARN: Anthropic API key missing - text detection skipped")
        return TextDetectionResult(text_mask=Image.new("L", image.size, 0), has_text=False)

    print("  Detecting text via Claude Vision...")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # Уменьшаем для API
    img_for_api = image.copy()
    max_dim = 1024
    if max(img_for_api.size) > max_dim:
        ratio = max_dim / max(img_for_api.size)
        new_size = (int(img_for_api.size[0] * ratio), int(img_for_api.size[1] * ratio))
        img_for_api = img_for_api.resize(new_size, Image.LANCZOS)

    if img_for_api.mode == "RGBA":
        rgb = Image.new("RGB", img_for_api.size, (255, 255, 255))
        rgb.paste(img_for_api, mask=img_for_api.getchannel("A"))
        img_for_api = rgb

    buf = io.BytesIO()
    img_for_api.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    prompt = """Analyze this product image. Find ALL text on the product (labels, brand name, descriptions, certifications).

For each text area, provide its approximate bounding box as percentage of image dimensions.

Return ONLY valid JSON (no markdown):
{"regions": [{"x_pct": 0.2, "y_pct": 0.3, "w_pct": 0.5, "h_pct": 0.1, "text": "example text"}], "has_text": true}

x_pct, y_pct = top-left corner as fraction (0.0-1.0)
w_pct, h_pct = width and height as fraction (0.0-1.0)

If no text found: {"regions": [], "has_text": false}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        )

        raw = response.content[0].text
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]

        data = json.loads(clean)

        regions = []
        for r in data.get("regions", []):
            x = int(r["x_pct"] * image.size[0])
            y = int(r["y_pct"] * image.size[1])
            w = int(r["w_pct"] * image.size[0])
            h = int(r["h_pct"] * image.size[1])
            regions.append(TextRegion(x=x, y=y, width=w, height=h, text=r.get("text", "")))

        has_text = len(regions) > 0

        if has_text:
            text_mask = _create_text_mask(image.size, regions)
            print(f"  OK: Found {len(regions)} text zones:")
            for r in regions[:5]:
                print(f"    '{r.text}'")
        else:
            text_mask = Image.new("L", image.size, 0)
            print("  No text found on product")

        return TextDetectionResult(regions=regions, text_mask=text_mask, has_text=has_text)

    except Exception as e:
        print(f"  ERROR text detection: {e}")
        return TextDetectionResult(text_mask=Image.new("L", image.size, 0), has_text=False)


def _create_text_mask(size: tuple[int, int], regions: list[TextRegion]) -> Image.Image:
    """Создаёт бинарную маску текстовых зон с padding."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    padding = config.TEXT_MASK_PADDING

    for r in regions:
        x1 = max(0, r.x - padding)
        y1 = max(0, r.y - padding)
        x2 = min(size[0], r.x + r.width + padding)
        y2 = min(size[1], r.y + r.height + padding)
        draw.rectangle([x1, y1, x2, y2], fill=255)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=3))
    return mask
