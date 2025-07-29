#!/usr/bin/env python3
"""
Translation management script for TextureAtlas Toolbox
Extracts and updates translation files from source code
Run from project root or tools directory
"""

import sys
import subprocess
from pathlib import Path


def get_project_dirs():
    """Get the project and translation directories"""
    script_dir = Path(__file__).parent

    # If script is in tools/translations, go up two levels to project root
    if script_dir.name == "translations" and script_dir.parent.name == "tools":
        project_root = script_dir.parent.parent
        src_dir = project_root / "src"
        translations_dir = src_dir / "translations"
    elif script_dir.name == "tools":
        # Script is directly in tools directory
        project_root = script_dir.parent
        src_dir = project_root / "src"
        translations_dir = src_dir / "translations"
    else:
        # Fallback: assume script is run from project root
        project_root = Path.cwd()
        src_dir = project_root / "src"
        translations_dir = src_dir / "translations"

    return project_root, src_dir, translations_dir

def get_available_languages():
    """Get list of available language codes and names with translation quality info"""
    return {
        "en": {"name": "English", "english_name": "English", "quality": "native"},
        "ar": {"name": "العربية", "english_name": "Arabic", "quality": "machine"},
        "bg": {"name": "Български", "english_name": "Bulgarian", "quality": "machine"},
        "zh_CN": {"name": "简体中文", "english_name": "Chinese (Simplified)", "quality": "machine"},
        "zh_TW": {"name": "繁體中文", "english_name": "Chinese (Traditional)", "quality": "machine"},
        "hr": {"name": "Hrvatski", "english_name": "Croatian", "quality": "machine"},
        "cs": {"name": "Čeština", "english_name": "Czech", "quality": "machine"},
        "da": {"name": "Dansk", "english_name": "Danish", "quality": "machine"},
        "nl": {"name": "Nederlands", "english_name": "Dutch", "quality": "machine"},
        "et": {"name": "Eesti", "english_name": "Estonian", "quality": "machine"},
        "fi": {"name": "Suomi", "english_name": "Finnish", "quality": "machine"},
        "fr": {"name": "Français", "english_name": "French", "quality": "machine"},
        "fr_CA": {"name": "Français canadien", "english_name": "French (Canadian)", "quality": "machine"},
        "de": {"name": "Deutsch", "english_name": "German", "quality": "machine"},
        "el": {"name": "Ελληνικά", "english_name": "Greek", "quality": "machine"},
        "he": {"name": "עברית", "english_name": "Hebrew", "quality": "machine"},
        "hi": {"name": "हिन्दी", "english_name": "Hindi", "quality": "machine"},
        "hu": {"name": "Magyar", "english_name": "Hungarian", "quality": "machine"},
        "is": {"name": "Íslenska", "english_name": "Icelandic", "quality": "machine"},
        "it": {"name": "Italiano", "english_name": "Italian", "quality": "machine"},
        "ja": {"name": "日本語", "english_name": "Japanese", "quality": "machine"},
        "ko": {"name": "한국어", "english_name": "Korean", "quality": "machine"},
        "lv": {"name": "Latviešu", "english_name": "Latvian", "quality": "machine"},
        "lt": {"name": "Lietuvių", "english_name": "Lithuanian", "quality": "machine"},
        "no": {"name": "Norsk bokmål", "english_name": "Norwegian (Bokmål)", "quality": "machine"},
        "nn": {"name": "Norsk nynorsk", "english_name": "Norwegian (Nynorsk)", "quality": "machine"},
        "pl": {"name": "Polski", "english_name": "Polish", "quality": "machine"},
        "pt": {"name": "Português", "english_name": "Portuguese", "quality": "machine"},
        "pt_br": {"name": "Português (Brasil)", "english_name": "Portuguese (Brazil)", "quality": "native"},
        "ro": {"name": "Română", "english_name": "Romanian", "quality": "machine"},
        "ru": {"name": "Русский", "english_name": "Russian", "quality": "machine"},
        "sk": {"name": "Slovenčina", "english_name": "Slovak", "quality": "machine"},
        "sl": {"name": "Slovenščina", "english_name": "Slovenian", "quality": "machine"},
        "sv": {"name": "Svenska", "english_name": "Swedish", "quality": "native"},
        "es": {"name": "Español", "english_name": "Spanish", "quality": "machine"},
        "th": {"name": "ไทย", "english_name": "Thai", "quality": "machine"},
        "tr": {"name": "Türkçe", "english_name": "Turkish", "quality": "machine"},
        "uk": {"name": "Українська", "english_name": "Ukrainian", "quality": "machine"},
        "vi": {"name": "Tiếng Việt", "english_name": "Vietnamese", "quality": "machine"},
    }

