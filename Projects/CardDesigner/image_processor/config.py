"""
Конфигурация Image Processor.
Все настройки, пороги, API ключи.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта (рядом с image_processor/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)


# --- API Keys ---
REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# --- Image Processing ---
MIN_RESOLUTION: int = 1500  # Минимальная сторона для пропуска апскейла
UPSCALE_FACTOR: int = 2  # Множитель апскейла по умолчанию
MAX_UPSCALE_FACTOR: int = 4

# --- Text Detection ---
TEXT_MASK_PADDING: int = 15  # Пиксели padding вокруг текстовых зон
TEXT_DETECTION_LANGUAGES: list[str] = ["ru", "en", "ch_sim"]
TEXT_CONFIDENCE_THRESHOLD: float = 0.3  # Минимальная уверенность OCR

# --- Enhancement ---
SHARPEN_RADIUS: int = 2
SHARPEN_PERCENT: int = 150
SHARPEN_THRESHOLD: int = 3
TEXT_SHARPEN_PERCENT: int = 50  # Мягкий шарпенинг для текстовых зон
SATURATION_BOOST: float = 1.08  # 8% boost
WHITE_BALANCE_AUTO: bool = True
DENOISE_STRENGTH: int = 3

# --- Normalizer ---
DEFAULT_PADDING_PERCENT: float = 0.10  # 10% padding от краёв
TARGET_MIN_SIZE: int = 2000  # Минимальный размер большей стороны

# --- Validator ---
VALIDATION_MODEL: str = "claude-sonnet-4-5-20250929"
VALIDATION_MIN_SCORE: int = 7  # Порог для предупреждения

# --- Paths ---
SUPPORTED_FORMATS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

# --- Replicate Models ---
REALESRGAN_MODEL: str = "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa"


def validate_config() -> list[str]:
    """Проверяет конфигурацию и возвращает список предупреждений."""
    warnings = []
    if not REPLICATE_API_TOKEN:
        warnings.append("REPLICATE_API_TOKEN не задан — AI-апскейл недоступен, будет использован Lanczos")
    if not ANTHROPIC_API_KEY:
        warnings.append("ANTHROPIC_API_KEY не задан — валидация через Claude Vision недоступна")
    return warnings
