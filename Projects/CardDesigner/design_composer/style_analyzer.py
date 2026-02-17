"""
Анализ стиля референсного изображения через Claude Vision.
Извлекает палитру, настроение, промпт для генерации фона.
"""

import base64
import io
import json

import anthropic
from PIL import Image

from . import config
from .models import DesignStyle


def analyze_reference_style(reference_image: Image.Image) -> DesignStyle:
    """
    Анализирует референсное изображение карточки через Claude Vision.

    Returns:
        DesignStyle с палитрой, настроением и промптом для Flux
    """
    if not config.ANTHROPIC_API_KEY:
        print("  WARN: Anthropic API key missing — using default style")
        return get_default_style()

    print("  Analyzing reference style via Claude Vision...")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # Уменьшаем для API
    img = reference_image.copy()
    max_dim = 1024
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

    if img.mode == "RGBA":
        rgb = Image.new("RGB", img.size, (255, 255, 255))
        rgb.paste(img, mask=img.getchannel("A"))
        img = rgb

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    prompt = """Analyze this marketplace product card design. Extract the visual style.

Return ONLY valid JSON (no markdown):
{
    "color_palette": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5"],
    "background_mood": "description of background style (e.g. soft gradient, nature bokeh, dark minimal)",
    "typography_style": "description of text style (e.g. bold sans-serif white, elegant dark serif)",
    "layout_type": "center or left-product or full-bleed",
    "bg_generation_prompt": "English prompt for AI image generator to create a similar background. Include colors, mood, lighting. Must say 'no products, no text, background only'."
}

color_palette: 5-7 dominant HEX colors from the design.
background_mood: describe the background feel.
layout_type: how is the product positioned.
bg_generation_prompt: detailed prompt to recreate a SIMILAR background in Flux AI."""

    try:
        response = client.messages.create(
            model=config.STYLE_ANALYSIS_MODEL,
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

        style = DesignStyle(
            color_palette=data.get("color_palette", []),
            background_mood=data.get("background_mood", ""),
            typography_style=data.get("typography_style", ""),
            layout_type=data.get("layout_type", "center"),
            bg_generation_prompt=data.get("bg_generation_prompt", ""),
            raw_analysis=raw,
        )

        print(f"  OK: Style analyzed")
        print(f"    Mood: {style.background_mood}")
        print(f"    Colors: {style.color_palette[:3]}...")

        return style

    except Exception as e:
        print(f"  ERROR style analysis: {e}")
        return get_default_style()


def get_default_style(marketplace: str = "wb") -> DesignStyle:
    """Дефолтный стиль."""
    return DesignStyle(
        color_palette=["#2d3436", "#e17055", "#ffffff", "#dfe6e9", "#74b9ff"],
        background_mood="clean minimal gradient",
        typography_style="bold sans-serif",
        layout_type="center",
        bg_generation_prompt="clean minimal product photography background, soft pastel gradient from light blue to white, gentle abstract light, no objects, no text, no products, professional studio, smooth bokeh",
    )
