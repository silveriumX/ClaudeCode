"""
Конфигурация Design Composer (Block 2).
Размеры карточек, модели, шрифты, пороги.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

# --- API Keys (общие с Block 1) ---
REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# --- Размеры карточек ---
CARD_SIZES: dict[str, tuple[int, int]] = {
    "wb": (900, 1200),      # Wildberries: 3:4
    "ozon": (1200, 1600),   # Ozon: 3:4
}

# --- Генерация фона ---
FLUX_MODEL: str = "black-forest-labs/flux-1.1-pro"
FLUX_FALLBACK_MODEL: str = "black-forest-labs/flux-dev"
RECRAFT_MODEL: str = "recraft-ai/recraft-v3"

# --- Layout ---
PRODUCT_MAX_HEIGHT_PCT: float = 0.85   # Продукт занимает макс 85% доступной высоты
PRODUCT_MAX_WIDTH_PCT: float = 0.58    # Продукт занимает макс 58% ширины (место для текста сбоку)
PRODUCT_VERTICAL_CENTER_PCT: float = 0.50  # Центр продукта — 50% от верха
TEXT_ZONE_PADDING_PX: int = 20

# --- Типографика ---
DEFAULT_FONT_FAMILY: str = "Montserrat"
FALLBACK_FONTS: list[str] = ["Inter", "Roboto", "Open Sans", "Arial"]
TITLE_FONT_SIZE_PX: int = 28
SUBTITLE_FONT_SIZE_PX: int = 18
BULLET_FONT_SIZE_PX: int = 18
PRICE_FONT_SIZE_PX: int = 32

# --- Рендер ---
PLAYWRIGHT_TIMEOUT_MS: int = 30000
SCREENSHOT_SCALE: int = 2  # Device scale factor

# --- Claude Vision ---
STYLE_ANALYSIS_MODEL: str = "claude-sonnet-4-5-20250929"
CARD_VALIDATION_MODEL: str = "claude-sonnet-4-5-20250929"
CARD_VALIDATION_MIN_SCORE: int = 7

# --- Выходные форматы ---
OUTPUT_FORMAT_PNG: bool = True
OUTPUT_FORMAT_JPG: bool = True
JPG_QUALITY: int = 95

# --- Пути ---
TEMPLATES_DIR: Path = Path(__file__).resolve().parent / "templates"


def validate_config() -> list[str]:
    """Проверяет конфигурацию и возвращает список предупреждений."""
    warnings = []
    if not REPLICATE_API_TOKEN:
        warnings.append("REPLICATE_API_TOKEN не задан — генерация фона недоступна")
    if not ANTHROPIC_API_KEY:
        warnings.append("ANTHROPIC_API_KEY не задан — анализ стиля и валидация недоступны")
    try:
        import playwright
    except ImportError:
        warnings.append("playwright не установлен — рендеринг карточек невозможен")
    return warnings
