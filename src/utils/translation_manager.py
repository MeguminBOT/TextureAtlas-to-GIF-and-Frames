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

        # Available languages with quality information
        self.available_languages = {
            "en": {"name": "English", "machine_translated": False, "quality": "native"},
            "sv": {"name": "Svenska", "machine_translated": False, "quality": "manual"},
        }

    def get_available_languages(self):
        """
        Returns a dictionary of available languages.
        Only returns languages that have translation files available.
        """
        available = {"en": {"name": "English", "machine_translated": False, "quality": "native"}}  # English is always available (default)

        # Language codes to check for with their quality information
        language_info = {
            "sv": {"name": "Svenska", "machine_translated": False, "quality": "manual"},
            "es": {"name": "Español", "machine_translated": True, "quality": "machine"}, 
            "fr": {"name": "Français", "machine_translated": True, "quality": "machine"},
            "de": {"name": "Deutsch", "machine_translated": True, "quality": "machine"},
            "ja": {"name": "日本語", "machine_translated": True, "quality": "machine"},
            "zh": {"name": "中文", "machine_translated": True, "quality": "machine"}
        }

        for lang_code, lang_info in language_info.items():
            # Check for unified translation files (app_XX format)
            patterns = [
                f"app_{lang_code}.ts",
                f"app_{lang_code}.qm",
                f"textureAtlas_{lang_code}.ts",  # Legacy support
                f"textureAtlas_{lang_code}.qm"   # Legacy support
            ]
            
            # If any pattern exists, the language is available
            if any((self.translations_dir / pattern).exists() for pattern in patterns):
                available[lang_code] = lang_info

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

    def is_machine_translated(self, language_code):
        """
        Check if a language is machine translated.
        
        Args:
            language_code (str): The language code to check
            
        Returns:
            bool: True if the language is machine translated, False otherwise
        """
        available_languages = self.get_available_languages()
        if language_code in available_languages:
            lang_info = available_languages[language_code]
            if isinstance(lang_info, dict):
                return lang_info.get("machine_translated", False)
        return False
    
    def get_machine_translation_disclaimer(self):
        """
        Get the machine translation disclaimer text in the current language.
        
        Returns:
            tuple: (title, message) for the disclaimer dialog
        """
        # These will be translated by the Qt translation system
        title = QCoreApplication.translate("MachineTranslationDisclaimer", "Machine Translation Notice")
        message = QCoreApplication.translate("MachineTranslationDisclaimer", 
            "This language was automatically translated and may contain inaccuracies. "
            "If you would like to contribute better translations, please visit our GitHub repository.")
        return title, message


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
