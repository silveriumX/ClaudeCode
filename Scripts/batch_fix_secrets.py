"""
Batch fix hardcoded secrets in all Scripts/ and Projects/ Python files.
Replaces hardcoded passwords, IPs, and proxy credentials with os.getenv() calls.
Adds dotenv loading if missing.
"""
import os

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Replacements map: old_value -> (env_var_name, is_string)
PASSWORD_MAP = {
    "Taurus!2025": {
        # Host-based mapping: which env var to use depends on the host in the same file
        "195.177.94.189": ("VPS_LINUX_PASSWORD", "VPS_LINUX_HOST"),
        "45.12.72.147": ("VPS_FINANCE_PASSWORD", "VPS_FINANCE_HOST"),
        "169.40.135.130": ("VPS_VLESS_PASSWORD", "VPS_VLESS_HOST"),
        "_default": ("VPS_LINUX_PASSWORD", "VPS_LINUX_HOST"),
    },
    os.getenv("VPS_WIN_PASSWORD"): {
        "62.84.101.97": ("VPS_WIN_PASSWORD", "VPS_WIN_HOST"),
        "151.241.154.57": ("VPS_DOWNLOAD_PASSWORD", "VPS_DOWNLOAD_HOST"),
        "_default": ("VPS_WIN_PASSWORD", "VPS_WIN_HOST"),
    },
}

PROXY_REPLACEMENTS = {
    "{os.getenv("PROXY_USER")}": "PROXY_USER",
    "{os.getenv("PROXY_PASS")}": "PROXY_PASS",
    "{os.getenv("PROXY_HOST")}": "PROXY_HOST",
}


def get_depth(file_path: Path) -> int:
    """Get the number of parent directories to project root."""
    rel = file_path.relative_to(PROJECT_ROOT)
    return len(rel.parts) - 1


def detect_host(content: str) -> str:
    """Detect which VPS host is used in the file."""
    for host in ["195.177.94.189", "45.12.72.147", "169.40.135.130",
                 "62.84.101.97", "151.241.154.57"]:
        if host in content:
            return host
    return ""


def add_dotenv_imports(content: str, depth: int) -> str:
    """Add dotenv and os imports if missing."""
    has_dotenv = "load_dotenv" in content
    has_os = re.search(r"^import os\b|^from os ", content, re.MULTILINE)

    if has_dotenv and has_os:
        return content

    lines = content.split("\n")
    insert_pos = 0

    # Find position after shebang and docstrings
    i = 0
    if lines and lines[0].startswith("#!"):
        i = 1
    if i < len(lines) and lines[i].strip().startswith('"""'):
        # Multi-line docstring
        if lines[i].count('"""') >= 2:
            i += 1
        else:
            i += 1
            while i < len(lines) and '"""' not in lines[i]:
                i += 1
            i += 1
    elif i < len(lines) and lines[i].strip().startswith("'''"):
        if lines[i].count("'''") >= 2:
            i += 1
        else:
            i += 1
            while i < len(lines) and "'''" not in lines[i]:
                i += 1
            i += 1

    insert_pos = i

    # Build import block
    imports_to_add = []
    if not has_os:
        imports_to_add.append("import os")
    if not has_dotenv:
        imports_to_add.append("from pathlib import Path")
        imports_to_add.append("")
        imports_to_add.append("from dotenv import load_dotenv")
        imports_to_add.append("")
        imports_to_add.append(f"load_dotenv(Path(__file__).resolve().parents[{depth}] / \".env\")")
        imports_to_add.append("")

    if imports_to_add:
        for idx, imp in enumerate(imports_to_add):
            lines.insert(insert_pos + idx, imp)

    return "\n".join(lines)


