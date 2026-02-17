"""
Secrets Import Tool
====================
Читает SECRETS_EXPORT.txt и раскладывает секреты по проектам.

Использование:
    python Scripts/secrets_import.py SECRETS_EXPORT.txt

Что делает:
    1. Парсит SECRETS_EXPORT.txt
    2. Создаёт .env файлы в каждом проекте
    3. Создаёт .credentials/ с JSON файлами
    4. Создаёт .claude/mcp.json

После импорта — УДАЛИТЬ SECRETS_EXPORT.txt!
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def parse_export_file(export_path: Path) -> dict[str, str]:
    """
    Парсить SECRETS_EXPORT.txt.

    Returns:
        dict: {relative_path: content}
    """
    content = export_path.read_text(encoding="utf-8")
    files: dict[str, str] = {}

    current_file = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        # Detect file start: "--- FILE: path ---" or "--- JSON: path ---"
        if line.startswith("--- FILE: ") and line.endswith(" ---"):
            current_file = line[len("--- FILE: "):-len(" ---")]
            current_lines = []
        elif line.startswith("--- JSON: ") and line.endswith(" ---"):
            current_file = line[len("--- JSON: "):-len(" ---")]
            current_lines = []
        elif line.startswith("--- END: ") and line.endswith(" ---"):
            if current_file:
                files[current_file] = "\n".join(current_lines)
                current_file = None
                current_lines = []
        elif current_file is not None:
            current_lines.append(line)

    return files


def import_secrets(export_path: Path) -> None:
    """Импортировать секреты из файла."""
    if not export_path.exists():
        logger.error(f"File not found: {export_path}")
        sys.exit(1)

    files = parse_export_file(export_path)

    if not files:
        logger.error("No secrets found in export file!")
        sys.exit(1)

    logger.info(f"Found {len(files)} files to import:")
    logger.info("")

    created = 0
    skipped = 0

    for rel_path, content in sorted(files.items()):
        target = PROJECT_ROOT / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            existing = target.read_text(encoding="utf-8", errors="replace")
            if existing.strip() == content.strip():
                logger.info(f"  = {rel_path} (already exists, identical)")
                skipped += 1
                continue
            else:
                # Backup existing
                backup = target.with_suffix(target.suffix + ".backup")
                backup.write_text(existing, encoding="utf-8")
                logger.info(f"  ! {rel_path} (exists, backed up to {backup.name})")

        target.write_text(content + "\n", encoding="utf-8")
        logger.info(f"  + {rel_path}")
        created += 1

    logger.info("")
    logger.info(f"Done: {created} created, {skipped} skipped")
    logger.info("")
    logger.info("NOW DELETE SECRETS_EXPORT.txt:")
    logger.info(f"  del \"{export_path}\"")
    logger.info("  Also delete from Google Drive and Recycle Bin!")


def main() -> None:
    if len(sys.argv) < 2:
        # Default path
        default = PROJECT_ROOT / "SECRETS_EXPORT.txt"
        if default.exists():
            export_path = default
        else:
            logger.error("Usage: python Scripts/secrets_import.py <SECRETS_EXPORT.txt>")
            sys.exit(1)
    else:
        export_path = Path(sys.argv[1])
        if not export_path.is_absolute():
            export_path = PROJECT_ROOT / export_path

    import_secrets(export_path)


if __name__ == "__main__":
    main()
