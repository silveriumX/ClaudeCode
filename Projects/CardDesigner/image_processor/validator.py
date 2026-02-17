"""
Валидация результата через Claude Vision API.
Сравнивает оригинал и обработанное фото, проверяет сохранность текста.
"""

import base64
import io
import json
from dataclasses import dataclass, field

from PIL import Image

from . import config


@dataclass
class ValidationResult:
    """Результат валидации."""
    text_ok: bool = True
    proportions_ok: bool = True
    elements_ok: bool = True
    quality_improved: bool = True
    score: int = 0
    issues: list[str] = field(default_factory=list)
    raw_response: str = ""

    @property
    def passed(self) -> bool:
        return self.score >= config.VALIDATION_MIN_SCORE


def validate_result(
    original: Image.Image,
    processed: Image.Image,
) -> ValidationResult:
    """
    Сравнивает оригинал и результат через Claude Vision.

    Args:
        original: исходное фото
        processed: обработанное фото

    Returns:
        ValidationResult
    """
    if not config.ANTHROPIC_API_KEY:
        print("  WARN: Claude API unavailable - validation skipped")
        return ValidationResult(score=8, raw_response="API недоступен, валидация пропущена")

    import anthropic

    print("  Sending to Claude Vision for validation...")

    # Конвертируем изображения в base64
    original_b64 = _image_to_base64(original, max_size=1024)
    processed_b64 = _image_to_base64(processed, max_size=1024)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    prompt = """Сравни два изображения товара: ОРИГИНАЛ и ОБРАБОТАННОЕ.

Проверь:
1. text_ok: Текст на товаре (этикетки, надписи на упаковке) читаем и не искажён?
2. proportions_ok: Пропорции товара сохранены? Ничего не растянуто/сжато?
3. elements_ok: Все элементы товара на месте? Ничего не пропало и не добавилось?
4. quality_improved: Визуальное качество улучшилось (резкость, цвета, детали)?

Ответь СТРОГО в формате JSON (без markdown):
{"text_ok": true/false, "proportions_ok": true/false, "elements_ok": true/false, "quality_improved": true/false, "score": 1-10, "issues": ["проблема 1", "проблема 2"]}

score 10 = идеально, 7+ = хорошо, <7 = есть проблемы.
Если issues пуст — значит всё отлично."""

    try:
        response = client.messages.create(
            model=config.VALIDATION_MODEL,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "ОРИГИНАЛ:"},
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": original_b64,
                    }},
                    {"type": "text", "text": "ОБРАБОТАННОЕ:"},
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": processed_b64,
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        )

        raw = response.content[0].text
        result = _parse_validation_response(raw)
        result.raw_response = raw

        if result.passed:
            print(f"  OK: Validation passed (score: {result.score}/10)")
        else:
            print(f"  FAIL: Validation failed (score: {result.score}/10)")

        if not result.text_ok:
            print("  FAIL: Text on product is damaged!")
        if not result.proportions_ok:
            print("  FAIL: Proportions changed!")
        if not result.elements_ok:
            print("  FAIL: Product elements changed!")
        for issue in result.issues:
            print(f"  WARN: {issue}")

        return result

    except Exception as e:
        print(f"  ERROR validation: {e}")
        return ValidationResult(score=0, issues=[str(e)], raw_response=str(e))


def _image_to_base64(image: Image.Image, max_size: int = 1024) -> str:
    """Конвертирует изображение в base64, уменьшая если нужно."""
    img = image.copy()

    # Уменьшаем для API (экономия токенов)
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    if img.mode == "RGBA":
        # Белый фон для Claude Vision
        rgb = Image.new("RGB", img.size, (255, 255, 255))
        rgb.paste(img, mask=img.getchannel("A"))
        img = rgb

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _parse_validation_response(raw: str) -> ValidationResult:
    """Парсит JSON ответ от Claude."""
    try:
        # Убираем возможные markdown-обёртки
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]

        data = json.loads(clean)
        return ValidationResult(
            text_ok=data.get("text_ok", True),
            proportions_ok=data.get("proportions_ok", True),
            elements_ok=data.get("elements_ok", True),
            quality_improved=data.get("quality_improved", False),
            score=data.get("score", 5),
            issues=data.get("issues", []),
        )
    except (json.JSONDecodeError, KeyError) as e:
        return ValidationResult(
            score=5,
            issues=[f"Не удалось распарсить ответ Claude: {e}"],
            raw_response=raw,
        )