def fix_python_file(file_path: Path) -> bool:
    """Fix hardcoded secrets in a single Python file."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    original = content
    depth = get_depth(file_path)
    host = detect_host(content)

    # 1. Replace passwords
    for password, host_map in PASSWORD_MAP.items():
        if password not in content:
            continue

        if host in host_map:
            pass_var, host_var = host_map[host]
        else:
            pass_var, host_var = host_map["_default"]

        # Pattern: VPS_PASSWORD = os.getenv("VPS_LINUX_PASSWORD") or password = os.getenv("VPS_LINUX_PASSWORD")
        content = re.sub(
            rf'''((?:VPS_)?(?:PASSWORD|PASS|password)\s*=\s*)['"]{re.escape(password)}['"]''',
            rf'\1os.getenv("{pass_var}")',
            content
        )
        # Pattern: password=os.getenv("VPS_LINUX_PASSWORD") in connect() calls
        content = re.sub(
            rf'''password=['"]{re.escape(password)}['"]''',
            f'password=os.getenv("{pass_var}")',
            content
        )

        # Replace associated host IP
        if host and host in host_map:
            # Pattern: host = os.getenv("VPS_LINUX_HOST")
            content = re.sub(
                rf'''((?:VPS_)?(?:HOST|host|SSH_HOST)\s*=\s*)['"]{re.escape(host)}['"]''',
                rf'\1os.getenv("{host_var}")',
                content
            )
            # Pattern: connect('195.177.94.189'
            content = re.sub(
                rf'''\.connect\(['"]{re.escape(host)}['"]''',
                f'.connect(os.getenv("{host_var}")',
                content
            )

    # 2. Replace proxy credentials
    for secret, env_var in PROXY_REPLACEMENTS.items():
        if secret in content:
            # In string assignments
            content = re.sub(
                rf'''([A-Z_]*\s*=\s*)['"]{re.escape(secret)}['"]''',
                rf'\1os.getenv("{env_var}")',
                content
            )
            # Inside f-strings or concatenated URLs
            content = content.replace(secret, f'{{os.getenv("{env_var}")}}')
            # Fix double-wrapped: os.getenv("X") that was already an f-string part
            # This handles edge cases in URL construction

    # 3. Add imports if anything changed
    if content != original:
        content = add_dotenv_imports(content, depth)
        file_path.write_text(content, encoding="utf-8")
        return True

    return False


def fix_bat_file(file_path: Path) -> bool:
    """Fix .bat files - replace with env var references."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    original = content

    # Add env loading at top if not present
    if "%VPS_PASSWORD%" not in content and "Taurus!2025" in content:
        content = content.replace(
            '"Taurus!2025"',
            '"%VPS_LINUX_PASSWORD%"'
        )

    if content != original:
        # Add note at top
        if not content.startswith("@REM"):
            content = "@REM NOTE: Set VPS_LINUX_PASSWORD env var before running\n" + content
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def fix_ps1_file(file_path: Path) -> bool:
    """Fix .ps1 files - replace with env var references."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    original = content

    # Load .env at top
    env_loader = '''# Load .env file
$envFile = Join-Path $PSScriptRoot "..\..\\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}
'''

    if "Taurus!2025" in content:
        content = content.replace('"Taurus!2025"', '$env:VPS_LINUX_PASSWORD')
        if "Load .env" not in content:
            content = env_loader + content

    if os.getenv("VPS_WIN_PASSWORD") in content:
        content = content.replace('os.getenv("VPS_WIN_PASSWORD")', '$env:VPS_WIN_PASSWORD')
        if "Load .env" not in content:
            content = env_loader + content

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    fixed = 0
    errors = 0

    # Find all Python files with secrets
    py_files = []
    for pattern in ["Scripts/**/*.py", "Projects/ServerManager/*.py"]:
        py_files.extend(PROJECT_ROOT.glob(pattern))

    for f in sorted(set(py_files)):
        try:
            if fix_python_file(f):
                rel = f.relative_to(PROJECT_ROOT)
                print(f"  + {rel}")
                fixed += 1
        except Exception as e:
            print(f"  ! {f.name}: {e}")
            errors += 1

    # Fix .bat files
    for f in PROJECT_ROOT.glob("Scripts/**/*.bat"):
        try:
            if fix_bat_file(f):
                print(f"  + {f.relative_to(PROJECT_ROOT)}")
                fixed += 1
        except Exception as e:
            print(f"  ! {f.name}: {e}")
            errors += 1

    # Fix .ps1 files
    for f in PROJECT_ROOT.glob("Scripts/**/*.ps1"):
        try:
            if fix_ps1_file(f):
                print(f"  + {f.relative_to(PROJECT_ROOT)}")
                fixed += 1
        except Exception as e:
            print(f"  ! {f.name}: {e}")
            errors += 1

    print(f"\nDone: {fixed} files fixed, {errors} errors")


if __name__ == "__main__":
    main()
