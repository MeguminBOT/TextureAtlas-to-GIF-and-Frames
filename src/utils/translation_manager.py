#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from PySide6.QtCore import QTranslator, QLocale, QCoreApplication
from PySide6.QtWidgets import QApplication


class TranslationManager:
    """
    Manages application translations and language switching.
    """

    def __init__(self, app_instance=None):
        self.app_instance = app_instance or QApplication.instance()
        self.current_translator = None
        self.current_locale = None

        # Get the translations directory path
        self.translations_dir = Path(__file__).parent.parent / "translations"

        # Available languages (language_code: display_name)
        self.available_languages = {
            "en": "English",
            "sv": "Svenska",
        }

    def get_available_languages(self):
        """
        Returns a dictionary of available languages.
        Only returns languages that have translation files available.
        """
        available = {"en": "English"}  # English is always available (default)

        # Language codes to check for
        language_codes = ["sv", "es", "fr", "de", "ja", "zh"]
        language_names = {
            "sv": "Svenska",
            "es": "Español", 
            "fr": "Français",
            "de": "Deutsch",
            "ja": "日本語",
            "zh": "中文"
        }

        for lang_code in language_codes:
            # Check for unified translation files (app_XX format)
            patterns = [
                f"app_{lang_code}.ts",
                f"app_{lang_code}.qm",
                f"textureAtlas_{lang_code}.ts",  # Legacy support
                f"textureAtlas_{lang_code}.qm"   # Legacy support
            ]
            
            # If any pattern exists, the language is available
            if any((self.translations_dir / pattern).exists() for pattern in patterns):
                available[lang_code] = language_names.get(lang_code, lang_code.upper())

        return available

    def get_system_locale(self):
        """
        Get the system's default locale language code.
        """
        system_locale = QLocale.system()
        language_code = system_locale.name()

        # Convert from Qt locale format (e.g., "en_US") to our format (e.g., "en")
        if "_" in language_code:
            base_lang = language_code.split("_")[0]
            # Handle special cases like Chinese
            if base_lang == "zh":
                if "CN" in language_code or "Hans" in language_code:
                    return "zh_CN"
                elif "TW" in language_code or "Hant" in language_code:
                    return "zh_TW"
            return base_lang

        return language_code

    def load_translation(self, language_code):
        """
        Load translation for the specified language code.

        Args:
            language_code (str): Language code (e.g., 'en', 'es', 'fr')

        Returns:
            bool: True if translation was loaded successfully, False otherwise
        """
        # Remove current translator if exists
        if self.current_translator:
            self.app_instance.removeTranslator(self.current_translator)
            self.current_translator = None

        # If requesting English, no translation file needed (it's the source language)
        if language_code == "en":
            self.current_locale = "en"
            return True

        # Create new translator
        translator = QTranslator()

        # Try to load the unified .qm file first (compiled translation)
        qm_file = self.translations_dir / f"app_{language_code}.qm"
        if qm_file.exists():
            if translator.load(str(qm_file)):
                self.app_instance.installTranslator(translator)
                self.current_translator = translator
                self.current_locale = language_code
                return True

        # Fallback: Try legacy naming scheme for existing translations
        legacy_qm_file = self.translations_dir / f"textureAtlas_{language_code}.qm"
        if legacy_qm_file.exists():
            if translator.load(str(legacy_qm_file)):
                self.app_instance.installTranslator(translator)
                self.current_translator = translator
                self.current_locale = language_code
                return True

        # If .qm file not found, try .ts file (source translation)
        ts_file = self.translations_dir / f"app_{language_code}.ts"
        if ts_file.exists():
            if translator.load(str(ts_file)):
                self.app_instance.installTranslator(translator)
                self.current_translator = translator
                self.current_locale = language_code
                return True

        # Fallback: Try legacy .ts file
        legacy_ts_file = self.translations_dir / f"textureAtlas_{language_code}.ts"
        if legacy_ts_file.exists():
            if translator.load(str(legacy_ts_file)):
                self.app_instance.installTranslator(translator)
                self.current_translator = translator
                self.current_locale = language_code
                return True

        print(f"Warning: Could not load translation for language '{language_code}'")
        return False

    def get_current_language(self):
        """
        Get the currently active language code.
        """
        return self.current_locale or "en"

    def refresh_ui(self, main_window):
        """
        Refresh the UI to apply new translations.
        This should be called after changing languages.

        Args:
            main_window: The main application window instance
        """
        if hasattr(main_window, "ui"):
            # Retranslate the UI
            main_window.ui.retranslateUi(main_window)

        # Emit language changed event if the main window supports it
        if hasattr(main_window, "language_changed"):
            main_window.language_changed.emit(self.current_locale or "en")


# Convenience function to get translation manager instance
_translation_manager = None


def get_translation_manager():
    """
    Get the global translation manager instance.
    """
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def tr(text, context=None):
    """
    Convenience function for translating text.

    Args:
        text (str): Text to translate
        context (str, optional): Translation context for disambiguation

    Returns:
        str: Translated text
    """
    if context:
        return QCoreApplication.translate(context, text)
    else:
        return QCoreApplication.translate("", text)