def parse_languages(lang_args):
    """Parse language arguments and return list of language codes"""
    available_languages = get_available_languages()

    if not lang_args or "all" in lang_args:
        return list(available_languages.keys())

    # Validate and collect requested languages
    requested_languages = []
    for lang in lang_args:
        lang_lower = lang.lower()
        if lang_lower in available_languages:
            requested_languages.append(lang_lower)
        else:
            print(
                f"Warning: Unknown language '{lang}'. Available: {', '.join(available_languages.keys())}"
            )

    if not requested_languages:
        print("No valid languages specified. Using all languages.")
        return list(available_languages.keys())

    return requested_languages


def run_command(command, cwd=None):
    """Run a command and handle errors"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"Error output: {result.stderr}")
            return False
        print(f"Success: {command}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except Exception as e:
        print(f"Exception running command {command}: {e}")
        return False

def extract_translations(languages=None):
    """Extract translatable strings from source files"""
    project_root, src_dir, translations_dir = get_project_dirs()

    # Default to all languages if none specified
    if languages is None:
        languages = list(get_available_languages().keys())

    print(f"Project root: {project_root}")
    print(f"Source directory: {src_dir}")
    print(f"Translations directory: {translations_dir}")
    print(f"Languages to process: {', '.join(languages)}")
    print("Extracting translatable strings...")

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return False

    if not translations_dir.exists():
        print(f"Creating translations directory: {translations_dir}")
        translations_dir.mkdir(parents=True, exist_ok=True)

    # Extract from Python files and UI files into a single unified translation file
    py_files = []
    for pattern in ["*.py", "gui/*.py", "utils/*.py", "core/*.py", "parsers/*.py"]:
        py_files.extend(src_dir.glob(pattern))

    # Also include UI files
    ui_files = list(src_dir.glob("gui/*.ui"))

    # Create a list of Python files to process
    py_file_list = [str(f) for f in py_files if f.is_file()]
    ui_file_list = [str(f) for f in ui_files if f.is_file()]

    all_files = py_file_list + ui_file_list

    if all_files:
        # Create unified translation files for specified languages
        for lang in languages:
            ts_file = translations_dir / f"app_{lang}.ts"
            # Use pyside6-lupdate for both Python and UI files
            files_str = " ".join(f'"{f}"' for f in all_files)
            cmd = f'pyside6-lupdate {files_str} -ts "{ts_file}"'
            if not run_command(cmd):
                print(f"Failed to extract to {ts_file}")
            else:
                print(
                    f"Updated {ts_file} (processed {len(py_file_list)} Python files and {len(ui_file_list)} UI files)"
                )
        return True
    else:
        print("No Python or UI files found for translation extraction")
        return False

def compile_translations(languages=None):
    """Compile .ts files to .qm files"""
    project_root, src_dir, translations_dir = get_project_dirs()

    # Default to all languages if none specified
    if languages is None:
        languages = list(get_available_languages().keys())

    print(f"Languages to compile: {', '.join(languages)}")
    print("Compiling translation files...")

    if not translations_dir.exists():
        print(f"Error: Translations directory not found: {translations_dir}")
        return False

    # Filter to only specified languages
    ts_files = []
    for lang in languages:
        ts_file = translations_dir / f"app_{lang}.ts"
        if ts_file.exists():
            ts_files.append(ts_file)
        else:
            print(f"Warning: Translation file not found: {ts_file}")

    if not ts_files:
        print("No translation files found for compilation")
        return False

    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        cmd = f'pyside6-lrelease "{ts_file}" -qm "{qm_file}"'
        if not run_command(cmd):
            print(f"Failed to compile {ts_file}")

    return True

def create_resource_file():
    """Create a Qt resource file for translations"""
    project_root, src_dir, translations_dir = get_project_dirs()

    qm_files = list(translations_dir.glob("app_*.qm"))

    if not qm_files:
        print("No .qm files found for resource file creation")
        return

    qrc_content = """<!DOCTYPE RCC>
