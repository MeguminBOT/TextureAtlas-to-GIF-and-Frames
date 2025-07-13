#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translation tools for TextureAtlas Toolbox.

This tool script helps with generating, updating, and compiling translation files.
Command-line tool for managing Qt translation files (.ts/.qm).
"""

import sys
import subprocess
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_source_files():
    """Get all Python source files that may contain translatable strings."""
    project_root = get_project_root()
    source_dirs = [
        project_root / "src",
    ]

    source_files = []
    excluded_files = {
        "__init__.py",
        "__pycache__",
    }

    print("Scanning for Python source files...")
    for source_dir in source_dirs:
        if source_dir.exists():
            # Find all .py files recursively
            py_files = list(source_dir.rglob("*.py"))

            # Filter out excluded files
            filtered_files = []
            for py_file in py_files:
                # Skip __pycache__ directories and __init__.py files
                if any(excluded in str(py_file) for excluded in excluded_files):
                    continue

                # Skip files that are too small (likely empty or just imports)
                try:
                    if py_file.stat().st_size < 100:  # Less than 100 bytes
                        continue
                except Exception:
                    continue

                filtered_files.append(py_file)

            print(f"  Found {len(filtered_files)} Python files in {source_dir}")
            source_files.extend(filtered_files)

    print(f"Total Python files to scan: {len(source_files)}")

    # Print some of the files being processed for debugging
    if source_files:
        print("Sample files:")
        for i, file in enumerate(source_files[:10]):  # Show first 10 files
            print(f"  {file.relative_to(project_root)}")
        if len(source_files) > 10:
            print(f"  ... and {len(source_files) - 10} more files")

    return source_files


def find_qt_tools(qt_dir=None):
    """Find Qt tools (lupdate, lrelease) in the Qt installation."""
    qt_paths = []

    # User-specified Qt directory
    if qt_dir:
        qt_paths.append(Path(qt_dir))

    # Common Qt installation paths
    qt_paths.extend(
        [
            Path("R:/DevelopmentStuff/QT"),  # AutisticLulus path to QT lol
            Path("C:/Qt"),
            Path("D:/Qt"),
            Path("E:/Qt"),
            Path("C:/Program Files/Qt"),
            Path("D:/Program Files/Qt"),
            Path("E:/Program Files/Qt"),
            Path("C:/Program Files (x86)/Qt"),
            Path("D:/Program Files (x86)/Qt"),
            Path("E:/Program Files (x86)/Qt"),
        ]
    )

    for qt_path in qt_paths:
        if not qt_path.exists():
            continue

        # Look for Qt versions and tools
        for version_dir in qt_path.glob("*"):
            if not version_dir.is_dir():
                continue

            # Look for bin directories in different configurations
            bin_paths = [
                version_dir / "bin",
                version_dir / "msvc2019_64" / "bin",
                version_dir / "msvc2022_64" / "bin",
                version_dir / "mingw_64" / "bin",
                version_dir / "gcc_64" / "bin",
            ]

            for bin_path in bin_paths:
                if bin_path.exists():
                    lupdate_exe = bin_path / "lupdate.exe"
                    lrelease_exe = bin_path / "lrelease.exe"

                    if lupdate_exe.exists() and lrelease_exe.exists():
                        return str(lupdate_exe), str(lrelease_exe)

    return None, None


def check_lupdate(qt_dir=None):
    """Check if lupdate tool is available."""
    # First try system PATH
    try:
        subprocess.run(["lupdate", "-version"], capture_output=True, check=True)
        return True, "lupdate"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try to find Qt tools
    lupdate_path, _ = find_qt_tools(qt_dir)
    if lupdate_path:
        try:
            subprocess.run([lupdate_path, "-version"], capture_output=True, check=True)
            return True, lupdate_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return False, None


def check_lrelease(qt_dir=None):
    """Check if lrelease tool is available."""
    # First try system PATH
    try:
        subprocess.run(["lrelease", "-version"], capture_output=True, check=True)
        return True, "lrelease"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try to find Qt tools
    _, lrelease_path = find_qt_tools(qt_dir)
    if lrelease_path:
        try:
            subprocess.run([lrelease_path, "-version"], capture_output=True, check=True)
            return True, lrelease_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return False, None


def update_translations(qt_dir=None):
    """Update translation files using lupdate."""
    available, lupdate_cmd = check_lupdate(qt_dir)
    if not available:
        print("Error: lupdate tool not found.")
        print("Please install Qt development tools:")
        print("  - On Windows: Install Qt from https://www.qt.io/download-qt-installer")
        print("  - On Ubuntu/Debian: sudo apt install qttools5-dev-tools")
        print("  - On macOS: brew install qt5")
        print("Or specify Qt directory with --qt-dir option")
        return False

    print(f"Using lupdate: {lupdate_cmd}")

    project_root = get_project_root()
    translations_dir = project_root / "src" / "translations"
    translations_dir.mkdir(exist_ok=True)

    # Get source files
    source_files = get_source_files()
    if not source_files:
        print("No source files found.")
        return False

    # Create a temporary .pro file for lupdate
    pro_content = f"""
# Automatically generated project file for translation extraction
# Source files to scan for translatable strings
SOURCES = {" \\\n          ".join(str(f) for f in source_files)}

