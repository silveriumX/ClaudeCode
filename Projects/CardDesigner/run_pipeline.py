"""Run pipeline on all SOLTHRA photos."""
import os, sys, time

# Setup
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Clear cached modules
for mod in list(sys.modules.keys()):
    if mod.startswith("image_processor"):
        del sys.modules[mod]

from pathlib import Path
from image_processor.pipeline import ImageProcessorPipeline
from image_processor import config

print(f"Replicate token: {config.REPLICATE_API_TOKEN[:10]}... ({len(config.REPLICATE_API_TOKEN)} chars)")
print(f"Anthropic key: {config.ANTHROPIC_API_KEY[:10]}... ({len(config.ANTHROPIC_API_KEY)} chars)")

# Wait for rate limit
print("Waiting 15s for Replicate rate limit reset...")
time.sleep(15)

pipeline = ImageProcessorPipeline(
    upscale=False,
    enhance=True,
    validate=False,
    save_intermediate=True,
)

input_dir = Path("test_input")
output_dir = Path("test_output")

print(f"\nStarting batch at {time.strftime('%H:%M:%S')}")
results = pipeline.process_batch(input_dir, output_dir)

# Summary
print(f"\n{'='*60}")
print(f"BATCH COMPLETE: {sum(1 for r in results if r.success)}/{len(results)} successful")
for r in results:
    status = "OK" if r.success else "FAIL"
    text = f"text:{r.text_count}" if r.text_detected else "no text"
    print(f"  [{status}] {r.input_path.name}: {r.original_size} -> {r.final_size} ({text}, {r.elapsed_seconds:.1f}s)")
    if r.error:
        print(f"         Error: {r.error}")
total_time = sum(r.elapsed_seconds for r in results)
print(f"\nTotal time: {total_time:.0f}s")
