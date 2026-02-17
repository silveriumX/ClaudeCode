"""Позволяет запускать: python -m image_processor"""
import os
import sys

# Fix Windows console encoding for Unicode symbols
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .cli import main

main()
