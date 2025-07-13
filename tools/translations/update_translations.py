#!/usr/bin/env python3
"""
Translation management script for TextureAtlas Toolbox
Extracts and updates translation files from source code
Run from project root or tools/translations directory
"""

import sys
import subprocess
from pathlib import Path
import argparse

def get_project_dirs():
    """Get the project and translation directories"""
    script_dir = Path(__file__).parent
    
    # If script is in tools/translations, go up two levels to project root
    if script_dir.name == "translations" and script_dir.parent.name == "tools":
        project_root = script_dir.parent.parent
        src_dir = project_root / "src"
        translations_dir = src_dir / "translations"
    else:
        # Fallback: assume script is run from project root
        project_root = Path.cwd()
        src_dir = project_root / "src"
        translations_dir = src_dir / "translations"
    
    return project_root, src_dir, translations_dir

def get_available_languages():
    """Get list of available language codes and names"""
    return {
        "en": "English",
        "sv": "Svenska",
        "es": "Español", 
        "fr": "Français",
        "de": "Deutsch",
        "ja": "日本語",
        "zh": "中文"
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
            print(f"Warning: Unknown language '{lang}'. Available: {', '.join(available_languages.keys())}")
    
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
    
    # Extract from Python files into a single unified translation file
    py_files = []
    for pattern in ["*.py", "gui/*.py", "utils/*.py", "core/*.py", "parsers/*.py"]:
        py_files.extend(src_dir.glob(pattern))
    
    # Create a list of Python files to process
    py_file_list = [str(f) for f in py_files if f.is_file()]
    
    if py_file_list:
        # Create unified translation files for specified languages
        for lang in languages:
            ts_file = translations_dir / f"app_{lang}.ts"
            # Use pylupdate for Python files
            files_str = " ".join(f'"{f}"' for f in py_file_list)
            cmd = f'pyside6-lupdate {files_str} -ts "{ts_file}"'
            if not run_command(cmd):
                print(f"Failed to extract to {ts_file}")
            else:
                print(f"Updated {ts_file}")
        return True
    else:
        print("No Python files found for translation extraction")
        return False

def merge_legacy_translations():
    """Merge existing legacy translations into unified files"""
    project_root, src_dir, translations_dir = get_project_dirs()
    
    print("Merging legacy translations...")
    
    # Map legacy files to unified files
    legacy_files = {
        "textureAtlas_sv.ts": "app_sv.ts",
        "textureAtlas_en.ts": "app_en.ts"
    }
    
    for legacy_name, unified_name in legacy_files.items():
        legacy_file = translations_dir / legacy_name
        unified_file = translations_dir / unified_name
        
        if legacy_file.exists() and unified_file.exists():
            print(f"Legacy translations found in {legacy_name}, keeping both files for compatibility")
            # You can manually merge translations using Qt Linguist if needed

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
        qm_file = ts_file.with_suffix('.qm')
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
    
    qrc_content = '''<!DOCTYPE RCC>
<RCC version="1.0">
<qresource prefix="/translations">
'''
    
    for qm_file in qm_files:
        qrc_content += f'    <file>{qm_file.name}</file>\n'
    
    qrc_content += '''</qresource>
</RCC>'''
    
    qrc_file = translations_dir / "translations.qrc"
    with open(qrc_file, 'w', encoding='utf-8') as f:
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
            
        lang_name = all_languages[lang_code]
        ts_file = translations_dir / f"app_{lang_code}.ts"
        qm_file = translations_dir / f"app_{lang_code}.qm"
        
        ts_status = "✅" if ts_file.exists() else "❌"
        qm_status = "✅" if qm_file.exists() else "❌"
        
        # Get translation count if file exists
        count_info = ""
        if ts_file.exists():
            try:
                with open(ts_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Count messages and finished translations more accurately
                    total_messages = content.count('<message>')
                    unfinished_count = content.count('type="unfinished"')
                    finished_translations = total_messages - unfinished_count
                    if total_messages > 0:
                        percentage = (finished_translations / total_messages) * 100
                        count_info = f" ({finished_translations}/{total_messages}, {percentage:.0f}%)"
            except Exception:
                pass
        
        print(f"{lang_code.upper()} {lang_name:12} | .ts {ts_status} | .qm {qm_status}{count_info}")

def main():
    # Simple argument parsing (avoiding argparse import for cleaner dependency list)
    if len(sys.argv) < 2:
        print("Translation Management Tool for TextureAtlas Toolbox")
        print("=" * 50)
        print("Usage: python update_translations.py [command] [languages...]")
        print()
        print("Commands:")
        print("  extract  - Extract translatable strings from source code")
        print("  compile  - Compile .ts files to .qm files")
        print("  merge    - Merge legacy translation files")
        print("  status   - Show translation status")
        print("  all      - Run extract, merge, compile, and create resource file")
        print()
        print("Languages (optional):")
        available_langs = get_available_languages()
        for code, name in available_langs.items():
            print(f"  {code:2} - {name}")
        print("  all      - Process all languages (default)")
        print()
        print("Examples:")
        print("  python update_translations.py extract")
        print("  python update_translations.py extract sv en")
        print("  python update_translations.py compile sv")
        print("  python update_translations.py status es fr de")
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
    elif command == "merge":
        merge_legacy_translations()
    elif command == "status":
        show_status(languages)
    elif command == "all":
        print("Running full translation update...")
        extract_translations(languages)
        merge_legacy_translations()
        compile_translations(languages)
        create_resource_file()
        show_status(languages)
    else:
        print(f"Invalid command: {command}")
        print("Valid commands: extract, compile, merge, status, all")
        sys.exit(1)

if __name__ == "__main__":
    main()
