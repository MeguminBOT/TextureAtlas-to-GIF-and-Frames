#!/usr/bin/env python3
"""
Migration script to consolidate legacy translations into unified app_*.ts files
Run from project root or tools/translations directory
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import shutil

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

def migrate_translations():
    """Migrate legacy textureAtlas_*.ts files to unified app_*.ts files"""
    project_root, src_dir, translations_dir = get_project_dirs()
    
    print("Migration tool for TextureAtlas Toolbox")
    print(f"Project root: {project_root}")
    print(f"Translations directory: {translations_dir}")
    print()
    
    if not translations_dir.exists():
        print(f"Error: Translations directory not found: {translations_dir}")
        return False
    
    # For Swedish, copy the existing excellent translations
    legacy_sv = translations_dir / "textureAtlas_sv.ts"
    unified_sv = translations_dir / "app_sv.ts"
    
    migrated_any = False
    
    if legacy_sv.exists():
        print(f"Copying Swedish translations from {legacy_sv.name} to {unified_sv.name}")
        
        # Create the unified Swedish file by copying the legacy one
        shutil.copy2(legacy_sv, unified_sv)
        
        # Update the language attribute if needed
        try:
            tree = ET.parse(unified_sv)
            root = tree.getroot()
            if root.tag == "TS":
                root.set("language", "sv")
                tree.write(unified_sv, encoding="utf-8", xml_declaration=True)
            print(f"✅ Swedish translations migrated to {unified_sv.name}")
            migrated_any = True
        except Exception as e:
            print(f"⚠️  Warning: Could not update language attribute: {e}")
    else:
        print("ℹ️  No legacy Swedish translations found to migrate")
    
    # Check for other legacy files
    legacy_en = translations_dir / "textureAtlas_en.ts"
    if legacy_en.exists():
        print(f"ℹ️  Found legacy English file: {legacy_en.name}")
        migrated_any = True
    
    # Clean up - rename legacy files to .backup
    legacy_files = ["textureAtlas_sv.ts", "textureAtlas_en.ts"]
    for legacy_file in legacy_files:
        legacy_path = translations_dir / legacy_file
        if legacy_path.exists():
            backup_path = translations_dir / f"{legacy_file}.backup"
            # Only move if backup doesn't already exist
            if not backup_path.exists():
                shutil.move(legacy_path, backup_path)
                print(f"📦 Moved {legacy_file} to {backup_path.name}")
            else:
                print(f"ℹ️  Backup already exists: {backup_path.name}")
    
    return migrated_any

def check_migration_status():
    """Check if migration has been completed"""
    project_root, src_dir, translations_dir = get_project_dirs()
    
    print("Migration Status Check")
    print("=" * 30)
    
    if not translations_dir.exists():
        print(f"❌ Translations directory not found: {translations_dir}")
        return
    
    # Check for unified files
    unified_files = list(translations_dir.glob("app_*.ts"))
    legacy_files = list(translations_dir.glob("textureAtlas_*.ts"))
    backup_files = list(translations_dir.glob("textureAtlas_*.ts.backup"))
    
    print(f"📁 Translations directory: {translations_dir}")
    print(f"✅ Unified files found: {len(unified_files)}")
    for f in unified_files:
        print(f"   - {f.name}")
    
    if legacy_files:
        print(f"⚠️  Legacy files still present: {len(legacy_files)}")
        for f in legacy_files:
            print(f"   - {f.name}")
        print("   Consider running migration to back these up.")
    
    if backup_files:
        print(f"📦 Backup files: {len(backup_files)}")
        for f in backup_files:
            print(f"   - {f.name}")
    
    if unified_files and not legacy_files:
        print("\n🎉 Migration appears complete!")
    elif not unified_files:
        print("\n❓ No unified translation files found. Run extraction first.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1].lower() == "status":
        check_migration_status()
    else:
        result = migrate_translations()
        if result:
            print("\n🎉 Migration complete!")
        else:
            print("\n✅ Nothing to migrate")
        
        print("\nNext steps:")
        print("1. Run: python update_translations.py extract")
        print("2. Run: python update_translations.py compile") 
        print("3. Test language switching in your application")
        print("\nOr run: python update_translations.py all")
