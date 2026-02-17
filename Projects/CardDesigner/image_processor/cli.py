"""
CLI интерфейс для Image Processor.
Запуск: python -m image_processor --input photo.jpg --output ./processed/
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import config
from .pipeline import ImageProcessorPipeline

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="CardDesigner Image Processor — обработка фото товаров",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python -m image_processor --input photo.jpg --output ./processed/
  python -m image_processor --input ./raw_photos/ --output ./processed/
  python -m image_processor --input photo.jpg --output ./out/ --no-upscale
  python -m image_processor --input ./photos/ --output ./out/ --upscale-factor 4
        """,
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Путь к файлу или папке с фото",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Папка для результатов",
    )
    parser.add_argument(
        "--no-upscale",
        action="store_true",
        help="Пропустить апскейл",
    )
    parser.add_argument(
        "--no-enhance",
        action="store_true",
        help="Пропустить улучшение качества",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Пропустить валидацию через Claude Vision",
    )
    parser.add_argument(
        "--upscale-factor",
        type=int,
        choices=[2, 4],
        default=2,
        help="Множитель апскейла (по умолчанию: 2)",
    )
    parser.add_argument(
        "--upscale-method",
        choices=["ai", "classical"],
        default="ai",
        help="Метод апскейла: ai (Real-ESRGAN) или classical (Lanczos)",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=None,
        help="Процент padding (0.0-0.5, по умолчанию: 0.10)",
    )
    parser.add_argument(
        "--no-intermediate",
        action="store_true",
        help="Не сохранять промежуточные файлы",
    )

    args = parser.parse_args()

    # --- Заголовок ---
    console.print("\n[bold cyan]" + "=" * 60 + "[/bold cyan]")
    console.print("[bold cyan]  CardDesigner Image Processor v0.1.0[/bold cyan]")
    console.print("[bold cyan]" + "=" * 60 + "[/bold cyan]\n")

    # --- Проверка конфигурации ---
    warnings = config.validate_config()
    for w in warnings:
        console.print(f"[yellow]\u26a0 {w}[/yellow]")

    # --- Определяем вход ---
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        console.print(f"[red]\u2717 Путь не существует: {input_path}[/red]")
        sys.exit(1)

    # --- Создаём пайплайн ---
    pipeline = ImageProcessorPipeline(
        upscale=not args.no_upscale,
        enhance=not args.no_enhance,
        validate=not args.no_validate,
        upscale_factor=args.upscale_factor,
        upscale_method=args.upscale_method,
        padding_percent=args.padding,
        save_intermediate=not args.no_intermediate,
    )

    # --- Запуск ---
    if input_path.is_file():
        if input_path.suffix.lower() not in config.SUPPORTED_FORMATS:
            console.print(f"[red]\u2717 Неподдерживаемый формат: {input_path.suffix}[/red]")
            sys.exit(1)
        results = [pipeline.process_single(input_path, output_path)]
    elif input_path.is_dir():
        results = pipeline.process_batch(input_path, output_path)
    else:
        console.print(f"[red]\u2717 Неизвестный тип пути: {input_path}[/red]")
        sys.exit(1)

    # --- Итоговая таблица ---
    console.print("\n")
    _print_summary(results)


def _print_summary(results: list) -> None:
    """Печатает итоговую таблицу результатов."""
    table = Table(title="Результаты обработки", show_lines=True)
    table.add_column("Файл", style="cyan")
    table.add_column("Статус", justify="center")
    table.add_column("Размер", justify="center")
    table.add_column("Текст", justify="center")
    table.add_column("Оценка", justify="center")
    table.add_column("Время", justify="right")

    success_count = 0
    for r in results:
        status = "[green]\u2713[/green]" if r.success else "[red]\u2717[/red]"
        size = f"{r.original_size[0]}x{r.original_size[1]} \u2192 {r.final_size[0]}x{r.final_size[1]}" if r.success else "-"
        text = f"{r.text_count} зон" if r.text_detected else "нет"

        if r.validation and r.validation.score > 0:
            score_color = "green" if r.validation.passed else "red"
            score = f"[{score_color}]{r.validation.score}/10[/{score_color}]"
        else:
            score = "-"

        elapsed = f"{r.elapsed_seconds:.1f}s"

        if r.error:
            status = f"[red]\u2717 {r.error[:30]}[/red]"

        table.add_row(r.input_path.name, status, size, text, score, elapsed)
        if r.success:
            success_count += 1

    console.print(table)
    console.print(f"\n[bold]Готово: {success_count}/{len(results)} фото обработано[/bold]")

    # Путь к результатам
    if results and results[0].output_path:
        console.print(f"[dim]Результаты: {results[0].output_path.parent}[/dim]\n")


if __name__ == "__main__":
    main()
