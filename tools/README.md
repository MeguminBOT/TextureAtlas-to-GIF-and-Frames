# TextureAtlas Toolbox - Development Tools

This directory contains utility scripts and tools for managing the TextureAtlas Toolbox project.

## 📁 Directory Structure

```
tools/
├── translations/           # Translation management tools
│   ├── update_translations.py    # Main translation management script
│   ├── migrate_translations.py   # Legacy translation migration tool
│   └── README.md                 # Translation tools documentation
└── README.md              # This file
```

## 🔧 Translation Tools

The translation tools are located in `tools/translations/` and can be run from either:
- Project root directory
- `tools/translations/` directory

### Quick Start

```bash
# From project root
python tools/translations/update_translations.py all

# From tools/translations directory
cd tools/translations
python update_translations.py all
```

### Available Commands

**Translation Management:**
```bash
python update_translations.py extract   # Extract strings from source code
python update_translations.py compile   # Compile .ts files to .qm files
python update_translations.py status    # Show translation status
python update_translations.py all       # Run full update cycle
```

**Legacy Migration:**
```bash
python migrate_translations.py          # Migrate legacy translation files
python migrate_translations.py status   # Check migration status
```

## 📋 Translation Status
- 🇺🇸 English (en) - Default language
- 🇸🇪 Swedish (sv) - Begun
- 🇪🇸 Spanish (es) - Unfinished
- 🇫🇷 French (fr) - Unfinished  
- 🇩🇪 German (de) - Unfinished
- 🇯🇵 Japanese (ja) - Unfinished
- 🇨🇳 Chinese (zh) - Unfinished

## 🎯 Workflow

1. **Development**: Add `self.tr("Text")` to new strings in Python code
2. **Extract**: Run `update_translations.py extract` to update translation files
3. **Translate**: Edit `.ts` files with translations or use Qt Linguist
4. **Compile**: Run `update_translations.py compile` to create `.qm` files
5. **Test**: Test language switching in the application

## 📂 File Locations

- **Source files**: `src/` (Python code with translatable strings)
- **Translation files**: `src/translations/` (`.ts` and `.qm` files)
- **Tools**: `tools/translations/` (management scripts)

## 🚀 Adding New Tools

When adding new development tools:
1. Create appropriate subdirectory under `tools/`
2. Add documentation to this README
3. Use relative paths that work from project root
4. Include error handling for missing directories
