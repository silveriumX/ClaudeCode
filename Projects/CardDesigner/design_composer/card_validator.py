"""
Валидация готовой карточки через Claude Vision.
Проверяет качество, читаемость текста, композицию.
"""

import base64
import io
import json

import anthropic
from PIL import Image

from . import config
from .models import CardSpec


def validate_card(
    card_image: Image.Image,
    spec: CardSpec,
) -> tuple[int, list[str]]:
    """
    Валидирует готовую карточку через Claude Vision.

    Returns:
        (score, issues) — оценка 1-10 и список проблем
    """
    if not config.ANTHROPIC_API_KEY:
        print("  WARN: Anthropic API key missing — validation skipped")
        return (0, ["API key missing"])

    print("  Validating card via Claude Vision...")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # Уменьшаем для API
    img = card_image.copy()
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

    marketplace = spec.marketplace.upper()
    prompt = f"""Evaluate this {marketplace} marketplace product card design.

Score 1-10 and list any issues. Return ONLY valid JSON (no markdown):
{{
    "score": 8,
    "product_visible": true,
    "text_readable": true,
    "background_appropriate": true,
    "overall_professional": true,
    "issues": ["issue1", "issue2"]
}}

Check:
- Is the product clearly visible and not cropped?
- Is text readable and well-positioned?
- Does the background complement the product?
- Does it look professional for a marketplace listing?
- Are colors harmonious?
- Any visual artifacts or layout problems?"""

    try:
        response = client.messages.create(
            model=config.CARD_VALIDATION_MODEL,
            max_tokens=500,
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
        score = data.get("score", 0)
        issues = data.get("issues", [])

        print(f"  OK: Score {score}/10, {len(issues)} issues")
        if issues:
            for issue in issues[:3]:
                print(f"    - {issue}")

        return (score, issues)

    except Exception as e:
        print(f"  ERROR validation: {e}")
        return (0, [str(e)])
