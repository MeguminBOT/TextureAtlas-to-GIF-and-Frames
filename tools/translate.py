#!/usr/bin/env python3
"""Translation management script for TextureAtlas Toolbox."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

SCRIPT_DIR = Path(__file__).resolve().parent
TRANSLATOR_APP_SRC = SCRIPT_DIR / "translator-app" / "src"

if TRANSLATOR_APP_SRC.exists() and str(TRANSLATOR_APP_SRC) not in sys.path:
    sys.path.insert(0, str(TRANSLATOR_APP_SRC))

try:
    from language_registry import LANGUAGE_REGISTRY  # type: ignore
    from translation_tasks import (  # type: ignore
        LocalizationOperations,
        OperationResult,
        resolve_language_code,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - surfaced to user
    raise SystemExit(
        "Unable to import translation backend. Ensure tools/translator-app/src is available."
    ) from exc


def parse_languages(lang_args: List[str]) -> List[str]:
    """Validate language arguments against the registry."""

    if not lang_args:
        return list(LANGUAGE_REGISTRY.keys())

    resolved: List[str] = []
    for lang in lang_args:
        if lang.lower() == "all":
            return list(LANGUAGE_REGISTRY.keys())
        canonical = resolve_language_code(lang)
        if canonical:
            resolved.append(canonical)
        else:
            print(
                f"Warning: Unknown language '{lang}'. Available codes: {', '.join(LANGUAGE_REGISTRY.keys())}"
            )

    if not resolved:
        print("No valid languages specified. Defaulting to all languages.")
        return list(LANGUAGE_REGISTRY.keys())
    return resolved


def print_usage() -> None:
    """Display usage instructions."""

    print("Translation Management Tool for TextureAtlas Toolbox")
    print("=" * 50)
    print("Usage: python translate.py [command] [languages...]")
    print()
    print("Commands:")
    print("  extract    - Extract translatable strings from source code")
    print("  compile    - Compile .ts files to .qm files")
    print("  resource   - Create/update Qt resource file for translations")
    print("  status     - Show translation status")
    print("  disclaimer - Add machine translation disclaimers")
    print("  all        - Run extract, compile, resource, and status")
    print()
    print("Languages (optional):")
    for code, meta in LANGUAGE_REGISTRY.items():
        quality = meta.get("quality", "")
        indicator = " 🤖" if quality == "machine" else " ✋" if quality == "native" else ""
        english_name = meta.get("english_name", meta["name"])
        display = meta["name"] if english_name == meta["name"] else f"{meta['name']} ({english_name})"
        print(f"  {code:6} - {display}{indicator}")
    print("  all        - Process every language (default)")
    print()
    print("Examples:")
    print("  python translate.py extract")
    print("  python translate.py extract sv en")
    print("  python translate.py compile sv")
    print("  python translate.py resource")
    print("  python translate.py status es fr de")
    print("  python translate.py disclaimer es fr de")
    print("  python translate.py all sv")


def render_result(result: OperationResult) -> None:
    """Print logs and errors for a given operation."""

    header = result.name.upper()
    print(f"\n=== {header} ===")
    for line in result.logs:
        print(line)
    if result.errors:
        print("--- errors ---")
        for line in result.errors:
            print(line)
    print(f"Status: {'OK' if result.success else 'FAILED'}")


def render_status(result: OperationResult, translations_dir: Path) -> None:
    """Pretty print the status table using the operation details."""

    print(f"\n📁 Translation Status - {translations_dir}")
    print("=" * 60)
    entries = result.details.get("entries", [])
    for entry in entries:
        progress = entry.get("total_messages", 0)
        finished = entry.get("finished_messages", 0)
        percentage = f" ({finished}/{progress}, {finished / progress * 100:.0f}%)" if progress else ""
        quality = entry.get("quality")
        indicator = " 🤖" if quality == "machine" else " ✋" if quality == "native" else ""
        print(
            f"{entry['language'].upper():6} {entry['name']:<18} | .ts {'✅' if entry['ts_exists'] else '❌'} | .qm {'✅' if entry['qm_exists'] else '❌'}{percentage}{indicator}"
        )


def run_command(command: str, ops: LocalizationOperations, languages: List[str]) -> None:
    """Dispatch CLI command to backend operations."""

    if command == "extract":
        render_result(ops.extract(languages))
    elif command == "compile":
        render_result(ops.compile(languages))
    elif command == "resource":
        render_result(ops.create_resource_file())
    elif command == "status":
        status_result = ops.status_report(languages)
        render_status(status_result, ops.paths.translations_dir)
    elif command == "disclaimer":
        render_result(ops.inject_disclaimers(languages))
    elif command == "all":
        print("Running full translation update...")
        render_result(ops.extract(languages))
        render_result(ops.compile(languages))
        render_result(ops.create_resource_file())
        status_result = ops.status_report(languages)
        render_status(status_result, ops.paths.translations_dir)
    else:
        print(f"Invalid command: {command}")
        print("Valid commands: extract, compile, resource, status, disclaimer, all")
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    lang_args = sys.argv[2:] if len(sys.argv) > 2 else ["all"]
    languages = parse_languages(lang_args)

    print(f"Command: {command}")
    print(f"Languages: {', '.join(languages)}")

    ops = LocalizationOperations()
    run_command(command, ops, languages)


if __name__ == "__main__":
    main()