# Translation files to generate/update
TRANSLATIONS = {translations_dir}/textureAtlas_sv.ts

# Codec for source files
CODECFORSRC = UTF-8
""".strip()

    pro_file = project_root / "translations.pro"
    try:
        with open(pro_file, "w", encoding="utf-8") as f:
            f.write(pro_content)

        # Run lupdate
        print("Running lupdate to extract translatable strings...")
        result = subprocess.run(
            [lupdate_cmd, str(pro_file)], cwd=str(project_root), capture_output=True, text=True
        )

        if result.returncode == 0:
            print("Translation files updated successfully!")
            print(f"Translation files are in: {translations_dir}")
            if result.stdout:
                print("lupdate output:")
                print(result.stdout)
        else:
            print(f"lupdate failed: {result.stderr}")
            return False

    finally:
        # Clean up temporary .pro file
        if pro_file.exists():
            pro_file.unlink()

    return True


def compile_translations(qt_dir=None):
    """Compile translation files using lrelease."""
    available, lrelease_cmd = check_lrelease(qt_dir)
    if not available:
        print("Error: lrelease tool not found.")
        print("Please install Qt development tools (same as for lupdate).")
        return False

    print(f"Using lrelease: {lrelease_cmd}")

    project_root = get_project_root()
    translations_dir = project_root / "src" / "translations"

    if not translations_dir.exists():
        print(f"Translations directory not found: {translations_dir}")
        return False

    # Find all .ts files
    ts_files = list(translations_dir.glob("*.ts"))
    if not ts_files:
        print("No translation files (.ts) found.")
        return False

    success_count = 0
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")

        print(f"Compiling {ts_file.name}...")
        result = subprocess.run(
            [lrelease_cmd, str(ts_file), "-qm", str(qm_file)], capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"  -> {qm_file.name}")
            success_count += 1
        else:
            print(f"  Error compiling {ts_file.name}: {result.stderr}")

    print(f"Compiled {success_count}/{len(ts_files)} translation files.")
    return success_count > 0


def preview_strings():
    """Preview translatable strings that would be extracted."""
    import re

    project_root = get_project_root()
    source_files = get_source_files()

    if not source_files:
        print("No source files found.")
        return False

    # Patterns to find translatable strings
    patterns = [
        # QCoreApplication.translate("Context", "String")
        r'QCoreApplication\.translate\s*\(\s*["\']([^"\']*)["\'],\s*["\']([^"\']*)["\']',
        # self.tr("String")
        r'\.tr\s*\(\s*["\']([^"\']*)["\']',
        # tr("String")
        r'(?:^|\s)tr\s*\(\s*["\']([^"\']*)["\']',
        # QMessageBox with text
        r'QMessageBox\.\w+\([^"\']*["\']([^"\']*)["\']',
        # Common UI text patterns
        r'setText\s*\(\s*["\']([^"\']*)["\']',
        r'setWindowTitle\s*\(\s*["\']([^"\']*)["\']',
        r'setStatusTip\s*\(\s*["\']([^"\']*)["\']',
    ]

    found_strings = set()
    files_with_strings = 0

    print("\nScanning for translatable strings...\n")

    for source_file in source_files:
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                content = f.read()

            file_strings = set()

            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        # For patterns that capture context and string
                        if len(match) == 2:
                            context, string = match
                            if string.strip() and len(string) > 1:
                                file_strings.add(f"{context}: {string}")
                        else:
                            string = match[0] if match else ""
                            if string.strip() and len(string) > 1:
                                file_strings.add(string)
                    else:
                        # For patterns that capture just the string
                        if match.strip() and len(match) > 1:
                            file_strings.add(match)

            if file_strings:
                files_with_strings += 1
                print(f"📁 {source_file.relative_to(project_root)}:")
                for string in sorted(file_strings):
                    print(f"   • {string}")
                    found_strings.add(string)
                print()

        except Exception as e:
            print(f"Warning: Could not read {source_file}: {e}")

    print("Summary:")
    print(f"  Files scanned: {len(source_files)}")
    print(f"  Files with translatable strings: {files_with_strings}")
    print(f"  Unique translatable strings found: {len(found_strings)}")

    if found_strings:
        print("\nNote: This is a preview. Run 'update' command to actually extract with lupdate.")
    else:
        print("\nNo translatable strings found. Consider:")
        print("  - Adding QCoreApplication.translate() calls")
        print("  - Using self.tr() methods in Qt widgets")
        print("  - Marking user-visible strings for translation")

    return len(found_strings) > 0


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Translation tools for TextureAtlas Toolbox")
    parser.add_argument(
        "command",
        choices=["update", "compile", "preview"],
        help="Command to run: update (extract strings), compile (build .qm files), preview (show strings that would be extracted)",
    )
    parser.add_argument("--qt-dir", help="Path to Qt installation directory")

    args = parser.parse_args()

    if args.command == "update":
        success = update_translations(args.qt_dir)
        sys.exit(0 if success else 1)
    elif args.command == "compile":
        success = compile_translations(args.qt_dir)
        sys.exit(0 if success else 1)
    elif args.command == "preview":
        success = preview_strings()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
