"""Application translation and localization management.

Provides dynamic discovery of available translations, language switching,
and quality metadata for each supported language. Translation files use
Qt's `.qm` (compiled) and `.ts` (source) formats located in
``src/translations/`` with the naming scheme ``app_{language_code}``.

Quality levels:
    native: Human-reviewed by native speakers.
    community: Human-translated community contributions.
    machine: Auto-generated machine translation.
    partial: Incomplete translation with some English strings.

To add a new language, add its metadata to the ``language_info`` dict in
:meth:`TranslationManager.get_available_languages` and create the
corresponding translation files.
"""

from pathlib import Path
from PySide6.QtCore import QTranslator, QLocale, QCoreApplication
from PySide6.QtWidgets import QApplication


class TranslationManager:
    """Manages application translations and language switching.

    Handles discovery of available translation files, loading translations,
    and providing metadata about translation quality.

    Attributes:
        app_instance: The QApplication instance for translator installation.
        current_translator: Currently installed QTranslator, if any.
        current_locale: Language code of the active translation.
        translations_dir: Path to the translations directory.
    """

    def __init__(self, app_instance: QApplication | None = None) -> None:
        """Initialize the translation manager.

        Args:
            app_instance: QApplication to install translators on. Defaults to
                the current application instance.
        """

        self.app_instance = app_instance or QApplication.instance()
        self.current_translator: QTranslator | None = None
        self.current_locale: str | None = None
        self.translations_dir = Path(__file__).parent.parent / "translations"

    def get_available_languages(self) -> dict[str, dict]:
        """Return languages that have translation files available.

        Returns:
            Dictionary mapping language codes to info dicts containing:
            ``name`` (native display name), ``english_name``, and ``quality``.
        """

        available = {
            "en": {"name": "English", "english_name": "English", "quality": "native"},
            "pt_br": {
                "name": "Português (Brasil)",
                "english_name": "Portuguese (Brazil)",
                "quality": "native",
            },
            "sv": {"name": "Svenska", "english_name": "Swedish", "quality": "native"},
        }

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
            # "de": {"name": "Deutsch", "english_name": "German", "quality": "machine"},
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
            "pt_br": {
                "name": "Português (Brasil)",
                "english_name": "Portuguese (Brazil)",
                "quality": "native",
            },
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
            patterns = [f"app_{lang_code}.ts", f"app_{lang_code}.qm"]
            if any((self.translations_dir / pattern).exists() for pattern in patterns):
                available[lang_code] = lang_info

        return available

    def get_system_locale(self) -> str:
        """Get the system's default locale as a language code.

        Converts Qt locale format (e.g., ``en_US``) to the application's
        format (e.g., ``en``). Chinese locales preserve region codes to
        distinguish Simplified (``zh_CN``) from Traditional (``zh_TW``).

        Returns:
            Language code suitable for :meth:`load_translation`.
        """

        system_locale = QLocale.system()
        language_code = system_locale.name()

        if "_" in language_code:
            base_lang = language_code.split("_")[0]
            if base_lang == "zh":
                if "CN" in language_code or "Hans" in language_code:
                    return "zh_CN"
                elif "TW" in language_code or "Hant" in language_code:
                    return "zh_TW"
            return base_lang

        return language_code

    def load_translation(self, language_code: str) -> bool:
        """Load translation for the specified language code.

        Removes any existing translator, then installs the new one. The
        ``auto`` code triggers system locale detection with English fallback.
        Prefers compiled ``.qm`` files over source ``.ts`` files.

        Args:
            language_code: Language code (e.g., ``en``, ``es``, ``auto``).

        Returns:
            True if translation loaded successfully, False otherwise.
        """

        if self.current_translator:
            self.app_instance.removeTranslator(self.current_translator)
            self.current_translator = None

        if language_code == "auto":
            detected_language = self.get_system_locale()
            available_languages = self.get_available_languages()
            if detected_language in available_languages:
                language_code = detected_language
            else:
                language_code = "en"

        if language_code == "en":
            self.current_locale = "en"
            return True

        translator = QTranslator()

        qm_file = self.translations_dir / f"app_{language_code}.qm"
        if qm_file.exists():
            if translator.load(str(qm_file)):
                self.app_instance.installTranslator(translator)
                self.current_translator = translator
                self.current_locale = language_code
                return True

        ts_file = self.translations_dir / f"app_{language_code}.ts"
        if ts_file.exists():
            if translator.load(str(ts_file)):
                self.app_instance.installTranslator(translator)
                self.current_translator = translator
                self.current_locale = language_code
                return True

        print(f"Warning: Could not load translation for language '{language_code}'")
        return False

    def get_current_language(self) -> str:
        """Return the currently active language code, defaulting to ``en``."""

        return self.current_locale or "en"

    def refresh_ui(self, main_window) -> None:
        """Refresh the UI to apply the current translation.

        Call after changing languages. Invokes ``retranslateUi`` on the
        window's UI and emits the ``language_changed`` signal if present.

        Args:
            main_window: The main application window instance.
        """

        if hasattr(main_window, "ui"):
            main_window.ui.retranslateUi(main_window)

        if hasattr(main_window, "language_changed"):
            main_window.language_changed.emit(self.current_locale or "en")

    def is_machine_translated(self, language_code: str) -> bool:
        """Check if a language uses machine translation.

        Args:
            language_code: The language code to check.

        Returns:
            True if the language quality is ``machine``, False otherwise.
        """

        available_languages = self.get_available_languages()
        if language_code in available_languages:
            lang_info = available_languages[language_code]
            if isinstance(lang_info, dict):
                return lang_info.get("quality") == "machine"
        return False

    def get_quality_level(self, language_code: str) -> str:
        """Get the quality level of a translation.

        Args:
            language_code: The language code to check.

        Returns:
            Quality level (``native``, ``community``, ``machine``, ``partial``)
            or ``unknown`` if not found.
        """

        available_languages = self.get_available_languages()
        if language_code in available_languages:
            lang_info = available_languages[language_code]
            if isinstance(lang_info, dict):
                return lang_info.get("quality", "unknown")
        return "unknown"

    def get_english_name(self, language_code: str) -> str:
        """Get the English name of a language.

        Args:
            language_code: The language code to look up.

        Returns:
            English name of the language, or ``Unknown`` if not found.
        """

        available_languages = self.get_available_languages()
        if language_code in available_languages:
            lang_info = available_languages[language_code]
            if isinstance(lang_info, dict):
                return lang_info.get("english_name", "Unknown")
        return "Unknown"

    def get_display_name(self, language_code: str, show_english: bool = False) -> str:
        """Get the display name for a language.

        Args:
            language_code: The language code to look up.
            show_english: If True, append the English name (e.g.,
                ``Deutsch / German``).

        Returns:
            Display name in the native script, optionally with English.
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

    def _format_language_display_name(self, native_name: str, english_name: str) -> str:
        """Format a bilingual language display name.

        Combines native and English names with a slash separator, unless
        the English name is empty, identical, or already present in the
        native name.

        Args:
            native_name: Language name in its native script.
            english_name: Language name in English.

        Returns:
            Formatted display name (e.g., ``Français / French``).
        """

        if not english_name or english_name == native_name:
            return native_name

        if english_name.lower() in native_name.lower():
            return native_name

        return f"{native_name} / {english_name}"

    def get_machine_translation_disclaimer(self) -> tuple[str, str]:
        """Get the machine translation disclaimer in the current language.

        Returns:
            A tuple (title, message) for displaying a disclaimer dialog.
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


_translation_manager: TranslationManager | None = None


def get_translation_manager() -> TranslationManager:
    """Return the global translation manager instance, creating it if needed."""

    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def tr(text: str, context: str | None = None) -> str:
    """Translate text using the application's current locale.

    Args:
        text: Text to translate.
        context: Optional translation context for disambiguation.

    Returns:
        Translated text, or the original if no translation exists.
    """

    if context:
        return QCoreApplication.translate(context, text)
    return QCoreApplication.translate("", text)
