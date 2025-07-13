# Translation Management - Quick Reference

## 🚀 Quick Commands

**Windows (PowerShell):**
```bash
.\translate.bat status                    # Show all language status
.\translate.bat status sv en              # Show Swedish and English only
.\translate.bat extract                   # Extract strings for all languages
.\translate.bat extract sv                # Extract strings for Swedish only
.\translate.bat compile sv es             # Compile Swedish and Spanish
.\translate.bat all sv                    # Full cycle for Swedish only
```

**Cross-platform:**
```bash
# Process all languages (default)
python tools/translations/update_translations.py status
python tools/translations/update_translations.py extract
python tools/translations/update_translations.py compile

# Process specific languages
python tools/translations/update_translations.py status sv en es
python tools/translations/update_translations.py extract sv
python tools/translations/update_translations.py compile sv es fr
python tools/translations/update_translations.py all sv
```

## 📁 File Locations

- **Translation files**: `src/translations/` (`.ts` and `.qm` files)
- **Management tools**: `tools/translations/` (Python scripts)
- **Documentation**: `tools/translations/README.md` (detailed docs)

## 🎯 Quick Workflow

1. **Add strings to code**: `self.tr("New text")`
2. **Extract**: `.\translate.bat extract` (all languages) or `.\translate.bat extract sv` (Swedish only)
3. **Edit translations**: Modify `.ts` files in `src/translations/`
4. **Compile**: `.\translate.bat compile` (all) or `.\translate.bat compile sv` (Swedish only)
5. **Test**: Run application and test language switching

## 💡 Pro Tips

- **Work on specific languages**: `.\translate.bat extract sv en` to update only Swedish and English
- **Check progress**: `.\translate.bat status sv` to see Swedish translation completion
- **Quick compile**: `.\translate.bat compile sv` to compile only the language you're working on
- **Bulk operations**: `.\translate.bat all sv` to do full cycle for Swedish only

## 📊 Current Status

- 🇺🇸 English: Template (192 strings)
- 🇸🇪 Swedish: 65% complete (125/192)
- 🇪🇸 Spanish: 5% complete
- 🇫🇷 French: 5% complete
- 🇩🇪 German: Template
- 🇯🇵 Japanese: Template
- 🇨🇳 Chinese: Template

See `tools/translations/README.md` for detailed documentation.
