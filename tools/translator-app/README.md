# Translation Helper

A comprehensive Qt-based GUI tool for editing translation files (.ts) for the TextureAtlas Toolbox.

## Features

- **Smart String Grouping**: Automatically groups identical source strings across multiple contexts, reducing translation work
- **Syntax Highlighting**: Highlights placeholders (e.g., `{count}`, `{filename}`) in both source and translation text
- **Dark/Light Mode**: Toggle between themes for comfortable editing in any environment
- **Real-time Preview**: See how translations look with actual placeholder values
- **Validation System**: Prevents saving files with missing or extra placeholders
- **Context Information**: Shows all contexts where each string is used
- **Copy Source**: Quick button to copy source text as a starting point for translation

## Usage

### Running the Application

**Option 1: Using the regular executable (Windows)**
1. Run `Translation Editor.exe` in the app folder or run the shortcut `Launch Translation Editor.bat`
**Note**: May be detected as a false positive by anti-virus.


**Option 2: Using the compressed "standalone" executable (Windows)**
1. Run `Translation Editor (Standalone).exe`
**Note**: This variant are more likely to be detected as a false positive by anti-virus than Option 1.

**Option 3: Using Python**
```bash
# From the src directory
cd src
python translation_editor.py

# Or from anywhere with a file argument
python tools/translator-app/src/translation_editor.py path/to/file.ts

# Using the launcher (Windows)
```

**Note**: The executable version includes all dependencies and doesn't require Python to be installed.

### Quick Start

1. **Open a .ts file**: Click "Open .ts File" or use Ctrl+O
2. **Select a translation**: Click on any item in the left list
3. **Edit translation**: Type in the "Translation" field on the right
4. **Preview results**: Use the placeholder fields to see how the translation looks
5. **Save**: Use Ctrl+S or click "Save .ts File"

### Visual Indicators

- ✅ **Green checkmark**: Translation is complete
- ❌ **Red X**: Translation is missing
- 📎**Number**: String appears in multiple contexts (grouped)

### Keyboard Shortcuts

- `Ctrl+O`: Open file
- `Ctrl+S`: Save file
- `Ctrl+Shift+S`: Save as
- `Ctrl+Q`: Exit

## File Structure

```
translator-app/
├── src/
│   ├── translation_editor.py    # Main application
│   └── setup/
│       └── build-windows.bat    # Windows build script

├── launch-translation-helper.bat # Quick launcher
├── requirements.txt             # Python dependencies
└── README.md                   # This file
```

## Smart Grouping Feature

When the same source string appears in multiple contexts (e.g., "Save" button appears in multiple dialogs), the tool automatically groups them together. This means:

- You only need to translate each unique string once
- Changes apply to all contexts using that string
- The context panel shows where each string is used
- Saving maintains the original file structure with all contexts

## Validation

The tool validates that:
- All placeholders from source text are included in translation
- No extra placeholders are added in translation
- Files cannot be saved with validation errors

This prevents runtime errors in the main application.
