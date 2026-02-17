"""
Основной пайплайн Design Composer.
Оркестрирует: анализ стиля → генерация фона → layout → рендер → валидация.
"""

import json
import time
from pathlib import Path

from PIL import Image

from . import config
from .models import CardSpec, CardResult, TextContent, DesignStyle, CardLayout
from .background_generator import generate_background
from .layout_engine import compute_layout
from .template_renderer import render_card_sync


class DesignComposerPipeline:
    """Пайплайн создания карточек для маркетплейсов."""

    def __init__(
        self,
        analyze_style: bool = True,
        generate_bg: bool = True,
        validate: bool = False,
        bg_method: str = "flux",
        template_name: str = "base",
        save_intermediate: bool = True,
    ):
        self.analyze_style = analyze_style
        self.generate_bg = generate_bg
        self.validate = validate
        self.bg_method = bg_method
        self.template_name = template_name
        self.save_intermediate = save_intermediate

    def compose_single(self, spec: CardSpec, output_dir: Path) -> CardResult:
        """Создаёт одну карточку через весь пайплайн."""
        result = CardResult(spec=spec)
        start_time = time.time()

        output_dir.mkdir(parents=True, exist_ok=True)
        intermediate_dir = output_dir / "intermediate"
        if self.save_intermediate:
            intermediate_dir.mkdir(parents=True, exist_ok=True)

        stem = spec.product_image_path.stem
        card_w, card_h = config.CARD_SIZES.get(spec.marketplace, (900, 1200))

        try:
            print(f"\n{'='*60}")
            print(f"Composing card: {spec.product_image_path.name} ({spec.marketplace.upper()} {card_w}x{card_h})")
            print(f"{'='*60}")

            # --- Step 1/5: Style Analysis ---
            print("\nStep 1/5: Style analysis")
            style = spec.style_override
            if not style:
                if self.analyze_style and spec.reference_image_path:
                    try:
                        from .style_analyzer import analyze_reference_style
                        ref_image = Image.open(spec.reference_image_path)
                        style = analyze_reference_style(ref_image)
                        result.steps_completed.append("style_analysis")
                        if self.save_intermediate:
                            _save_json(intermediate_dir / f"{stem}_01_style.json", {
                                "color_palette": style.color_palette,
                                "background_mood": style.background_mood,
                                "bg_generation_prompt": style.bg_generation_prompt,
                            })
                    except Exception as e:
                        print(f"  WARN: Style analysis failed: {e}")
                        style = _get_default_style()
                else:
                    style = _get_default_style()
                    print(f"  Using default style")
            else:
                print(f"  Using provided style override")
            result.style = style

            # --- Step 2/5: Background Generation ---
            print("\nStep 2/5: Background generation")
            if self.generate_bg:
                background = generate_background(card_w, card_h, style, method=self.bg_method)
                result.steps_completed.append("background_generation")
                if self.save_intermediate:
                    background.save(intermediate_dir / f"{stem}_02_background.png")
            else:
                # Белый фон по умолчанию
                background = Image.new("RGB", (card_w, card_h), (255, 255, 255))
                print(f"  Using white background")

            result.background_path = intermediate_dir / f"{stem}_02_background.png" if self.save_intermediate else None

            # --- Step 3/5: Layout ---
            print("\nStep 3/5: Layout computation")
            product_image = Image.open(spec.product_image_path).convert("RGBA")
            print(f"  Product: {product_image.size[0]}x{product_image.size[1]}")

            layout = compute_layout(
                card_w, card_h, product_image, spec.text,
                layout_type=style.layout_type if style.layout_type else "center",
            )
            result.layout = layout
            result.steps_completed.append("layout")

            if self.save_intermediate:
                _save_json(intermediate_dir / f"{stem}_03_layout.json", {
                    "card": f"{card_w}x{card_h}",
                    "product_zone": _zone_to_dict(layout.product_zone),
                    "title_zone": _zone_to_dict(layout.title_zone),
                    "product_scale": layout.product_scale,
                })

            # --- Step 4/5: Render ---
            print("\nStep 4/5: Template rendering")
            rendered_path = output_dir / f"{stem}_card_{spec.marketplace}.png"
            render_card_sync(
                background=background,
                product_image=product_image,
                text=spec.text,
                layout=layout,
                style=style,
                output_path=rendered_path,
                template_name=self.template_name,
            )
            result.output_png_path = rendered_path
            result.steps_completed.append("rendering")

            # Сохраняем JPG версию
            if config.OUTPUT_FORMAT_JPG:
                jpg_path = output_dir / f"{stem}_card_{spec.marketplace}.jpg"
                card_img = Image.open(rendered_path).convert("RGB")
                card_img.save(jpg_path, format="JPEG", quality=config.JPG_QUALITY)
                result.output_jpg_path = jpg_path
                print(f"  Saved JPG: {jpg_path.name}")

            # --- Step 5/5: Validation ---
            if self.validate:
                print("\nStep 5/5: Card validation")
                try:
                    from .card_validator import validate_card
                    card_img = Image.open(rendered_path)
                    score, issues = validate_card(card_img, spec)
                    result.validation_score = score
                    result.validation_issues = issues
                    result.steps_completed.append("validation")
                    print(f"  Score: {score}/10")
                except Exception as e:
                    print(f"  WARN: Validation failed: {e}")
            else:
                print("\nStep 5/5: Validation (skipped)")

            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False
            print(f"\n  ERROR: {e}")
            import traceback
            traceback.print_exc()

        result.elapsed_seconds = time.time() - start_time
        return result

    def compose_batch(self, specs: list[CardSpec], output_dir: Path) -> list[CardResult]:
        """Создаёт несколько карточек."""
        if not specs:
            print("No card specs provided")
            return []

        print(f"\nComposing {len(specs)} cards\n")
        results = []
        for i, spec in enumerate(specs, 1):
            print(f"\n[{i}/{len(specs)}]")
            result = self.compose_single(spec, output_dir)
            results.append(result)

        return results


def _get_default_style() -> DesignStyle:
    """Дефолтный стиль — тёмный premium."""
    return DesignStyle(
        color_palette=["#0a0a0a", "#e17055", "#ffffff"],
        background_mood="dark premium studio",
        typography_style="bold sans-serif",
        layout_type="center",
        bg_generation_prompt="dark moody product photography background, deep charcoal gray to black gradient, subtle studio lighting from above, professional advertising aesthetic, no objects, no text, no products, cinematic dark",
    )


def _zone_to_dict(zone) -> dict | None:
    if zone is None:
        return None
    return {"name": zone.name, "x": zone.x, "y": zone.y, "w": zone.width, "h": zone.height}


def _save_json(path: Path, data: dict):
    import json
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
