# -*- coding: utf-8 -*-
"""Проверка: все файлы из Личное1 (кроме дубликатов) есть в Личное с тем же размером."""
from pathlib import Path

ROOT = Path(r"C:\Users\Admin\Documents\Cursor")
LICHNOE1 = ROOT / "Личное1"
LICHNOE = ROOT / "Личное"

# Не проверяем (дубликаты или служебные)
SKIP = {
    "README_ПЕРЕНЕСЕНО.md",  # мы добавили в Личное1
    "PERSONAL_OPS.md",       # дубликат ЛИЧНАЯ_ОПЕРАЦИОНКА
    "INDEX.md",              # в Личное другой INDEX (объединённый)
}
# Файл в Личное1 пустой, контент в Личное в другом месте (Notes/18.01...)
SKIP_REL = {"Психология_и_ментальное/18.01. ночные заметки о ночи.md"}

def relpath(p: Path, base: Path) -> str:
    return str(p.relative_to(base)).replace("\\", "/")

def main():
    errors = []
    for f in LICHNOE1.rglob("*"):
        if not f.is_file():
            continue
        rel = relpath(f, LICHNOE1)
        if f.name in SKIP:
            print(f"Skip (duplicate/service): {rel}")
            continue
        if rel in SKIP_REL:
            print(f"Skip (empty, content in Notes): {rel}")
            continue
        dest = LICHNOE / rel
        if not dest.exists():
            errors.append(f"MISSING: {rel}")
            continue
        if f.stat().st_size != dest.stat().st_size:
            errors.append(f"SIZE MISMATCH: {rel} (src={f.stat().st_size}, dst={dest.stat().st_size})")
            continue
        print(f"OK: {rel} ({f.stat().st_size} bytes)")
    if errors:
        print("\n--- ERRORS ---")
        for e in errors:
            print(e)
        return 1
    print("\n--- All files verified. No loss.")
    return 0

if __name__ == "__main__":
    exit(main())