<RCC version="1.0">
<qresource prefix="/translations">
"""

    for qm_file in qm_files:
        qrc_content += f"    <file>{qm_file.name}</file>\n"

    qrc_content += """</qresource>
</RCC>"""

    qrc_file = translations_dir / "translations.qrc"
    with open(qrc_file, "w", encoding="utf-8") as f:
        f.write(qrc_content)

    print(f"Created resource file: {qrc_file}")

def show_status(languages=None):
    """Show current translation status"""
    project_root, src_dir, translations_dir = get_project_dirs()

    all_languages = get_available_languages()

    # Default to all languages if none specified
    if languages is None:
        languages = list(all_languages.keys())

    print(f"\n📁 Translation Status - {translations_dir}")
    if len(languages) < len(all_languages):
        print(f"Showing status for: {', '.join(languages)}")
    print("=" * 60)

    for lang_code in languages:
        if lang_code not in all_languages:
            print(f"Warning: Unknown language '{lang_code}'")
            continue

        lang_info = all_languages[lang_code]
        lang_name = lang_info["name"] if isinstance(lang_info, dict) else lang_info
        ts_file = translations_dir / f"app_{lang_code}.ts"
        qm_file = translations_dir / f"app_{lang_code}.qm"

        ts_status = "✅" if ts_file.exists() else "❌"
        qm_status = "✅" if qm_file.exists() else "❌"

        # Add quality indicator
        quality_indicator = ""
        if isinstance(lang_info, dict):
            if lang_info.get("quality") == "machine":
                quality_indicator = " 🤖"  # Robot emoji for machine translated
            elif lang_info.get("quality") == "native":
                quality_indicator = " ✋"  # Hand emoji for native quality

        # Get translation count if file exists
        count_info = ""
        if ts_file.exists():
            try:
                with open(ts_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Count messages and finished translations more accurately
                    total_messages = content.count("<message>")
                    unfinished_count = content.count('type="unfinished"')
                    finished_translations = total_messages - unfinished_count
                    if total_messages > 0:
                        percentage = (finished_translations / total_messages) * 100
                        count_info = (
                            f" ({finished_translations}/{total_messages}, {percentage:.0f}%)"
                        )
            except Exception:
                pass

        print(
            f"{lang_code.upper()} {lang_name:12} | .ts {ts_status} | .qm {qm_status}{count_info}{quality_indicator}"
        )

def inject_machine_translation_disclaimers(languages=None):
    """Inject machine translation disclaimers into translation files"""
    project_root, src_dir, translations_dir = get_project_dirs()
    all_languages = get_available_languages()

    # Default to all languages if none specified
    if languages is None:
        languages = list(all_languages.keys())

    print("Injecting machine translation disclaimers...")

    for lang_code in languages:
        if lang_code not in all_languages:
            print(f"Warning: Unknown language '{lang_code}'")
            continue

        lang_info = all_languages[lang_code]
        if not isinstance(lang_info, dict) or lang_info.get("quality") != "machine":
            print(f"Skipping {lang_code}: Not marked as machine translated")
            continue

        ts_file = translations_dir / f"app_{lang_code}.ts"
        if not ts_file.exists():
            print(f"Warning: Translation file not found: {ts_file}")
            continue

        try:
            # Read the current translation file
            with open(ts_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Define the disclaimer context and message
            disclaimer_context = """<context>
    <name>MachineTranslationDisclaimer</name>
    <message>
        <location filename="../Main.py" line="0"/>
        <source>Machine Translation Notice</source>
        <translation type="unfinished">Machine Translation Notice</translation>
    </message>
    <message>
        <location filename="../Main.py" line="1"/>
        <source>This language was automatically translated and may contain inaccuracies. If you would like to contribute better translations, please visit our GitHub repository.</source>
        <translation type="unfinished">This language was automatically translated and may contain inaccuracies. If you would like to contribute better translations, please visit our GitHub repository.</translation>
    </message>
