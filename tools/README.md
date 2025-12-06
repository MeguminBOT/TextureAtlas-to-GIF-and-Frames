# TextureAtlas Toolbox - Development Tools

This directory contains utility scripts and tools for managing the TextureAtlas Toolbox project,
primarily focused on translation/localization workflows.

## 📁 Directory Structure

```
tools/
├── translate.py              # Main CLI translation management script
├── translate.bat             # Windows batch wrapper for translate.py
├── convert ts to txt.py      # Converts between simple text format and Qt .ts files
├── convert ts to txt.bat     # Interactive Windows menu for simple translations
├── translator-app/           # GUI Translation Editor application
│   ├── src/                  # Editor source code
│   ├── app/                  # Compiled executable
│   ├── README.md             # Editor documentation
│   └── Translation Editor (Standalone).exe
└── README.md                 # This file
```

---

## 🔧 Translation Tools Overview

There are three ways to manage translations for TextureAtlas Toolbox:

| Tool | Best For | Interface |
|------|----------|-----------|
| `translate.py` | Developers, CI/CD, batch operations | CLI |
| `translator-app/` | Translators editing `.ts` files visually | GUI |
| `convert ts to txt.py` | Contributors who prefer plain text editing | CLI/Interactive |

---

## 🖥️ CLI Translation Management (`translate.py`)

The primary command-line tool for extracting, compiling, and managing translation files.

### Quick Start

```bash
# From project root
python tools/translate.py all

# Or on Windows, use the batch wrapper
tools\translate.bat all
```

### Available Commands

| Command | Description |
|---------|-------------|
| `extract` | Extract translatable strings from Python source code into `.ts` files |
| `compile` | Compile `.ts` files to binary `.qm` files for the application |
| `resource` | Create/update Qt resource file for translations |
| `status` | Show translation progress for each language |
| `disclaimer` | Add machine translation disclaimers to `.ts` files |
| `all` | Run extract → compile → resource → status in sequence |

### Usage Examples

```bash
# Extract strings for all languages
python tools/translate.py extract

# Extract only for Swedish and English
python tools/translate.py extract sv en

# Compile Swedish translations
python tools/translate.py compile sv

# Check status for Spanish, French, and German
python tools/translate.py status es fr de

# Full update cycle for all languages
python tools/translate.py all
```

### Supported Languages

Run `python tools/translate.py` without arguments to see all available language codes.
Languages are marked with indicators:
- 🤖 Machine-translated
- ✋ Native/human-translated

---

## 🎨 Translation Editor GUI (`translator-app/`)

A standalone graphical application for editing `.ts` translation files with features like:

- **Smart string grouping**: Identical strings across contexts are grouped together
- **Syntax highlighting**: Placeholders like `{count}` and `{filename}` are highlighted
- **Real-time preview**: See how translations look with sample placeholder values
- **Validation**: Prevents saving files with missing or extra placeholders
- **Dark/Light mode**: Toggle themes for comfortable editing

### Running the Editor

**Option 1: Executable (Windows)**
```
tools\translator-app\app\Translation Editor.exe
```
Or use the shortcut: `tools\translator-app\Launch Translation Editor.bat`

**Option 2: Standalone Executable (Windows)**
```
tools\translator-app\Translation Editor (Standalone).exe
```

**Option 3: Python**
```bash
python tools/translator-app/src/Main.py

# Or open a specific file
python tools/translator-app/src/Main.py src/translations/app_sv.ts
```

See [`translator-app/README.md`](translator-app/README.md) for full documentation.

---

## 📝 Simple Text Format (`convert ts to txt.py`)

For contributors who prefer editing translations in a plain text format rather than XML.

### Text Format

```
original := translated
```

Example (`sv.txt`):
```
Language Settings := Språkinställningar
Select Application Language := Välj applikationsspråk
Save := Spara
```

### Interactive Mode (Windows)

Double-click `convert ts to txt.bat` for an interactive menu that guides you through:

1. Extracting strings from `.ts` to `.txt`
2. Creating new translation templates
3. Applying `.txt` translations back to `.ts` files

### Command Line Usage

```bash
# Extract Swedish translations to simple format
python "tools/convert ts to txt.py" sv --extract

# Create a template for a new language
python "tools/convert ts to txt.py" de --create-example

# Apply translations from .txt back to .ts
python "tools/convert ts to txt.py" sv
```

---

## 🎯 Translation Workflow

### For Developers

1. Add `self.tr("Text")` to new strings in Python code
2. Run `python tools/translate.py extract` to update `.ts` files
3. Run `python tools/translate.py compile` to generate `.qm` files
4. Test language switching in the application

### For Translators

1. Open `.ts` file in the Translation Editor or your preferred tool
2. Translate entries marked as unfinished
3. Save the file
4. Ask a developer to compile, or run `python tools/translate.py compile`

### For Contributors (Simple Text Method)

1. Run `tools\convert ts to txt.bat` and choose "Extract" for your language
2. Edit the generated `.txt` file with any text editor
3. Run the batch file again and choose "Apply" to update `.ts` files
4. Submit your changes via pull request

---

## 📂 File Locations

| Type | Location |
|------|----------|
| Python source files | `src/` |
| Translation files (`.ts`, `.qm`) | `src/translations/` |
| CLI tools | `tools/` |
| GUI editor | `tools/translator-app/` |
| Simple text translations | `translations/` (created when using converter) |

---

## 🚀 Adding New Tools

When adding new development tools:

1. Create the tool in `tools/` (or a subdirectory for larger tools)
2. Add documentation to this README
3. Use relative paths that work from project root
4. Include error handling for missing directories

*Last updated: December 6, 2025 — TextureAtlas Toolbox v2.0.0*