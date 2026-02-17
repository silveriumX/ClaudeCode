"""End-to-end тест Block 2: тёмная premium карточка SOLTHRA."""
import os, sys, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

for mod in list(sys.modules.keys()):
    if mod.startswith("design_composer"):
        del sys.modules[mod]

from pathlib import Path
from design_composer.models import CardSpec, TextContent, DesignStyle, Feature
from design_composer.pipeline import DesignComposerPipeline
from design_composer import config

print(f"Replicate: {config.REPLICATE_API_TOKEN[:10]}... ({len(config.REPLICATE_API_TOKEN)})")
print(f"Anthropic: {config.ANTHROPIC_API_KEY[:10]}... ({len(config.ANTHROPIC_API_KEY)})")

print("Waiting 15s for rate limit...")
time.sleep(15)

# Тёмный стиль в духе примеров пылесосов
custom_style = DesignStyle(
    color_palette=["#0a0a0a", "#2D8B5E", "#ffffff"],
    background_mood="dark premium studio",
    bg_generation_prompt="dark moody product photography background, deep charcoal gray to black gradient, subtle studio lighting from above, soft light rays, very dark, professional advertising aesthetic, no objects, no text, no products, cinematic dark",
)

spec = CardSpec(
    product_image_path=Path("test_output/solthra_final.png"),
    marketplace="wb",
    text=TextContent(
        title="BERBERINE\nCOMPLEX",
        subtitle="поддержка метаболизма • контроль холестерина",
        features=[
            Feature(number="500", unit="мг", label="берберина\nв капсуле"),
            Feature(number="90", unit="шт", label="капсул\nв упаковке"),
            Feature(number="100%", unit="", label="натуральный\nсостав"),
            Feature(number="GMP", unit="", label="сертифицированное\nпроизводство"),
        ],
        badge_text="PREMIUM",
    ),
    style_override=custom_style,
)

pipeline = DesignComposerPipeline(
    analyze_style=False,
    generate_bg=True,
    validate=False,
    bg_method="flux",
    save_intermediate=True,
)

output_dir = Path("cards_output")
print(f"\nStarting compose at {time.strftime('%H:%M:%S')}")
result = pipeline.compose_single(spec, output_dir)

print(f"\n{'='*60}")
print(f"RESULT:")
print(f"  Success: {result.success}")
print(f"  Time: {result.elapsed_seconds:.1f}s")
print(f"  Steps: {result.steps_completed}")
if result.output_png_path:
    print(f"  PNG: {result.output_png_path}")
if result.output_jpg_path:
    print(f"  JPG: {result.output_jpg_path}")
if result.error:
    print(f"  Error: {result.error}")
