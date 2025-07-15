#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from PySide6.QtCore import QTranslator, QLocale, QCoreApplication
from PySide6.QtWidgets import QApplication


class TranslationManager:
    """
    Manages application translations and language switching.

    This class handles:
    - Dynamic discovery of available translation files
    - Loading and switching between language translations
    - Managing Qt translators and locale settings
    - Providing translation quality information (native vs machine-translated)

    LANGUAGE SYSTEM OVERVIEW:
    ------------------------
    The translation system works with two main components:

    1. Language Information Dictionary:
       Each language is defined with metadata including:
       - name: Display name in the language's native script
       - machine_translated: Boolean indicating if auto-translated
       - quality: "native" for high quality, "community" for good human translations,
                 "machine" for auto-generated translations, "partial" for incomplete translations

    2. Translation Files:
       Located in src/translations/ directory:
       - app_{language_code}.ts: Source translation files (XML format)
       - app_{language_code}.qm: Compiled translation files (binary format)

    SUPPORTED FILE FORMATS:
    ----------------------
    - .ts files: Qt Linguist source files (human-readable XML)
    - .qm files: Compiled Qt translation files (binary, faster loading)

    The system automatically prioritizes .qm files over .ts files for performance,
    using the standardized app_{language_code} naming scheme.

    ADDING NEW LANGUAGES:
    --------------------
    1. Add language info to the language_info dict in get_available_languages()
    2. Create translation files: app_{language_code}.ts and/or app_{language_code}.qm
    3. The language will automatically appear in the UI if files are found

    Example:
        # Add Italian support
        "it": {"name": "Italiano", "machine_translated": False, "quality": "native"}

        # Create files: src/translations/app_it.ts or app_it.qm
    """

    def __init__(self, app_instance=None):
        self.app_instance = app_instance or QApplication.instance()
        self.current_translator = None
        self.current_locale = None

        # Get the translations directory path
        self.translations_dir = Path(__file__).parent.parent / "translations"

    def get_available_languages(self):
        """
        Returns a dictionary of available languages.
        Only returns languages that have translation files available.

        Returns:
            dict: Dictionary mapping language codes to language information dictionaries.
                  Each language info dict contains:
                  - name (str): Display name of the language in its native script
                  - english_name (str): English name of the language
                  - quality (str): Translation quality ("native", "community", "machine", "partial")
        """
        available = {
            "en": {"name": "English", "english_name": "English", "quality": "native"},
            "pt_br": {"name": "Português (Brasil)", "english_name": "Portuguese (Brazil)", "quality": "native"},
            "sv": {"name": "Svenska", "english_name": "Swedish", "quality": "native"},
        }

        # Language codes to check for with their quality information
        #
        # LANGUAGE DICTIONARY STRUCTURE:
        # Each entry follows this format:
        # "language_code": {
        #     "name": "Language Name in Native Script",
        #     "english_name": "English Name",
        #     "quality": str  # Quality level
        # }
        #
        # QUALITY LEVELS:
        # - "native": Near perfect quality (human-reviewed, native speakers)
        # - "community": Good quality community contributions (human-translated)
        # - "machine": Machine translated (auto-generated)
        # - "partial": Incomplete translation (some strings still in English)
        #
        # EXAMPLES:
        # "de": {"name": "Deutsch", "english_name": "German", "quality": "community"}
        # "fr": {"name": "Français", "english_name": "French", "quality": "machine"}
        # "es": {"name": "Español", "english_name": "Spanish", "quality": "partial"}
        #
        # ADDING NEW LANGUAGES:
        # 1. Add the language code and info to this dictionary
        # 2. Create translation files in src/translations/ directory:
        #    - app_{language_code}.ts (source translation file)
        #    - app_{language_code}.qm (compiled translation file)
        # 3. The language will automatically appear in the UI if translation files exist
        #
        # LANGUAGE CODE STANDARDS:
        # - Use ISO 639-1 two-letter codes for most languages (e.g., "en", "fr", "de")
        # - For Chinese, use region-specific codes: "zh_CN" (Simplified), "zh_TW" (Traditional)
        # - Keep codes lowercase for consistency

        # If a language is commented out, it's not currently supported and needs to be translated first.
        language_info = {
            # "ar": {"name": "العربية", "english_name": "Arabic", "quality": "machine"},
            # "bg": {"name": "Български", "english_name": "Bulgarian", "quality": "machine"},
            # "zh_CN": {"name": "简体中文", "english_name": "Chinese (Simplified)", "quality": "machine"},
            # "zh_TW": {"name": "繁體中文", "english_name": "Chinese (Traditional)", "quality": "machine"},
            # "hr": {"name": "Hrvatski", "english_name": "Croatian", "quality": "machine"},
            # "cs": {"name": "Čeština", "english_name": "Czech", "quality": "machine"},
            "da": {"name": "Dansk", "english_name": "Danish", "quality": "machine"},
            # "nl": {"name": "Nederlands", "english_name": "Dutch", "quality": "machine"},
            # "en": {"name": "English", "english_name": "English", "quality": "machine"},
            # "et": {"name": "Eesti", "english_name": "Estonian", "quality": "machine"},
            # "fi": {"name": "Suomi", "english_name": "Finnish", "quality": "machine"},
            # "fr": {"name": "Français", "english_name": "French", "quality": "machine"},
            # "fr_CA": {"name": "Français canadien", "english_name": "French (Canadian)",
            #"de": {"name": "Deutsch", "english_name": "German", "quality": "machine"},
            # "el": {"name": "Ελληνικά", "english_name": "Greek", "quality": "machine"},
            # "he": {"name": "עברית", "english_name": "Hebrew", "quality": "machine"},
            # "hi": {"name": "हिन्दी", "english_name": "Hindi", "quality": "machine"},
            # "hu": {"name": "Magyar", "english_name": "Hungarian", "quality": "machine"},
            # "is": {"name": "Íslenska", "english_name": "Icelandic", "quality": "machine"},
            # "it": {"name": "Italiano", "english_name": "Italian", "quality": "machine"},
            # "ja": {"name": "日本語", "english_name": "Japanese", "quality": "machine"},
            # "ko": {"name": "한국어", "english_name": "Korean", "quality": "machine"},
            # "lv": {"name": "Latviešu", "english_name": "Latvian", "quality": "machine"},
            # "lt": {"name": "Lietuvių", "english_name": "Lithuanian", "quality": "machine"},
            # "no": {"name": "Norsk bokmål", "english_name": "Norwegian (Bokmål)", "quality": "machine"},
            # "nn": {"name": "Norsk nynorsk", "english_name": "Norwegian (Nynorsk)", "quality": "machine"},
            # "pl": {"name": "Polski", "english_name": "Polish", "quality": "machine"},
            # "pt": {"name": "Português", "english_name": "Portuguese", "quality": "machine"},
            "pt_br": {"name": "Português (Brasil)", "english_name": "Portuguese (Brazil)", "quality": "native"},
            # "ro": {"name": "Română", "english_name": "Romanian", "quality": "machine"},
            # "ru": {"name": "Русский", "english_name": "Russian", "quality": "machine"},
            # "sk": {"name": "Slovenčina", "english_name": "Slovak", "quality": "machine"},
            # "sl": {"name": "Slovenščina", "english_name": "Slovenian", "quality": "machine"},
            "sv": {"name": "Svenska", "english_name": "Swedish", "quality": "native"},
            # "es": {"name": "Español", "english_name": "Spanish", "quality": "machine"},
            # "th": {"name": "ไทย", "english_name": "Thai", "quality": "machine"},
            # "tr": {"name": "Türkçe", "english_name": "Turkish", "quality": "machine"},
            # "uk": {"name": "Українська", "english_name": "Ukrainian", "quality": "machine"},
            # "vi": {"name": "Tiếng Việt", "english_name": "Vietnamese", "quality": "machine"},
        }

        for lang_code, lang_info in language_info.items():
            # Check for translation files using the standardized app_XX format
            # The system looks for both source (.ts) and compiled (.qm) files
            patterns = [
                f"app_{lang_code}.ts",  # Source translation file
                f"app_{lang_code}.qm",  # Compiled translation file
            ]

            # If any translation file pattern exists, the language is considered available
            # This allows for partial translations or mixed file formats
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
            # Handle special cases like Chinese where region matters for script selection
            # zh_CN/zh_Hans = Simplified Chinese (Mainland China)
            # zh_TW/zh_Hant = Traditional Chinese (Taiwan, Hong Kong)
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
            language_code (str): Language code (e.g., 'en', 'es', 'fr', 'auto')

        Returns:
            bool: True if translation was loaded successfully, False otherwise
        """
        if self.current_translator:
            self.app_instance.removeTranslator(self.current_translator)
            self.current_translator = None

        # Handle auto-detection
        if language_code == "auto":
            detected_language = self.get_system_locale()
            available_languages = self.get_available_languages()

            # If detected language is available, use it
            if detected_language in available_languages:
                language_code = detected_language
            else:
                # Fall back to English if system language is not available
                language_code = "en"

        if language_code == "en":
            self.current_locale = "en"
            return True

        translator = QTranslator()

        # Try to load the .qm file first (compiled translation)
        qm_file = self.translations_dir / f"app_{language_code}.qm"
        if qm_file.exists():
            if translator.load(str(qm_file)):
                self.app_instance.installTranslator(translator)
                self.current_translator = translator
                self.current_locale = language_code
                return True

        # Fallback to .ts file (source translation)
        ts_file = self.translations_dir / f"app_{language_code}.ts"
        if ts_file.exists():
            if translator.load(str(ts_file)):
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
            main_window.ui.retranslateUi(main_window)

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
                return lang_info.get("quality") == "machine"
        return False

    def get_quality_level(self, language_code):
        """
        Get the quality level of a translation.

        Args:
            language_code (str): The language code to check

        Returns:
            str: Quality level ("native", "community", "machine", "partial") or "unknown"
        """
        available_languages = self.get_available_languages()
        if language_code in available_languages:
            lang_info = available_languages[language_code]
            if isinstance(lang_info, dict):
                return lang_info.get("quality", "unknown")
        return "unknown"

    def get_english_name(self, language_code):
        """
        Get the English name of a language.

        Args:
            language_code (str): The language code to check

        Returns:
            str: English name of the language or "Unknown"
        """
        available_languages = self.get_available_languages()
        if language_code in available_languages:
            lang_info = available_languages[language_code]
            if isinstance(lang_info, dict):
                return lang_info.get("english_name", "Unknown")
        return "Unknown"

    def get_display_name(self, language_code, show_english=False):
        """
        Get the display name for a language, optionally including English name.

        Args:
            language_code (str): The language code to check
            show_english (bool): Whether to include English name in parentheses

        Returns:
            str: Display name (e.g., "Deutsch" or "Deutsch (German)")
        """
        available_languages = self.get_available_languages()
        if language_code in available_languages:
            lang_info = available_languages[language_code]
            if isinstance(lang_info, dict):
                native_name = lang_info.get("name", "Unknown")
                if show_english and language_code != "en":
                    english_name = lang_info.get("english_name", "Unknown")
                    return self._format_language_display_name(native_name, english_name)
                return native_name
        return "Unknown"

    def _format_language_display_name(self, native_name, english_name):
        """
        Format a language display name, handling existing parentheses smartly.

        Args:
            native_name (str): Native language name (may contain parentheses)
            english_name (str): English language name

        Returns:
            str: Properly formatted display name
        """
        if not english_name or english_name == native_name:
            return native_name

        # Check if native name already contains the English name
        if english_name.lower() in native_name.lower():
            return native_name

        # Always use forward slash for consistency
        return f"{native_name} / {english_name}"

    def get_machine_translation_disclaimer(self):
        """
        Get the machine translation disclaimer text in the current language.

        Returns:
            tuple: (title, message) for the disclaimer dialog
        """

        title = QCoreApplication.translate(
            "MachineTranslationDisclaimer", "Machine Translation Notice"
        )
        message = QCoreApplication.translate(
            "MachineTranslationDisclaimer",
            "This language was automatically translated and may contain inaccuracies. "
            "If you would like to contribute better translations, please visit our GitHub repository.",
        )
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
