"""
Рендеринг карточки: HTML + Playwright → PNG.
Стиль: тёмный premium, крупный продукт, инфографика-характеристики.
"""

import asyncio
import base64
import io
import time
from pathlib import Path

from PIL import Image
from jinja2 import Environment, FileSystemLoader

from . import config
from .models import TextContent, DesignStyle, CardLayout


def render_card_sync(
    background: Image.Image,
    product_image: Image.Image,
    text: TextContent,
    layout: CardLayout,
    style: DesignStyle,
    output_path: Path,
    template_name: str = "base",
) -> Path:
    """Синхронная обёртка для рендера карточки."""
    return asyncio.run(_render_card(
        background, product_image, text, layout, style, output_path, template_name
    ))


async def _render_card(
    background: Image.Image,
    product_image: Image.Image,
    text: TextContent,
    layout: CardLayout,
    style: DesignStyle,
    output_path: Path,
    template_name: str = "base",
) -> Path:
    """Рендерит карточку через Playwright."""
    print(f"  Rendering card via Playwright...")
    start = time.time()

    cw = layout.card_width
    ch = layout.card_height
    scale = cw / 900  # Масштаб от базового WB

    # --- Data URI ---
    bg_uri = _image_to_data_uri(background, "JPEG")
    product_uri = _image_to_data_uri(product_image, "PNG")

    # --- Цвета ---
    palette = style.color_palette if style.color_palette else ["#1a1a2e", "#e17055", "#ffffff"]
    accent = palette[1] if len(palette) > 1 else "#e17055"

    # --- Адаптивные размеры ---
    pad = int(35 * scale)

    # === TITLE ===
    main_title_fs = int(74 * scale)     # ОГРОМНЫЙ
    sub_title_fs = int(14 * scale)
    sub_title_mt = int(8 * scale)

    # === FEATURES BAR (bottom) ===
    feature_num_fs = int(52 * scale)    # Крупные цифры — ЕЩЁ БОЛЬШЕ
    feature_unit_fs = int(30 * scale)   # Единицы
    feature_label_fs = int(12 * scale)  # Подпись
    features_bar_py = int(35 * scale)   # Vertical padding
    features_bar_px = int(12 * scale)   # Horizontal padding
    features_bar_h = int(170 * scale)   # Approx height for watermark positioning

    # === BADGE ===
    badge_fs = int(13 * scale)
    badge_top = int(pad * 0.5)

    # === WATERMARK ===
    watermark_fs = int(100 * scale)

    # === PRODUCT — LARGE, center ===
    product_w = int(cw * 0.65)
    product_max_h = int(ch * 0.58)
    product_top_pct = 44  # Above center (leave room for features bar bottom)

    # Title top
    title_top = int(pad * 0.5)

    # Features data
    features_data = []
    for f in text.features:
        features_data.append({
            "number": f.number,
            "unit": f.unit,
            "label": f.label,
        })

    # --- Jinja2 ---
    env = Environment(loader=FileSystemLoader(str(config.TEMPLATES_DIR)))
    template = env.get_template(f"{template_name}.html")

    html = template.render(
        card_width=cw,
        card_height=ch,
        background_data_uri=bg_uri,
        product_data_uri=product_uri,
        # Sizing
        pad=pad,
        product_w=product_w,
        product_max_h=product_max_h,
        product_top_pct=product_top_pct,
        # Title
        main_title=text.title,
        sub_title=text.subtitle,
        title_top=title_top,
        main_title_fs=main_title_fs,
        sub_title_fs=sub_title_fs,
        sub_title_mt=sub_title_mt,
        # Features bar
        features=features_data,
        feature_num_fs=feature_num_fs,
        feature_unit_fs=feature_unit_fs,
        feature_label_fs=feature_label_fs,
        features_bar_py=features_bar_py,
        features_bar_px=features_bar_px,
        features_bar_h=features_bar_h,
        # Colors
        accent_color=accent,
        # Badge
        badge_text=text.badge_text,
        badge_fs=badge_fs,
        badge_top=badge_top,
        # Watermark
        watermark_text=text.title.split("\n")[0] if text.title else "",
        watermark_fs=watermark_fs,
    )

    # --- Playwright ---
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": cw, "height": ch},
            device_scale_factor=config.SCREENSHOT_SCALE,
        )

        await page.set_content(html, wait_until="commit", timeout=60000)
        # Wait for fonts to load, then extra time for rendering
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # If fonts don't load, continue with fallback
        await page.wait_for_timeout(2000)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(output_path), full_page=False, type="png")
        await browser.close()

    # Resize if needed
    rendered = Image.open(output_path)
    if rendered.size != (cw, ch):
        rendered = rendered.resize((cw, ch), Image.LANCZOS)
        rendered.save(output_path, format="PNG")

    elapsed = time.time() - start
    print(f"  OK: Card rendered ({elapsed:.1f}s, {cw}x{ch})")
    return output_path


def _image_to_data_uri(image: Image.Image, fmt: str = "PNG") -> str:
    """Конвертирует PIL Image в base64 data URI."""
    buf = io.BytesIO()
    if fmt.upper() == "JPEG" and image.mode == "RGBA":
        rgb = Image.new("RGB", image.size, (255, 255, 255))
        rgb.paste(image, mask=image.getchannel("A"))
        rgb.save(buf, format="JPEG", quality=90)
    else:
        image.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if fmt.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"
