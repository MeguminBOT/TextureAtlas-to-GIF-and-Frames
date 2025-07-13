# Translation Management Tools

This directory contains scripts for managing translations in the TextureAtlas Toolbox project.

## 🔧 Tools

### `update_translations.py`
Main translation management script that handles extraction, compilation, and status reporting.

**Usage:**
```bash
python update_translations.py [command] [languages...]
```

**Commands:**
- `extract [langs...]` - Extract translatable strings from source code to .ts files
- `compile [langs...]` - Compile .ts files to .qm files for the application
- `merge` - Merge legacy translation files (if any)
- `status [langs...]` - Show current translation status for specified languages
- `all [langs...]` - Run full update cycle (extract → merge → compile → resource file)

**Language Selection:**
- `en sv es fr de ja zh` - Specific language codes
- `all` - Process all languages (default if no languages specified)
- Multiple languages: `sv en es` - Process Swedish, English, and Spanish

**Examples:**
```bash
# Extract strings for all languages
python update_translations.py extract

# Extract strings only for Swedish and English
python update_translations.py extract sv en

# Compile only Swedish translations
python update_translations.py compile sv

# Show status for Spanish, French, and German
python update_translations.py status es fr de

# Full update cycle for Swedish only
python update_translations.py all sv

# Show status with translation progress
python update_translations.py status
```

### `migrate_translations.py`
Legacy translation migration tool for consolidating old translation files into the unified system.

**Usage:**
```bash
python migrate_translations.py [status]
```

**Commands:**
- (no args) - Run migration of legacy files
- `status` - Check migration status and show file inventory

## 📂 How It Works

### File Locations
The tools automatically detect project structure:
- **Source code**: `../../src/` (relative to tools/translations/)
- **Translation files**: `../../src/translations/`

### Path Detection
Scripts work from either location:
- Project root: `python tools/translations/update_translations.py`
- Tools directory: `cd tools/translations && python update_translations.py`

## 🔄 Workflow

1. **Add translatable strings** to Python code using `self.tr("Text")`
2. **Extract strings**: `python update_translations.py extract`
3. **Edit translations** in `.ts` files (manually or with Qt Linguist)
4. **Compile translations**: `python update_translations.py compile`
5. **Test** language switching in the application

## 📊 Status Reporting

Use `python update_translations.py status` to see:
- Which language files exist (.ts and .qm)
- Translation completion status
- File locations and sizes

## 🛠️ Requirements

- PySide6 tools (`pyside6-lupdate`, `pyside6-lrelease`)
- Python 3.10+
- Source code with `self.tr()` calls for translatable strings

## 🎯 Benefits

- **Unified management** - One file per language instead of multiple fragments
- **Safe updates** - UI file recompilation won't overwrite translations
- **Professional workflow** - Standard Qt translation system
- **Legacy support** - Preserves existing translations during migration
- **Cross-platform** - Works on Windows, Linux, macOS
