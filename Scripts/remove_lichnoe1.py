# -*- coding: utf-8 -*-
"""Удаление папки Личное1 после проверки переноса в Личное."""
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\Admin\Documents\Cursor")
LICHNOE1 = ROOT / "Личное1"

def main():
    if not LICHNOE1.exists():
        print("Личное1 уже удалена.")
        return 0
    print(f"Удаляю {LICHNOE1}...")
    shutil.rmtree(LICHNOE1)
    print("Готово. Личное1 удалена.")
    return 0

if __name__ == "__main__":
    main()
