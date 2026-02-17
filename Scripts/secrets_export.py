"""
Secrets Export Tool
===================
Собирает ВСЕ секреты из workspace в один файл для переноса на другой ПК.

Использование:
    python Scripts/secrets_export.py

Результат:
    SECRETS_EXPORT.txt — один файл со всеми ключами, паролями, IP.
    Перенести через Google Drive / флешку, после импорта — УДАЛИТЬ.
"""

import base64
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = PROJECT_ROOT / "SECRETS_EXPORT.txt"


def find_env_files() -> list[Path]:
    """Найти все .env файлы в workspace."""
    env_files = sorted(
        p for p in PROJECT_ROOT.rglob(".env")
        if ".git" not in p.parts and "node_modules" not in p.parts and "venv" not in p.parts
    )
    return env_files


def find_credential_files() -> list[Path]:
    """Найти JSON credential файлы."""
    creds_dir = PROJECT_ROOT / ".credentials"
    if not creds_dir.exists():
        return []
    return sorted(creds_dir.glob("*.json"))


def export_secrets() -> None:
    """Экспортировать все секреты в один файл."""
    lines: list[str] = []

    # Header
    lines.append("=" * 70)
    lines.append("SECRETS EXPORT")
    lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Source: {PROJECT_ROOT}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("AFTER IMPORT — DELETE THIS FILE!")
    lines.append("")

    # === .env files ===
    env_files = find_env_files()
    lines.append(f"{'=' * 70}")
    lines.append(f"SECTION: ENV FILES ({len(env_files)} files)")
    lines.append(f"{'=' * 70}")
    lines.append("")

    for env_path in env_files:
        rel_path = env_path.relative_to(PROJECT_ROOT)
        content = env_path.read_text(encoding="utf-8", errors="replace")

        lines.append(f"--- FILE: {rel_path} ---")
        lines.append(content.rstrip())
        lines.append(f"--- END: {rel_path} ---")
        lines.append("")

        logger.info(f"  + {rel_path}")

    # === Credential JSON files ===
    cred_files = find_credential_files()
    if cred_files:
        lines.append(f"{'=' * 70}")
        lines.append(f"SECTION: CREDENTIAL JSON FILES ({len(cred_files)} files)")
        lines.append(f"{'=' * 70}")
        lines.append("")

        for cred_path in cred_files:
            rel_path = cred_path.relative_to(PROJECT_ROOT)
            content = cred_path.read_text(encoding="utf-8", errors="replace")

            lines.append(f"--- JSON: {rel_path} ---")
            lines.append(content.rstrip())
            lines.append(f"--- END: {rel_path} ---")
            lines.append("")

            logger.info(f"  + {rel_path} (JSON credential)")

    # === Claude MCP config ===
    mcp_path = PROJECT_ROOT / ".claude" / "mcp.json"
    if mcp_path.exists():
        lines.append(f"{'=' * 70}")
        lines.append("SECTION: CLAUDE MCP CONFIG")
        lines.append(f"{'=' * 70}")
        lines.append("")
        lines.append(f"--- JSON: .claude/mcp.json ---")
        lines.append(mcp_path.read_text(encoding="utf-8").rstrip())
        lines.append(f"--- END: .claude/mcp.json ---")
        lines.append("")
        logger.info("  + .claude/mcp.json")

    # === Summary ===
    lines.append(f"{'=' * 70}")
    lines.append("IMPORT INSTRUCTIONS")
    lines.append(f"{'=' * 70}")
    lines.append("")
    lines.append("On the new PC, run:")
    lines.append("  python Scripts/secrets_import.py SECRETS_EXPORT.txt")
    lines.append("")
    lines.append("Or tell Claude Code:")
    lines.append('  "Import secrets from SECRETS_EXPORT.txt"')
    lines.append("")
    lines.append("THEN DELETE SECRETS_EXPORT.txt FROM EVERYWHERE:")
    lines.append("  - Local disk")
    lines.append("  - Google Drive")
    lines.append("  - Recycle Bin")
    lines.append("")

    # Write
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    logger.info("")
    logger.info(f"Exported to: {OUTPUT_FILE}")
    logger.info(f"  {len(env_files)} .env files")
    logger.info(f"  {len(cred_files)} credential JSON files")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Upload SECRETS_EXPORT.txt to Google Drive")
    logger.info("  2. Download on new PC into project root")
    logger.info("  3. Run: python Scripts/secrets_import.py SECRETS_EXPORT.txt")
    logger.info("  4. DELETE SECRETS_EXPORT.txt everywhere!")


if __name__ == "__main__":
    export_secrets()
