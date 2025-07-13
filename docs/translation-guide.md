# Translation Guide

This guide explains how to contribute translations to the TextureAtlas Toolbox application. The project uses Qt's translation system with `.ts` (TypeScript Translation) files that can be edited with various tools.

**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**

## 📋 Table of Contents

- [Translation System Overview](#-translation-system-overview)
- [Getting Started](#-getting-started)
- [TS File Structure](#-ts-file-structure)
- [What to Translate](#-what-to-translate)
- [Placeholder Variables](#-placeholder-variables)
- [Translation Tools](#-translation-tools)
- [Working with TS Files](#-working-with-ts-files)
- [Testing Your Translations](#-testing-your-translations)
- [Translation Management Scripts](#-translation-management-scripts)
- [Best Practices](#-best-practices)
- [Troubleshooting](#-troubleshooting)

## 🌐 Translation System Overview

The TextureAtlas Toolbox uses Qt's internationalization (i18n) system:

- **Source Language**: English (en_US)
- **Translation Files**: Located in `src/translations/`
- **File Format**: Qt TS files (XML-based)
- **Compiled Files**: QM files (binary, generated automatically)
- **Supported Languages**: English, Swedish, Spanish, French, German, Japanese, Chinese

### File Structure
```
src/translations/
├── app_en.ts      # English (reference/source)
├── app_sv.ts      # Swedish
├── app_es.ts      # Spanish  
├── app_fr.ts      # French
├── app_de.ts      # German
├── app_ja.ts      # Japanese
└── app_zh.ts      # Chinese
```

## 🚀 Getting Started

### Prerequisites
- Basic understanding of the target language
- Text editor or Qt Linguist (recommended)
- Git for version control (if contributing)

### Quick Start
1. Choose your language file (e.g., `app_es.ts` for Spanish)
2. Open the file in your preferred editor. Notepad will suffice, but Notepad++/VS Code or any colour coded text editor is recommended.
3. Find entries with `<translation type="unfinished"></translation>`
4. Add your translation between the `<translation>` tags
5. Save the file and test your changes

## 📁 TS File Structure

TS files are XML-based with a specific structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="sv">
<context>
    <name>WindowClassName</name>
    <message>
        <location filename="../gui/window.py" line="42"/>
        <source>Original English Text</source>
        <translation>Your Translation Here</translation>
    </message>
</context>
</TS>
```

### Key Elements

#### File Header
```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="sv">
```
- **version**: Qt TS format version (always 2.1)
- **language**: ISO language code (e.g., `sv` for Swedish, `es` for Spanish)

#### Context Blocks
```xml
<context>
    <name>TextureAtlasExtractorApp</name>
    <!-- Messages for this class/context -->
</context>
```
- **name**: The Python class or context where the text appears
- Groups related translations together
- Common contexts: `TextureAtlasExtractorApp`, `ProcessingWindow`, `SettingsWindow`

#### Message Entries
```xml
<message>
    <location filename="../Main.py" line="147"/>
    <source>Variable delay</source>
    <translation>Variabel fördröjning</translation>
</message>
```
- **location**: Source file and line number (for reference only)
- **source**: Original English text (DO NOT MODIFY)
- **translation**: Your translated text

#### Translation States
```xml
<!-- Not yet translated -->
<translation type="unfinished"></translation>

<!-- Translated -->
<translation>Your Translation</translation>

<!-- Obsolete/removed from source -->
<translation type="vanished">Old Translation</translation>
```

## 🔍 What to Translate

### Translate These Elements
✅ **User Interface Text**
- Button labels: "Start process", "Cancel", "OK"
- Menu items: "File", "Settings", "Help"
- Tab titles: "Animation Settings", "Compression"
- Dialog titles: "Error", "Warning", "Success"

✅ **User Messages**
- Error messages: "No input directory selected"
- Success messages: "Processing completed successfully!"
- Warning messages: "Could not load language"
- Information text: "Select files to process"

✅ **Tooltips and Help Text**
- Explanatory text for UI elements
- Status descriptions
- Guide text

✅ **File Dialog Labels**
- "Select Input Directory"
- "Select Output Directory" 
- "Image files (*.png *.jpg *.jpeg);;All files (*.*)"

### Do NOT Translate
❌ **Technical Terms**
- File extensions: ".png", ".xml", ".ts"
- Format names: "TextureAtlas", "GIF", "WebP"
- Technical settings: "FPS", "RGB", "alpha"

❌ **Variable Names and Placeholders**
- `{version}`, `{filename}`, `{count}` (see Placeholder Variables section)
- Code-related terms that would break functionality

❌ **Source Elements**
- Never modify `<source>` content
- Never change `<location>` attributes
- Don't alter XML structure

## 🔧 Placeholder Variables

Many strings contain placeholder variables that get replaced with actual values at runtime.

### Common Placeholders
```xml
<!-- Version numbers -->
<source>TextureAtlas Toolbox v{version}</source>
<translation>TextureAtlas Toolbox v{version}</translation>

<!-- File names (Swedish example) -->
<source>Processing: {filename}</source>
<translation>Bearbetar: {filename}</translation>

<!-- Counts and numbers (Swedish example) -->
<source>Progress: {current} / {total} files</source>
<translation>Framsteg: {current} / {total} filer</translation>

<!-- Multiple variables (Swedish example) -->
<source>CPU: {cpu} (Threads: {threads})</source>
<translation>Processor: {cpu} (Trådar: {threads})</translation>
```

### Rules for Placeholders
1. **Always preserve the exact placeholder text**: `{version}`, `{filename}`, etc.
2. **You can reorder placeholders** to match your language's grammar
3. **You can adjust surrounding text** but keep the `{placeholder}` intact
4. **Common placeholders**:
   - `{version}` - Version numbers
   - `{filename}` - File names
   - `{count}`, `{current}`, `{total}` - Numbers
   - `{error}` - Error messages
   - `{cpu}`, `{threads}`, `{memory}` - System information

### Examples by Language

**English (Original)**
```xml
<source>Found {count} unknown spritesheet(s) with background colors.</source>
```

**Swedish**
```xml
<translation>Hittade {count} okända spritesheet(s) med bakgrundsfärger.</translation>
```

**German**
```xml
<translation>Es wurden {count} unbekannte Spritesheet(s) mit Hintergrundfarben gefunden.</translation>
```

**French**
```xml
<translation>Trouvé {count} spritesheet(s) inconnue(s) avec des couleurs d'arrière-plan.</translation>
```
   
   # With context for disambiguation
   text = QCoreApplication.translate("ButtonContext", "Save")
   ```

3. **In UI classes**, use the `self.tr()` method:
   ```python
   class MyWindow(QDialog):
       def tr(self, text):
           return QCoreApplication.translate("MyWindow", text)
       
       def setup_ui(self):
           self.button.setText(self.tr("Click Me"))
   ```

#### Updating Translation Files

1. **Extract new strings** (requires Qt tools):
   ```bash
   python tools/translation_manager.py update
   ```

2. **Compile translations**:
   ```bash
   python tools/translation_manager.py compile
   ```

#### Adding a New Language

1. **Create the translation file**:
   ```bash
   # Add the language to the translation_manager.py script
   # Then run:
   python tools/translation_manager.py update
   ```

2. **Add to available languages** in `src/utils/translation_manager.py`:
   ```python
   self.available_languages = {
       # ... existing languages ...
       "new_lang": "Language Name",
   }
   ```

3. **Translate the strings** in the generated `.ts` file
4. **Compile the translations**:
   ```bash
   python tools/translation_manager.py compile
   ```

## Translation File Format

Translation files use Qt's .ts XML format:

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="es">
<context>
    <name>ClassName</name>
    <message>
        <source>Original English text</source>
        <translation>Translated text</translation>
    </message>
</context>
</TS>
```

## 🛠️ Translation Tools

### Option 1: Qt Linguist
Qt Linguist is the official tool for editing TS files.

**Installation**
- Windows: Download Qt installer, select "Qt Linguist"
- Linux: `sudo apt install qttools5-dev-tools` (or similar)
- macOS: Install Qt via Homebrew

**Features**
- Visual editor with context
- Automatic validation
- Translation memory
- Progress tracking
- Spell checking

**Usage**
1. Open Qt Linguist
2. File → Open → Select your `.ts` file
3. Navigate through messages
4. Enter translations in the bottom panel
5. File → Save to update the TS file

### Option 2: Text Editor
Any text editor can edit TS files, but you need to be careful with XML syntax.

**Recommended Editors**
- VS Code (with XML extensions)
- Sublime Text
- Notepad++
- Vim/Emacs

**Pros**: Simple, fast, no additional software
**Cons**: No validation, easy to break XML, no translation aids

### Option 3: Online Translation Tools
Some online tools support TS files, but always verify the output.

## 📝 Working with TS Files

### Finding Untranslated Strings
Look for entries like this:
```xml
<translation type="unfinished"></translation>
```

### Adding a Translation
Change from:
```xml
<translation type="unfinished"></translation>
```

To:
```xml
<translation>Your Translation Here</translation>
```

### Updating Existing Translations
Simply replace the text between `<translation>` tags:
```xml
<!-- Before -->
<translation>Old Translation</translation>

<!-- After -->
<translation>New Improved Translation</translation>
```

### Handling Special Characters

**Quotes and Apostrophes**
Use XML entities for special characters:
```xml
<!-- Use &apos; for apostrophes in XML -->
<source>animations with &apos;idle&apos; in their name</source>
<translation>animationer med &apos;idle&apos; i namnet</translation>

<!-- Use &quot; for quotes -->
<source>Select &quot;Advanced&quot; options</source>
<translation>Välj &quot;Avancerade&quot; alternativ</translation>
```

**Other Special Characters**
- `&lt;` for `<`
- `&gt;` for `>`
- `&amp;` for `&`

### Multi-line Translations
For longer text, you can use line breaks:
```xml
<translation>This is a longer translation
that spans multiple lines for
better readability.</translation>
```

## 🧪 Testing Your Translations

### Using the Application
1. Save your TS file
2. Run the translation management script to compile:
   ```bash
   python tools/translations/update_translations.py compile sv
   ```
3. Launch the application
4. Go to Settings → Language → Select your language
5. Verify your translations appear correctly

### Translation Management Script
The project includes scripts to help manage translations:

```bash
# Extract new strings from source code
python tools/translations/update_translations.py extract sv

# Compile translations to binary format
python tools/translations/update_translations.py compile sv

# Show translation status
python tools/translations/update_translations.py status sv

# Work with multiple languages
python tools/translations/update_translations.py status sv es fr
```

### Validation Checklist
- [ ] All placeholders (`{variable}`) are preserved
- [ ] No XML syntax errors
- [ ] Text fits in the UI (not too long)
- [ ] Special characters are properly escaped
- [ ] Context makes sense for the UI element
- [ ] Grammar and spelling are correct

## 🔧 Translation Management Scripts

The project includes powerful scripts to manage translations efficiently.

### Location
Scripts are located in `tools/translations/`:
- `update_translations.py` - Main management script
- `migrate_translations.py` - Legacy migration tool
- `translate.bat` - Windows convenience script

### Common Commands

**Check Translation Status**
```bash
# Status for all languages
python tools/translations/update_translations.py status

# Status for specific languages
python tools/translations/update_translations.py status sv es fr

# Status for Swedish only
python tools/translations/update_translations.py status sv
```

**Extract New Strings**
```bash
# Extract for all languages
python tools/translations/update_translations.py extract

# Extract for specific languages
python tools/translations/update_translations.py extract sv es
```

**Compile Translations**
```bash
# Compile all languages
python tools/translations/update_translations.py compile

# Compile specific languages
python tools/translations/update_translations.py compile sv fr
```

### Windows Convenience Script
Windows users can use the batch script:
```batch
# Show status
.\translate.bat status sv

# Extract and compile Swedish
.\translate.bat extract sv
.\translate.bat compile sv

# Work with multiple languages
.\translate.bat status sv es fr
```

### Understanding Status Output
```
Translation Status Report
========================

Swedish (sv): 131/201 translated (65%)
Spanish (es): 19/205 translated (9%)  
French (fr): 13/200 translated (6%)
```

This shows:
- **Language name and code**
- **Translated count / Total count**
- **Completion percentage**

## 💡 Best Practices

### Language-Specific Guidelines Example.

**Swedish (sv)**
- Use formal address ("ni" forms) in UI
- Keep compound words reasonable length
- Maintain consistent terminology

**Spanish (es)**
- Consider regional variations (prefer neutral Spanish)
- Use consistent gender for technical terms
- Watch for text expansion (Spanish ~20% longer than English)

**French (fr)**
- Follow proper capitalization rules
- Consider formal vs informal address
- Account for text length changes

**German (de)**
- Handle compound words appropriately
- Consider formal address (Sie/Du)
- Watch for significant text expansion

**Japanese (ja)**
- Consider context for politeness levels
- Keep technical terms in katakana when appropriate
- Be mindful of vertical text limitations

**Chinese (zh)**
- Use Simplified Chinese unless specified
- Keep technical terms consistent
- Consider character width in UI layouts

### General Guidelines

**Consistency**
- Maintain consistent terminology throughout
- Use the same translation for repeated phrases
- Keep UI element names consistent

**Context Awareness**
- Consider where the text appears (button, dialog, menu)
- Ensure translations fit the UI space
- Match the tone of the original text

**User Experience**
- Prioritize clarity over literal translation
- Use familiar terms for your target audience
- Consider cultural differences in software interaction

**Technical Accuracy**
- Don't translate technical terms that users expect in English
- Preserve software-specific terminology
- Maintain functional aspects (like file extensions)

## 🔧 Advanced Troubleshooting

### Common Issues

**XML Syntax Errors**
```
Error: XML parse error at line 45
```
**Solution**: Check for:
- Unclosed tags: `<translation>text`
- Unescaped special characters: `<translation>Bill's file</translation>`
- Should be: `<translation>Bill&apos;s file</translation>`

**Missing Translations**
Your translations don't appear in the application.

**Solution**:
1. Ensure the TS file is saved
2. Run compile command: `python tools/translations/update_translations.py compile sv`
3. Restart the application
4. Check language selection in settings

**Text Too Long**
Your translation doesn't fit in the UI.

**Solution**:
- Use shorter synonyms
- Abbreviate where appropriate
- Check the UI element context
- Consider redesigning long phrases

**Placeholder Issues**
Variables like `{filename}` don't work.

**Solution**:
- Ensure exact placeholder spelling: `{filename}`, not `{file_name}`
- Check for extra spaces: `{ filename }` won't work
- Verify placeholder is inside translation tags

### Getting Help

**Translation Questions**
- Check existing translations in other languages for reference
- Look at the source code context in the `<location>` attribute
- Test changes in the application to see context

**Technical Issues**
- Check the project's issue tracker
- Verify your Python environment has required packages
- Ensure file permissions allow writing

**File Corruption**
If your TS file becomes corrupted:
1. Check Git history: `git checkout HEAD -- src/translations/app_sv.ts`
2. Use the extraction command to regenerate: `python tools/translations/update_translations.py extract sv`
3. Reapply your translations

### Validation Commands

**Check XML Syntax**
```bash
# Linux/Mac
xmllint --noout src/translations/app_sv.ts

# Windows (if available)
# Or use online XML validators
```

**Test Compilation**
```bash
python tools/translations/update_translations.py compile sv
```
If this fails, there's likely an XML syntax error.

**Compare with Reference**
```bash
# Show differences from last commit
git diff src/translations/app_sv.ts

# Compare with English reference
# (manual comparison recommended)
```

## 📚 Additional Resources

### Qt Documentation
- [Qt Linguist Manual](https://doc.qt.io/qt-6/qtlinguist-index.html)
- [Qt Internationalization](https://doc.qt.io/qt-6/internationalization.html)

### Translation Tools
- [Qt Linguist](https://doc.qt.io/qt-6/qtlinguist-linguist.html) - Official Qt translation tool
- [Poedit](https://poedit.net/) - General translation editor (with TS support)
- [OmegaT](https://omegat.org/) - Open source translation memory tool

### Language Resources
- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
- [Unicode Character Reference](https://unicode-table.com/)
- [XML Entity Reference](https://www.w3.org/TR/xml-entity-names/)

### Project Specific
- [User Manual](user-manual.md) - Understanding the application
- [Developer Documentation](developer-docs.md) - Technical details
- [Contributing Guidelines](../CONTRIBUTING.md) - How to contribute

---

*Thank you for contributing to the TextureAtlas Toolbox translations! Your work helps make the software accessible to users worldwide.*