</context>"""

            # Check if disclaimer already exists
            if "MachineTranslationDisclaimer" in content:
                print(f"Disclaimer already exists in {ts_file}")
                continue

            # Find the position to insert (before </TS>)
            if "</TS>" in content:
                # Insert before closing tag
                content = content.replace("</TS>", disclaimer_context + "\n</TS>")

                # Write back to file
                with open(ts_file, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"Added machine translation disclaimer to {ts_file}")
            else:
                print(f"Warning: Could not find insertion point in {ts_file}")

        except Exception as e:
            print(f"Error processing {ts_file}: {e}")

def main():
    # Simple argument parsing (avoiding argparse import for cleaner dependency list)
    if len(sys.argv) < 2:
        print("Translation Management Tool for TextureAtlas Toolbox")
        print("=" * 50)
        print("Usage: python update_translations.py [command] [languages...]")
        print()
        print("Commands:")
        print("  extract    - Extract translatable strings from source code")
        print("  compile    - Compile .ts files to .qm files")
        print("  resource   - Create/update Qt resource file for translations")
        print("  status     - Show translation status")
        print("  disclaimer - Add machine translation disclaimers")
        print("  all        - Run extract, compile, and create resource file")
        print()
        print("Languages (optional):")
        available_langs = get_available_languages()
        for code, lang_info in available_langs.items():
            if isinstance(lang_info, dict):
                name = lang_info["name"]
                english_name = lang_info.get("english_name", "")
                quality = lang_info.get("quality", "unknown")
                quality_indicator = (
                    " 🤖" if quality == "machine" else " ✋" if quality == "native" else ""
                )
                display_name = f"{name} ({english_name})" if english_name != name else name
                print(f"  {code:2} - {display_name}{quality_indicator}")
            else:
                print(f"  {code:2} - {lang_info}")
        print("  all      - Process all languages (default)")
        print()
        print("Examples:")
        print("  python update_translations.py extract")
        print("  python update_translations.py extract sv en")
        print("  python update_translations.py compile sv")
        print("  python update_translations.py resource")
        print("  python update_translations.py status es fr de")
        print("  python update_translations.py disclaimer es fr de")
        print("  python update_translations.py all sv")
        sys.exit(1)

    # Parse command and languages
    command = sys.argv[1].lower()
    lang_args = sys.argv[2:] if len(sys.argv) > 2 else ["all"]

    # Parse languages
    languages = parse_languages(lang_args)

    print(f"Command: {command}")
    print(f"Languages: {', '.join(languages)}")
    print()

    # Execute command
    if command == "extract":
        extract_translations(languages)
    elif command == "compile":
        compile_translations(languages)
    elif command == "resource":
        create_resource_file()
    elif command == "status":
        show_status(languages)
    elif command == "disclaimer":
        inject_machine_translation_disclaimers(languages)
    elif command == "all":
        print("Running full translation update...")
        extract_translations(languages)
        compile_translations(languages)
        create_resource_file()
        show_status(languages)
    else:
        print(f"Invalid command: {command}")
        print("Valid commands: extract, compile, resource, status, disclaimer, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
