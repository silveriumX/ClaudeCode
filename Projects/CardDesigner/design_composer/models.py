"""
Модели данных Design Composer.
Все dataclass'ы для передачи данных между модулями.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Feature:
    """Характеристика товара для инфографики: крупная цифра + единица + подпись."""
    number: str       # "3 600"
    unit: str = ""    # "Вт", "Па", "мин"
    label: str = ""   # "мощность", "без подзарядки"


@dataclass
class TextContent:
    """Текст для карточки (задаётся пользователем)."""
    title: str = ""
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)  # Инфографика-характеристики
    price: str = ""              # "1 290 ₽"
    badge_text: str = ""         # "ХИТ", "НОВИНКА", "-30%"


@dataclass
class DesignStyle:
    """Стиль дизайна (из анализа референса или дефолтный)."""
    color_palette: list[str] = field(default_factory=list)  # hex: ["#1a1a2e", "#e94560"]
    background_mood: str = ""     # "minimalist gradient", "nature bokeh", "clean white"
    typography_style: str = ""    # "bold sans-serif", "elegant serif"
    layout_type: str = "center"   # "center", "left-product", "full-bleed"
    bg_generation_prompt: str = "" # Промпт для Flux
    raw_analysis: str = ""


@dataclass
class LayoutZone:
    """Позиция одного элемента на карточке."""
    name: str      # "product", "title", "subtitle", "bullets", "price", "badge"
    x: int
    y: int
    width: int
    height: int
    z_index: int = 0


@dataclass
class CardLayout:
    """Полная раскладка карточки."""
    card_width: int
    card_height: int
    product_zone: LayoutZone | None = None
    title_zone: LayoutZone | None = None
    subtitle_zone: LayoutZone | None = None
    bullets_zone: LayoutZone | None = None
    price_zone: LayoutZone | None = None
    badge_zone: LayoutZone | None = None
    product_scale: float = 1.0


@dataclass
class CardSpec:
    """Полная спецификация для создания одной карточки."""
    product_image_path: Path
    marketplace: str = "wb"       # "wb" или "ozon"
    text: TextContent = field(default_factory=TextContent)
    reference_image_path: Path | None = None
    style_override: DesignStyle | None = None
    template_name: str = "base"


@dataclass
class CardResult:
    """Результат создания одной карточки."""
    spec: CardSpec | None = None
    output_png_path: Path | None = None
    output_jpg_path: Path | None = None
    success: bool = False
    elapsed_seconds: float = 0.0
    steps_completed: list[str] = field(default_factory=list)
    style: DesignStyle | None = None
    layout: CardLayout | None = None
    background_path: Path | None = None
    validation_score: int = 0
    validation_issues: list[str] = field(default_factory=list)
    error: str | None = None
