"""CLI интерфейс Design Composer."""

import argparse
from pathlib import Path

from .models import CardSpec, TextContent
from .pipeline import DesignComposerPipeline


def main():
    parser = argparse.ArgumentParser(
        description="CardDesigner Design Composer — создание карточек для маркетплейсов"
    )
    parser.add_argument("-i", "--input", required=True, help="Путь к обработанному фото (Block 1 output)")
    parser.add_argument("-o", "--output", required=True, help="Папка для результатов")
    parser.add_argument("-m", "--marketplace", default="wb", choices=["wb", "ozon"], help="Маркетплейс (default: wb)")
    parser.add_argument("--title", default="", help="Заголовок карточки")
    parser.add_argument("--subtitle", default="", help="Подзаголовок")
    parser.add_argument("--bullets", nargs="+", default=[], help="Пункты преимуществ")
    parser.add_argument("--price", default="", help="Цена (напр. '1 290 руб.')")
    parser.add_argument("--badge", default="", help="Бейдж (напр. 'ХИТ', 'НОВИНКА')")
    parser.add_argument("--reference", default=None, help="Референс дизайна для анализа стиля")
    parser.add_argument("--bg-method", default="flux", choices=["flux", "recraft", "gradient"], help="Метод генерации фона")
    parser.add_argument("--no-validate", action="store_true", help="Пропустить валидацию")
    parser.add_argument("--no-intermediate", action="store_true", help="Не сохранять промежуточные файлы")

    args = parser.parse_args()

    text = TextContent(
        title=args.title,
        subtitle=args.subtitle,
        bullets=args.bullets,
        price=args.price,
        badge_text=args.badge,
    )

    spec = CardSpec(
        product_image_path=Path(args.input),
        marketplace=args.marketplace,
        text=text,
        reference_image_path=Path(args.reference) if args.reference else None,
    )

    pipeline = DesignComposerPipeline(
        analyze_style=bool(args.reference),
        generate_bg=True,
        validate=not args.no_validate,
        bg_method=args.bg_method,
        save_intermediate=not args.no_intermediate,
    )

    result = pipeline.compose_single(spec, Path(args.output))

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
