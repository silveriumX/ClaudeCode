"""Позволяет запускать: python -m design_composer"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from .cli import main
main()
