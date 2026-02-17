"""Quick test: re-uses cached Flux background, only re-renders template."""
import os, sys, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

for mod in list(sys.modules.keys()):
    if mod.startswith("design_composer"):
        del sys.modules[mod]

from pathlib import Path
from PIL import Image
from design_composer.models import CardSpec, TextContent, DesignStyle, Feature, CardLayout, CardResult
from design_composer.layout_engine import compute_layout
from design_composer.template_renderer import render_card_sync
from design_composer import config

# Re-use cached Flux background
bg_path = Path("cards_output/intermediate/solthra_final_02_background.png")
if not bg_path.exists():
    print(f"ERROR: cached background not found at {bg_path}")
    sys.exit(1)

background = Image.open(bg_path)
print(f"Background: {background.size} from cache")

# Product
product_path = Path("test_output/solthra_final.png")
product_image = Image.open(product_path).convert("RGBA")
print(f"Product: {product_image.size}")

# Style
custom_style = DesignStyle(
    color_palette=["#0a0a0a", "#2D8B5E", "#ffffff"],
    background_mood="dark premium studio",
)

# Text
text = TextContent(
    title="BERBERINE\nCOMPLEX",
    subtitle="поддержка метаболизма • контроль холестерина",
    features=[
        Feature(number="500", unit="мг", label="берберина\nв капсуле"),
        Feature(number="90", unit="шт", label="капсул\nв упаковке"),
        Feature(number="100%", unit="", label="натуральный\nсостав"),
        Feature(number="GMP", unit="", label="сертифицированное\nпроизводство"),
    ],
    badge_text="PREMIUM",
)

# Layout
card_w, card_h = 900, 1200
layout = compute_layout(card_w, card_h, product_image, text, layout_type="center")

# Render
output_path = Path("cards_output/solthra_final_card_wb.png")
print(f"\nRendering...")
start = time.time()

render_card_sync(
    background=background,
    product_image=product_image,
    text=text,
    layout=layout,
    style=custom_style,
    output_path=output_path,
    template_name="base",
)

elapsed = time.time() - start
print(f"\nDone in {elapsed:.1f}s")
print(f"Output: {output_path}")

# Also save JPG
jpg_path = output_path.with_suffix(".jpg")
card_img = Image.open(output_path).convert("RGB")
card_img.save(jpg_path, format="JPEG", quality=95)
print(f"JPG: {jpg_path}")
