"""
Основной пайплайн обработки изображений.
Оркестрирует все шаги: удаление фона -> детекция текста -> апскейл -> улучшение -> нормализация -> валидация.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from . import config
from .background_remover import remove_background
from .text_detector import detect_text_regions, TextDetectionResult
from .upscaler import needs_upscale, upscale_image
from .enhancer import enhance_image
from .normalizer import normalize_image
from .validator import validate_result, ValidationResult


@dataclass
class ProcessingResult:
    """Результат обработки одного изображения."""
    input_path: Path
    output_path: Path | None = None
    success: bool = False
    elapsed_seconds: float = 0.0
    original_size: tuple[int, int] = (0, 0)
    final_size: tuple[int, int] = (0, 0)
    text_detected: bool = False
    text_count: int = 0
    validation: ValidationResult | None = None
    error: str | None = None
    steps_completed: list[str] = field(default_factory=list)


class ImageProcessorPipeline:
    """Пайплайн обработки фото товаров."""

    def __init__(
        self,
        upscale: bool = True,
        enhance: bool = True,
        validate: bool = True,
        upscale_factor: int = 2,
        upscale_method: str = "ai",
        padding_percent: float | None = None,
        save_intermediate: bool = True,
    ):
        self.upscale = upscale
        self.enhance = enhance
        self.validate = validate
        self.upscale_factor = upscale_factor
        self.upscale_method = upscale_method
        self.padding_percent = padding_percent
        self.save_intermediate = save_intermediate

    def process_single(self, image_path: Path, output_dir: Path) -> ProcessingResult:
        """Обрабатывает одно изображение через весь пайплайн."""
        result = ProcessingResult(input_path=image_path)
        start_time = time.time()

        output_dir.mkdir(parents=True, exist_ok=True)
        intermediate_dir = output_dir / "intermediate"
        if self.save_intermediate:
            intermediate_dir.mkdir(parents=True, exist_ok=True)

        stem = image_path.stem

        try:
            print(f"\n{'='*60}")
            print(f"Processing: {image_path.name}")
            print(f"{'='*60}")

            original = Image.open(image_path)
            result.original_size = original.size
            print(f"  Size: {original.size[0]}x{original.size[1]}, mode: {original.mode}")

            # --- Step 1: Background removal ---
            print("\nStep 1/6: Background removal")
            no_bg = remove_background(original)
            result.steps_completed.append("background_removal")
            if self.save_intermediate:
                no_bg.save(intermediate_dir / f"{stem}_01_no_bg.png")

            # --- Step 2: Text detection ---
            print("\nStep 2/6: Text detection")
            text_result: TextDetectionResult = detect_text_regions(no_bg)
            result.text_detected = text_result.has_text
            result.text_count = text_result.count
            result.steps_completed.append("text_detection")
            if self.save_intermediate and text_result.text_mask is not None:
                text_result.text_mask.save(intermediate_dir / f"{stem}_02_text_mask.png")

            # --- Step 3: Upscale ---
            current = no_bg
            if self.upscale and needs_upscale(current):
                print(f"\nStep 3/6: Upscale ({self.upscale_method}, {self.upscale_factor}x)")
                current = upscale_image(current, method=self.upscale_method, factor=self.upscale_factor)
                if text_result.text_mask is not None:
                    text_result.text_mask = text_result.text_mask.resize(current.size, Image.LANCZOS)
                result.steps_completed.append("upscale")
                if self.save_intermediate:
                    current.save(intermediate_dir / f"{stem}_03_upscaled.png")
            else:
                print("\nStep 3/6: Upscale (skipped)")

            # --- Step 4: Enhancement ---
            if self.enhance:
                print("\nStep 4/6: Quality enhancement")
                current = enhance_image(current, text_result.text_mask)
                result.steps_completed.append("enhancement")
                if self.save_intermediate:
                    current.save(intermediate_dir / f"{stem}_04_enhanced.png")
            else:
                print("\nStep 4/6: Enhancement (skipped)")

            # --- Step 5: Normalization ---
            print("\nStep 5/6: Normalization")
            current = normalize_image(current, padding_percent=self.padding_percent)
            result.steps_completed.append("normalization")
            if self.save_intermediate:
                current.save(intermediate_dir / f"{stem}_05_normalized.png")

            # --- Step 6: Validation ---
            if self.validate:
                print("\nStep 6/6: Validation (Claude Vision)")
                validation = validate_result(original, current)
                result.validation = validation
                result.steps_completed.append("validation")
            else:
                print("\nStep 6/6: Validation (skipped)")

            # --- Save final ---
            output_path = output_dir / f"{stem}_final.png"
            current.save(output_path, format="PNG", optimize=True)
            result.output_path = output_path
            result.final_size = current.size
            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False
            print(f"\n  ERROR: {e}")
            import traceback
            traceback.print_exc()

        result.elapsed_seconds = time.time() - start_time
        return result

    def process_batch(self, input_dir: Path, output_dir: Path) -> list[ProcessingResult]:
        """Обрабатывает все изображения в папке."""
        files = sorted([f for f in input_dir.iterdir() if f.suffix.lower() in config.SUPPORTED_FORMATS])

        if not files:
            print(f"No images found in {input_dir}")
            return []

        print(f"\nFound {len(files)} images to process\n")

        results = []
        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}]")
            result = self.process_single(file_path, output_dir)
            results.append(result)

        return results
