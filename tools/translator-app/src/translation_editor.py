#!/usr/bin/env python3
"""
Translation Editor - A Qt-based GUI for editing translation files

This tool was created to make it easier for users to contribute translations
to the "TextureAtlas Toolbox" project, even if they don't know how to code
or don't want to install development tools like Qt Linguist,
or being overwhelmed by the sheer amount of text if opened with a text editor.

It provides a clean, user-friendly interface with features like
* Smart string grouping
* Simple syntax highlighting for placeholders
* Real-time validation

Machine translation requires the optional 'requests' package and an API key:
* Set DEEPL_API_KEY for DeepL (optionally override DEEPL_API_ENDPOINT).
* Set GOOGLE_TRANSLATE_API_KEY for Google Cloud Translation API usage.

"""

import sys
import os
import re
import html
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QTextBrowser,
    QLineEdit,
    QLabel,
    QPushButton,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QScrollArea,
    QGroupBox,
    QStatusBar,
    QCheckBox,
    QComboBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QIcon

try:
    import requests
except ImportError:  # Lazy dependency for translation services
    requests = None


class PlaceholderHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for highlighting placeholders in text"""

    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.setup_formats()

    def setup_formats(self):
        """Setup text formats for highlighting"""
        self.placeholder_format = QTextCharFormat()
        if self.dark_mode:
            self.placeholder_format.setForeground(QColor(100, 200, 255))
        else:
            self.placeholder_format.setForeground(QColor(0, 100, 200))
        self.placeholder_format.setFontWeight(QFont.Bold)

    def highlightBlock(self, text):
        """Highlight placeholders in the given text block"""
        pattern = r"\{[^}]*\}"

        import re

        for match in re.finditer(pattern, text):
            start = match.start()
            length = match.end() - start
            self.setFormat(start, length, self.placeholder_format)

    def set_dark_mode(self, dark_mode):
        """Update highlighting for dark/light mode"""
        self.dark_mode = dark_mode
        self.setup_formats()
        self.rehighlight()


class TranslationItem:
    """Represents a single translation entry or group of identical entries"""

    def __init__(
        self,
        source: str,
        translation: str = "",
        context: str = "",
        filename: str = "",
        line: int = 0,
    ):
        self.source = source
        self.translation = translation or ""
        self.contexts = [context] if context else []
        self.locations = [(filename, line)] if filename else []
        self.is_translated = bool(self.translation.strip())

    def add_context(self, context: str, filename: str = "", line: int = 0):
        """Add another context that uses this same source string"""
        if context and context not in self.contexts:
            self.contexts.append(context)
        if filename and (filename, line) not in self.locations:
            self.locations.append((filename, line))

    def get_context_display(self) -> str:
        """Get formatted display of all contexts"""
        if len(self.contexts) == 1:
            return self.contexts[0]
        elif len(self.contexts) > 1:
            return f"{self.contexts[0]} (+{len(self.contexts) - 1} more)"
        else:
            return "Unknown"

    def get_all_contexts_info(self) -> str:
        """Get detailed info about all contexts and locations"""
        info_lines = []
        for i, context in enumerate(self.contexts):
            if i < len(self.locations):
                filename, line = self.locations[i]
                info_lines.append(f"Context: {context}\nFile: {filename}:{line}")
            else:
                info_lines.append(f"Context: {context}")
        return "\n\n".join(info_lines)

    @property
    def context(self) -> str:
        """Backward compatibility - returns first context"""
        return self.contexts[0] if self.contexts else ""

    @property
    def filename(self) -> str:
        """Backward compatibility - returns first filename"""
        return self.locations[0][0] if self.locations else ""

    @property
    def line(self) -> int:
        """Backward compatibility - returns first line"""
        return self.locations[0][1] if self.locations else 0

    def has_placeholders(self) -> bool:
        """Check if the source text contains format placeholders"""
        return bool(re.search(r"\{[^}]*\}", self.source))

    def get_placeholders(self) -> List[str]:
        """Extract all placeholders from source text"""
        return re.findall(r"\{[^}]*\}", self.source)

    def preview_with_placeholders(self, placeholder_values: Dict[str, str]) -> str:
        """Generate preview text with placeholder values"""
        if not self.translation:
            return ""

        preview = self.translation
        placeholders = self.get_placeholders()

        for placeholder in placeholders:
            key = placeholder.strip("{}")
            if key in placeholder_values:
                preview = preview.replace(placeholder, placeholder_values[key])
            elif placeholder in placeholder_values:
                preview = preview.replace(placeholder, placeholder_values[placeholder])
            else:
                preview = preview.replace(placeholder, f"[{key}]")

        return preview

    def validate_translation(self) -> tuple[bool, str]:
        """Validate that translation contains all required placeholders from source"""
        if not self.translation.strip():
            return True, ""

        source_placeholders = set(self.get_placeholders())
        translation_placeholders = set(re.findall(r"\{[^}]*\}", self.translation))

        missing_placeholders = source_placeholders - translation_placeholders
        extra_placeholders = translation_placeholders - source_placeholders

        errors = []
        if missing_placeholders:
            errors.append(f"Missing placeholders: {', '.join(missing_placeholders)}")
        if extra_placeholders:
            errors.append(f"Extra placeholders: {', '.join(extra_placeholders)}")

        if errors:
            return False, "; ".join(errors)
        return True, ""


class TranslationError(Exception):
    """Raised when a machine translation request fails"""


class TranslationProvider(ABC):
    """Abstract translation provider"""

    name: str = "Translation Provider"

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Return availability flag and status message"""

    @abstractmethod
    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text and return the translated string"""


class DeepLProvider(TranslationProvider):
    """DeepL translation provider"""

    name = "DeepL"
    _SUPPORTED_CODES = {
        "BG",
        "CS",
        "DA",
        "DE",
        "EL",
        "EN",
        "ES",
        "ET",
        "FI",
        "FR",
        "HU",
        "ID",
        "IT",
        "JA",
        "KO",
        "LT",
        "LV",
        "NB",
        "NL",
        "PL",
        "PT",
        "RO",
        "RU",
        "SK",
        "SL",
        "SV",
        "TR",
        "UK",
        "ZH",
    }

    def __init__(self):
        self._endpoint = os.environ.get(
            "DEEPL_API_ENDPOINT", "https://api-free.deepl.com/v2/translate"
        )

    @staticmethod
    def _api_key() -> Optional[str]:
        return os.environ.get("DEEPL_API_KEY")

    def is_available(self) -> tuple[bool, str]:
        if requests is None:
            return False, "Install the 'requests' package to enable machine translation."
        if not self._api_key():
            return False, "Set the DEEPL_API_KEY environment variable to enable DeepL."
        return True, "DeepL ready"

    def _map_language(self, code: Optional[str], *, is_target: bool) -> Optional[str]:
        if not code:
            return None
        normalized = code.upper()

        if normalized not in self._SUPPORTED_CODES and normalized not in {
            "EN-US",
            "EN-GB",
            "PT-BR",
            "PT-PT",
        }:
            raise TranslationError(f"DeepL does not support the language code '{code}'.")

        if normalized == "EN" and is_target:
            return os.environ.get("DEEPL_TARGET_EN_VARIANT", "EN-US").upper()
        if normalized == "PT" and is_target:
            return os.environ.get("DEEPL_TARGET_PT_VARIANT", "PT-BR").upper()
        if normalized == "EN" and not is_target:
            return "EN"
        if normalized == "PT" and not is_target:
            return "PT"
        return normalized

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        if not text.strip():
            return ""
        api_key = self._api_key()
        if not api_key:
            raise TranslationError("DEEPL_API_KEY is not configured.")
        if requests is None:
            raise TranslationError("The 'requests' package is required for DeepL translations.")

        mapped_target = self._map_language(target_lang, is_target=True)
        mapped_source = self._map_language(source_lang, is_target=False)

        payload = {"text": text, "target_lang": mapped_target}
        if mapped_source:
            payload["source_lang"] = mapped_source

        headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}

        try:
            response = requests.post(self._endpoint, data=payload, headers=headers, timeout=15)
        except Exception as exc:  # pragma: no cover - network error surface to user
            raise TranslationError(f"DeepL request failed: {exc}") from exc

        if response.status_code >= 400:
            raise TranslationError(f"DeepL error {response.status_code}: {response.text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationError("Failed to decode DeepL response.") from exc

        translations = data.get("translations") or []
        if not translations:
            raise TranslationError("DeepL returned no translation result.")

        return translations[0].get("text", "")


class GoogleTranslateProvider(TranslationProvider):
    """Google Cloud Translation API provider"""

    name = "Google Translate"
    _ENDPOINT = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self):
        self._supported_codes = {
            "EN",
            "ES",
            "DE",
            "FR",
            "IT",
            "JA",
            "KO",
            "PL",
            "PT",
            "RU",
            "TR",
            "ZH",
        }

    @staticmethod
    def _api_key() -> Optional[str]:
        return os.environ.get("GOOGLE_TRANSLATE_API_KEY")

    def is_available(self) -> tuple[bool, str]:
        if requests is None:
            return False, "Install the 'requests' package to enable machine translation."
        if not self._api_key():
            return False, "Set GOOGLE_TRANSLATE_API_KEY to enable Google Translate."
        return True, "Google Translate ready"

    def _map_language(self, code: Optional[str]) -> Optional[str]:
        if not code:
            return None
        normalized = code.upper()
        if normalized not in self._supported_codes:
            raise TranslationError(f"Google Translate does not support '{code}'.")
        return normalized.lower()

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        if not text.strip():
            return ""
        api_key = self._api_key()
        if not api_key:
            raise TranslationError("GOOGLE_TRANSLATE_API_KEY is not configured.")
        if requests is None:
            raise TranslationError("The 'requests' package is required for Google Translate.")

        mapped_target = self._map_language(target_lang)
        mapped_source = self._map_language(source_lang)

        payload = {
            "q": text,
            "target": mapped_target,
            "format": "text",
        }
        if mapped_source:
            payload["source"] = mapped_source

        params = {"key": api_key}

        try:
            response = requests.post(self._ENDPOINT, params=params, json=payload, timeout=15)
        except Exception as exc:  # pragma: no cover - network issues surface to user
            raise TranslationError(f"Google Translate request failed: {exc}") from exc

        if response.status_code >= 400:
            raise TranslationError(
                f"Google Translate error {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationError("Failed to decode Google Translate response.") from exc

        translations = data.get("data", {}).get("translations") or []
        if not translations:
            raise TranslationError("Google Translate returned no translation result.")

        translated_text = translations[0].get("translatedText", "")
        return html.unescape(translated_text)


class LibreTranslateProvider(TranslationProvider):
    """LibreTranslate self-hosted translation provider"""

    name = "LibreTranslate"

    def __init__(self):
        self._endpoint = os.environ.get(
            "LIBRETRANSLATE_ENDPOINT", "http://127.0.0.1:5000/translate"
        )
        self._api_key = os.environ.get("LIBRETRANSLATE_API_KEY")

    def _map_language(self, code: Optional[str], *, is_target: bool) -> str:
        if not code:
            return "auto" if not is_target else "en"
        return code.lower()

    def is_available(self) -> tuple[bool, str]:
        if requests is None:
            return False, "Install the 'requests' package to enable machine translation."
        return True, f"Endpoint: {self._endpoint}"

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        if not text.strip():
            return ""
        if requests is None:
            raise TranslationError("The 'requests' package is required for LibreTranslate.")

        mapped_target = self._map_language(target_lang, is_target=True)
        mapped_source = self._map_language(source_lang, is_target=False)

        payload = {
            "q": text,
            "source": mapped_source,
            "target": mapped_target,
            "format": "text",
        }
        if self._api_key:
            payload["api_key"] = self._api_key

        try:
            response = requests.post(self._endpoint, data=payload, timeout=15)
        except Exception as exc:
            raise TranslationError(f"LibreTranslate request failed: {exc}") from exc

        if response.status_code >= 400:
            raise TranslationError(f"LibreTranslate error {response.status_code}: {response.text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationError("Failed to decode LibreTranslate response.") from exc

        if "error" in data:
            raise TranslationError(f"LibreTranslate error: {data['error']}")

        translated_text = data.get("translatedText", "")
        return translated_text


class TranslationManager:
    """Coordinates translation providers and helper utilities"""

    LANGUAGE_CHOICES = [
        ("EN", "English"),
        ("ES", "Spanish"),
        ("DE", "German"),
        ("FR", "French"),
        ("IT", "Italian"),
        ("JA", "Japanese"),
        ("KO", "Korean"),
        ("PL", "Polish"),
        ("PT", "Portuguese"),
        ("RU", "Russian"),
        ("TR", "Turkish"),
        ("ZH", "Chinese"),
    ]

    def __init__(self):
        """Set up the available providers and reusable helper state."""
        self.providers: Dict[str, TranslationProvider] = {
            "deepl": DeepLProvider(),
            "google": GoogleTranslateProvider(),
            "libretranslate": LibreTranslateProvider(),
        }

    def get_provider_name(self, key: Optional[str]) -> str:
        """Return a display name for a provider key, defaulting to human text."""
        if not key:
            return "Manual"
        provider = self.providers.get(key)
        return provider.name if provider else "Unknown"

    def is_provider_available(self, key: Optional[str]) -> tuple[bool, str]:
        """Report whether the requested provider can be used right now."""
        if not key:
            return False, "Machine translation disabled."
        provider = self.providers.get(key)
        if not provider:
            return False, "Selected provider is not available."
        return provider.is_available()

    def translate(
        self,
        provider_key: str,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> str:
        """Delegate translation work to the provider after availability checks."""
        provider = self.providers.get(provider_key)
        if not provider:
            raise TranslationError("Selected translation provider is not supported.")
        available, reason = provider.is_available()
        if not available:
            raise TranslationError(reason)
        return provider.translate(text, target_lang, source_lang)

    @staticmethod
    def protect_placeholders(text: str) -> tuple[str, Dict[str, str]]:
        """Replace placeholders with ASCII tokens that providers leave untouched"""
        mapping: Dict[str, str] = {}

        def repl(match):
            token = f"PH{len(mapping)}{uuid.uuid4().hex[:8].upper()}"
            mapping[token] = match.group(0)
            return token

        protected_text = re.sub(r"\{[^}]*\}", repl, text)
        return protected_text, mapping

    @staticmethod
    def restore_placeholders(text: str, mapping: Dict[str, str]) -> str:
        """Swap placeholder tokens back to their original brace-wrapped text."""
        restored = text
        for token, original in mapping.items():
            restored = restored.replace(token, original)
        return restored


class TranslationEditor(QMainWindow):
    """Main translation editor window"""

    def __init__(self):
        """Initialize the editor window, widgets, and theme defaults."""
        super().__init__()
        self.current_file = None
        self.translations: List[TranslationItem] = []
        self.current_item: Optional[TranslationItem] = None
        self.is_modified = False
        self.dark_mode = False
        self.translation_manager = TranslationManager()
        self.selected_provider_key: Optional[str] = None
        self.source_lang_combo = None
        self.target_lang_combo = None
        self.provider_combo = None
        self.translate_btn = None
        self.auto_translate_all_btn = None
        self.provider_status_label = None

        self.source_highlighter = None
        self.translation_highlighter = None

        self.init_ui()
        self.setup_connections()
        self.apply_theme()

    @staticmethod
    def _find_asset(relative_path: str) -> Optional[Path]:
        """Locate an asset path starting from common project roots"""
        script_path = Path(__file__).resolve()
        candidates = [Path.cwd()]
        candidates.extend(list(script_path.parents)[:4])
        checked: Set[Path] = set()
        for base in candidates:
            if base is None:
                continue
            candidate = (base / relative_path).resolve()
            if candidate in checked:
                continue
            checked.add(candidate)
            if candidate.exists():
                return candidate
        return None

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Translation Editor - TextureAtlas Toolbox")
        self.setGeometry(100, 100, 1200, 800)

        icon_path = self._find_asset("assets/icon-ts.ico")
        icon_set = False

        if icon_path and icon_path.exists():
            try:
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    self.setWindowIcon(icon)
                    icon_set = True
            except Exception:
                pass

        if not icon_set:
            png_icon_path = self._find_asset("assets/icon-ts.png")
            if png_icon_path and png_icon_path.exists():
                try:
                    icon = QIcon(str(png_icon_path))
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                except Exception:
                    pass

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        self.create_left_panel(splitter)

        self.create_right_panel(splitter)

        splitter.setSizes([360, 840])

        self.create_menu_bar()
        self.create_toolbar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Open a .ts file to start editing")

    def create_left_panel(self, parent):
        """Create the left panel with translation list"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search translations...")
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        left_layout.addLayout(filter_layout)

        self.translation_list = QListWidget()
        self.translation_list.setAlternatingRowColors(True)  # Required for CSS ::alternate selector
        left_layout.addWidget(self.translation_list)

        self.stats_label = QLabel("No file loaded")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 5px;")
        left_layout.addWidget(self.stats_label)

        parent.addWidget(left_widget)

    def create_right_panel(self, parent):
        """Create the right panel with translation editor"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        source_group = QGroupBox("Source Text")
        source_layout = QVBoxLayout(source_group)
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setMaximumHeight(100)
        self.source_text.setFont(QFont("Consolas", 10))

        self.source_highlighter = PlaceholderHighlighter(
            self.source_text.document(), self.dark_mode
        )

        source_layout.addWidget(self.source_text)
        right_layout.addWidget(source_group)

        translation_group = QGroupBox("Translation")
        translation_layout = QVBoxLayout(translation_group)

        # Use a compact grid to keep controls aligned regardless of translations
        translation_controls = QGridLayout()
        translation_controls.setContentsMargins(0, 0, 0, 0)
        translation_controls.setHorizontalSpacing(12)
        translation_controls.setVerticalSpacing(6)

        self.copy_source_btn = QPushButton("Copy Source")
        self.copy_source_btn.setToolTip("Copy source text to translation field")
        self.copy_source_btn.clicked.connect(self.copy_source_to_translation)
        self.copy_source_btn.setEnabled(False)
        translation_controls.addWidget(self.copy_source_btn, 0, 0, 1, 2)

        provider_label = QLabel("Service:")
        translation_controls.addWidget(provider_label, 0, 2, alignment=Qt.AlignRight)

        self.provider_combo = QComboBox()
        self.provider_combo.setToolTip("Select a machine translation provider")
        translation_controls.addWidget(self.provider_combo, 0, 3)

        self.translate_btn = QPushButton("Auto-Translate")
        self.translate_btn.setEnabled(False)
        translation_controls.addWidget(self.translate_btn, 0, 4)

        from_label = QLabel("From:")
        translation_controls.addWidget(from_label, 1, 0, alignment=Qt.AlignRight)
        self.source_lang_combo = QComboBox()
        translation_controls.addWidget(self.source_lang_combo, 1, 1)

        to_label = QLabel("To:")
        translation_controls.addWidget(to_label, 1, 2, alignment=Qt.AlignRight)
        self.target_lang_combo = QComboBox()
        translation_controls.addWidget(self.target_lang_combo, 1, 3)

        translation_controls.setColumnStretch(1, 1)
        translation_controls.setColumnStretch(3, 1)

        translation_layout.addLayout(translation_controls)

        self.provider_status_label = QLabel(
            "Machine translation disabled. Configure an API key to enable providers."
        )
        self.provider_status_label.setWordWrap(True)
        self.provider_status_label.setStyleSheet("font-size: 11px; padding: 2px 0; color: #666666;")
        translation_layout.addWidget(self.provider_status_label)

        self.translation_text = QTextEdit()
        self.translation_text.setMaximumHeight(100)
        self.translation_text.setFont(QFont("Consolas", 10))

        self.translation_highlighter = PlaceholderHighlighter(
            self.translation_text.document(), self.dark_mode
        )

        translation_layout.addWidget(self.translation_text)
        right_layout.addWidget(translation_group)

        self.populate_language_combos()
        self.populate_provider_combo()

        self.placeholder_group = QGroupBox("Placeholder Values (for preview)")
        placeholder_layout = QVBoxLayout(self.placeholder_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.placeholder_widget = QWidget()
        self.placeholder_layout = QVBoxLayout(self.placeholder_widget)
        scroll_area.setWidget(self.placeholder_widget)

        placeholder_layout.addWidget(scroll_area)
        self.placeholder_group.setVisible(False)
        right_layout.addWidget(self.placeholder_group)

        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setFont(QFont("Consolas", 10))
        self.preview_text.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        preview_layout.addWidget(self.preview_text)
        right_layout.addWidget(preview_group)

        context_group = QGroupBox("Context Information")
        context_layout = QVBoxLayout(context_group)
        self.context_label = QLabel("No translation selected")
        self.context_label.setWordWrap(True)
        self.context_label.setStyleSheet("padding: 5px;")
        context_layout.addWidget(self.context_label)
        right_layout.addWidget(context_group)

        parent.addWidget(right_widget)

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        open_action = file_menu.addAction("Open .ts file...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)

        save_action = file_menu.addAction("Save")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)

        save_as_action = file_menu.addAction("Save As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        help_menu = menubar.addMenu("Help")

        usage_action = help_menu.addAction("Using the Translator App")
        usage_action.triggered.connect(self.show_usage_help)

        api_help_action = help_menu.addAction("Translation API Keys")
        api_help_action.triggered.connect(self.show_api_key_help)

    def show_usage_help(self):
        """Show usage instructions for the translator app"""
        html = (
            "<h3>Getting started</h3>"
            "<ol>"
            "<li>Use <strong>File &gt; Open</strong> to load a Qt <code>.ts</code> file.</li>"
            "<li>Select a source entry on the left to review and edit its translation.</li>"
            "<li>Keep placeholders such as <code>{value}</code> intact.</li>"
            "<li>Use the placeholder panel to preview strings with sample values.</li>"
            "<li>Click <em>Auto-Translate</em> or <em>Translate All Missing</em> after configuring a provider.</li>"
            "<li>Save regularly with <kbd>Ctrl</kbd>+<kbd>S</kbd> or <strong>File &gt; Save</strong>.</li>"
            "</ol>"
        )
        self.show_help_dialog("Translator App Help", html)

    def show_api_key_help(self):
        """Explain how to configure machine translation API keys"""
        html = (
            "<p>Machine translation is optional. Provide your own API key or request one from the maintainer if needed.</p>"
            "<h3>DeepL (paid subscription)</h3>"
            "<ul><li>Requires an active DeepL API plan.</li>"
            "<li>Set <code>DEEPL_API_KEY</code> (and <code>DEEPL_API_ENDPOINT</code> for Pro/custom).</li></ul>"
            "<h3>Google Cloud Translation (paid per usage)</h3>"
            "<ul><li>Requires a Google Cloud project with billing enabled.</li>"
            "<li>Set <code>GOOGLE_TRANSLATE_API_KEY</code>.</li></ul>"
            "<h3>LibreTranslate (self-hosted / free)</h3>"
            "<ul><li>Install Docker (<a href='https://docs.docker.com/desktop/setup/install/windows-install/'>Windows guide</a>) and run the official container (see <a href='https://github.com/LibreTranslate/LibreTranslate#docker'>instructions</a>).</li>"
            "<li>Set <code>LIBRETRANSLATE_ENDPOINT</code> if your container exposes a different URL (defaults to http://127.0.0.1:5000/translate).</li>"
            "<li>Set <code>LIBRETRANSLATE_API_KEY</code> only if your instance enforces a key.</li></ul>"
            "<p>Restart the app after changing environment variables so the providers can detect your keys.</p>"
        )
        self.show_help_dialog("Translation API Keys", html)

    def show_help_dialog(self, title: str, html: str):
        """Show rich-text help content with clickable links"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(html)
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.resize(520, 380)
        dialog.exec()

    def create_toolbar(self):
        """Create toolbar with main actions"""
        toolbar = self.addToolBar("Main")

        open_btn = QPushButton("Open .ts File")
        open_btn.clicked.connect(self.open_file)
        toolbar.addWidget(open_btn)

        self.save_btn = QPushButton("Save .ts File")
        self.save_btn.clicked.connect(self.save_file)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.clicked.connect(self.save_file_as)
        self.save_as_btn.setEnabled(False)
        toolbar.addWidget(self.save_as_btn)

        toolbar.addSeparator()

        self.dark_mode_checkbox = QCheckBox("Dark Mode")
        self.dark_mode_checkbox.toggled.connect(self.toggle_dark_mode)
        toolbar.addWidget(self.dark_mode_checkbox)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        self.auto_translate_all_btn = QPushButton("Translate All Missing")
        self.auto_translate_all_btn.setEnabled(False)
        self.auto_translate_all_btn.clicked.connect(self.auto_translate_all_entries)
        toolbar.addWidget(self.auto_translate_all_btn)

    def setup_connections(self):
        """Setup signal connections"""
        self.translation_list.currentItemChanged.connect(self.on_translation_selected)
        self.translation_text.textChanged.connect(self.on_translation_changed)
        self.filter_input.textChanged.connect(self.filter_translations)
        if self.provider_combo:
            self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        if self.translate_btn:
            self.translate_btn.clicked.connect(self.handle_auto_translate)

    def open_file(self):
        """Open a .ts translation file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Translation File",
            "src/translations",
            "Qt Translation Files (*.ts);;All Files (*)",
        )

        if file_path:
            self.load_ts_file(file_path)

    def load_ts_file(self, file_path: str):
        """Load translations from a .ts file"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            self.translations.clear()
            translation_groups = {}

            for context in root.findall("context"):
                context_name = context.find("name")
                context_name = context_name.text if context_name is not None else ""

                for message in context.findall("message"):
                    source_elem = message.find("source")
                    translation_elem = message.find("translation")
                    location_elem = message.find("location")

                    source = (
                        source_elem.text
                        if source_elem is not None and source_elem.text is not None
                        else ""
                    )
                    translation = (
                        translation_elem.text
                        if translation_elem is not None and translation_elem.text is not None
                        else ""
                    )

                    filename = ""
                    line = 0
                    if location_elem is not None:
                        filename = location_elem.get("filename", "")
                        line = int(location_elem.get("line", 0))

                    if source.strip():
                        if source in translation_groups:
                            existing_item = translation_groups[source]
                            existing_item.add_context(context_name, filename, line)
                            if translation.strip() and not existing_item.translation.strip():
                                existing_item.translation = translation
                                existing_item.is_translated = True
                        else:
                            item = TranslationItem(
                                source, translation, context_name, filename, line
                            )
                            translation_groups[source] = item

            self.translations = list(translation_groups.values())

            self.current_file = file_path
            self.is_modified = False
            self.update_translation_list()
            self.update_stats()
            self.save_btn.setEnabled(True)
            self.save_as_btn.setEnabled(True)

            total_entries = sum(len(item.contexts) for item in self.translations)
            grouped_msg = f"Loaded {len(self.translations)} unique translations ({total_entries} total entries) from {Path(file_path).name}"

            self.setWindowTitle(f"Translation Editor - {Path(file_path).name}")
            self.status_bar.showMessage(grouped_msg)
            if self.provider_combo:
                self.update_provider_status(self.provider_combo.currentData())

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def update_translation_list(self):
        """Update the translation list widget"""
        self.translation_list.clear()

        filter_text = self.filter_input.text().lower()

        for item in self.translations:
            if (
                filter_text
                and filter_text not in item.source.lower()
                and filter_text not in item.translation.lower()
            ):
                continue

            list_item = QListWidgetItem()

            if item.is_translated:
                status = "✅"
            else:
                status = "❌"

            group_indicator = ""
            if len(item.contexts) > 1:
                group_indicator = f" 📎{len(item.contexts)}"

            display_text = f"{status}{group_indicator} {item.source[:75]}{'...' if len(item.source) > 75 else ''}"
            list_item.setText(display_text)

            list_item.setData(Qt.UserRole, item)

            self.translation_list.addItem(list_item)

    def update_stats(self):
        """Update translation statistics"""
        total = len(self.translations)
        translated = sum(1 for item in self.translations if item.is_translated)
        percentage = (translated / total * 100) if total > 0 else 0

        self.stats_label.setText(f"Progress: {translated}/{total} ({percentage:.1f}%)")

    def on_translation_selected(self, current, previous):
        """Handle translation item selection"""
        if current is None:
            self.current_item = None
            self.clear_editor()
            return

        self.current_item = current.data(Qt.UserRole)
        self.load_translation_in_editor()

    def clear_editor(self):
        """Clear the translation editor"""
        self.source_text.clear()
        self.translation_text.clear()
        self.preview_text.clear()
        self.context_label.setText("No translation selected")
        self.placeholder_group.setVisible(False)
        self.copy_source_btn.setEnabled(False)

    def load_translation_in_editor(self):
        """Load the selected translation into the editor"""
        if not self.current_item:
            return

        self.copy_source_btn.setEnabled(True)

        self.source_text.setPlainText(self.current_item.source)

        self.translation_text.blockSignals(True)
        self.translation_text.setPlainText(self.current_item.translation)
        self.translation_text.blockSignals(False)

        if len(self.current_item.contexts) == 1:
            context_info = f"Context: {self.current_item.contexts[0]}\n"
            context_info += f"File: {self.current_item.filename}:{self.current_item.line}"
        else:
            context_info = f"Used in {len(self.current_item.contexts)} contexts:\n\n"
            context_info += self.current_item.get_all_contexts_info()

        self.context_label.setText(context_info)

        self.setup_placeholders()

        self.update_preview()

    def setup_placeholders(self):
        """Setup placeholder input fields if needed"""
        if not self.current_item or not self.current_item.has_placeholders():
            self.placeholder_group.setVisible(False)
            return

        for i in reversed(range(self.placeholder_layout.count())):
            child = self.placeholder_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        placeholders = self.current_item.get_placeholders()
        for placeholder in placeholders:
            placeholder_key = placeholder.strip("{}")

            label = QLabel(f"{placeholder}:")
            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Example value for {placeholder}")
            input_field.textChanged.connect(self.update_preview)

            if self.dark_mode:
                input_field.setStyleSheet(
                    "QLineEdit { color: #FFA500; background-color: #3a3a3a; }"
                )
            else:
                input_field.setStyleSheet(
                    "QLineEdit { color: #FF6600; background-color: #ffffff; }"
                )

            if "name" in placeholder_key.lower():
                input_field.setText("John Doe")
            elif "count" in placeholder_key.lower() or "number" in placeholder_key.lower():
                input_field.setText("42")
            elif "file" in placeholder_key.lower():
                input_field.setText("example.txt")
            elif "percent" in placeholder_key.lower():
                input_field.setText("75%")
            elif "cpu" in placeholder_key.lower():
                input_field.setText("AMD Ryzen 9 3900X 12-Core Processor")
            elif "memory" in placeholder_key.lower() or "ram" in placeholder_key.lower():
                input_field.setText("16384")
            elif "threads" in placeholder_key.lower():
                input_field.setText("24")
            else:
                input_field.setText(f"[{placeholder_key}]")

            self.placeholder_layout.addWidget(label)
            self.placeholder_layout.addWidget(input_field)

        self.placeholder_group.setVisible(True)

    def get_placeholder_values(self) -> Dict[str, str]:
        """Get current placeholder values from input fields"""
        values = {}

        for i in range(0, self.placeholder_layout.count(), 2):
            label_item = self.placeholder_layout.itemAt(i)
            input_item = self.placeholder_layout.itemAt(i + 1)

            if label_item and input_item:
                label_widget = label_item.widget()
                input_widget = input_item.widget()

                if isinstance(label_widget, QLabel) and isinstance(input_widget, QLineEdit):
                    label_text = label_widget.text().rstrip(":")
                    placeholder_key = label_text.strip("{}")

                    values[label_text] = input_widget.text()
                    values[placeholder_key] = input_widget.text()

        return values

    def populate_language_combos(self):
        """Populate language combo boxes"""
        if not self.source_lang_combo or not self.target_lang_combo:
            return

        self.source_lang_combo.blockSignals(True)
        self.target_lang_combo.blockSignals(True)

        self.source_lang_combo.clear()
        self.target_lang_combo.clear()

        self.source_lang_combo.addItem("Auto detect", None)

        for code, name in TranslationManager.LANGUAGE_CHOICES:
            label = f"{name} ({code})"
            self.source_lang_combo.addItem(label, code)
            self.target_lang_combo.addItem(label, code)

        default_index = self.target_lang_combo.findData("EN")
        if default_index >= 0:
            self.target_lang_combo.setCurrentIndex(default_index)

        self.source_lang_combo.blockSignals(False)
        self.target_lang_combo.blockSignals(False)

    def populate_provider_combo(self):
        """Populate provider combo with available providers"""
        if not self.provider_combo:
            return

        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        self.provider_combo.addItem("Manual (disabled)", None)

        for key, provider in self.translation_manager.providers.items():
            available, message = provider.is_available()
            label = provider.name
            if not available:
                label = f"{label} (setup required)"
            self.provider_combo.addItem(label, key)
            index = self.provider_combo.count() - 1
            self.provider_combo.setItemData(index, message, Qt.ToolTipRole)

        self.provider_combo.blockSignals(False)
        self.provider_combo.setCurrentIndex(0)
        self.update_provider_status(None)

    def on_provider_changed(self):
        """Handle provider combo selection"""
        provider_key = self.provider_combo.currentData() if self.provider_combo else None
        self.selected_provider_key = provider_key
        self.update_provider_status(provider_key)

    def update_provider_status(self, provider_key: Optional[str]):
        """Update provider status label and button state"""
        if not self.provider_status_label or not self.translate_btn:
            return

        if not provider_key:
            self.provider_status_label.setText(
                "Machine translation disabled. Select a provider and configure its API key to enable auto-translate."
            )
            self.translate_btn.setEnabled(False)
            if self.auto_translate_all_btn:
                self.auto_translate_all_btn.setEnabled(False)
            return

        available, message = self.translation_manager.is_provider_available(provider_key)
        provider_name = self.translation_manager.get_provider_name(provider_key)
        if available:
            self.provider_status_label.setText(f"{provider_name} ready: {message}")
            self.selected_provider_key = provider_key
        else:
            self.provider_status_label.setText(message)
            self.selected_provider_key = None

        self.translate_btn.setEnabled(available)
        if self.auto_translate_all_btn:
            self.auto_translate_all_btn.setEnabled(available and bool(self.translations))

    def handle_auto_translate(self):
        """Perform machine translation using the configured provider"""
        if not self.current_item:
            QMessageBox.information(self, "Auto-Translate", "Select a source string first.")
            return

        provider_key = self.provider_combo.currentData() if self.provider_combo else None
        if not provider_key:
            QMessageBox.information(
                self,
                "Auto-Translate",
                "Select a translation provider and configure its API key before using auto-translate.",
            )
            return

        target_lang = self.target_lang_combo.currentData() if self.target_lang_combo else None
        if not target_lang:
            QMessageBox.warning(self, "Missing Target Language", "Please select a target language.")
            return

        source_lang = self.source_lang_combo.currentData() if self.source_lang_combo else None
        source_text = self.current_item.source
        if not source_text.strip():
            QMessageBox.information(self, "Auto-Translate", "Source text is empty.")
            return

        protected_text, placeholder_map = self.translation_manager.protect_placeholders(source_text)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            translated = self.translation_manager.translate(
                provider_key,
                protected_text,
                target_lang,
                source_lang,
            )
        except TranslationError as exc:
            QMessageBox.warning(self, "Translation Failed", str(exc))
            self.status_bar.showMessage(f"Translation failed: {exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        restored = self.translation_manager.restore_placeholders(translated, placeholder_map)
        self.translation_text.setPlainText(restored)
        self.status_bar.showMessage(
            f"Translated using {self.translation_manager.get_provider_name(provider_key)}"
        )

    def auto_translate_all_entries(self):
        """Auto-translate every untranslated entry using current provider"""
        if not self.translations:
            QMessageBox.information(
                self, "Translate All Missing", "Load a translation file before running this action."
            )
            return

        provider_key = self.provider_combo.currentData() if self.provider_combo else None
        if not provider_key:
            QMessageBox.information(
                self,
                "Translate All Missing",
                "Select a translation provider and configure its API key before translating.",
            )
            return

        target_lang = self.target_lang_combo.currentData() if self.target_lang_combo else None
        if not target_lang:
            QMessageBox.warning(self, "Missing Target Language", "Please select a target language.")
            return

        source_lang = self.source_lang_combo.currentData() if self.source_lang_combo else None
        items_to_translate = [item for item in self.translations if not item.translation.strip()]

        if not items_to_translate:
            QMessageBox.information(
                self, "Translate All Missing", "Every entry already has a translation."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Translate All Missing",
            (
                "This will send all untranslated strings to the selected provider.\n\n"
                "Placeholder values may need manual review, and automatic translations may overwrite manual work.\n\n"
                "Do you want to continue?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        if self.auto_translate_all_btn:
            self.auto_translate_all_btn.setEnabled(False)
        translated_count = 0
        errors: List[str] = []

        provider_name = self.translation_manager.get_provider_name(provider_key)

        for item in items_to_translate:
            protected_text, mapping = self.translation_manager.protect_placeholders(item.source)
            try:
                translated = self.translation_manager.translate(
                    provider_key,
                    protected_text,
                    target_lang,
                    source_lang,
                )
            except TranslationError as exc:
                errors.append(f"{item.source[:40]}…: {exc}")
                continue

            restored = self.translation_manager.restore_placeholders(translated, mapping)
            item.translation = restored
            item.is_translated = bool(restored.strip())
            translated_count += 1

        QApplication.restoreOverrideCursor()
        if self.provider_combo:
            self.update_provider_status(self.provider_combo.currentData())

        if translated_count:
            self.is_modified = True
            current_row = self.translation_list.currentRow()
            self.update_translation_list()
            self.update_stats()
            if 0 <= current_row < self.translation_list.count():
                self.translation_list.setCurrentRow(current_row)
            if self.current_item:
                self.translation_text.blockSignals(True)
                self.translation_text.setPlainText(self.current_item.translation)
                self.translation_text.blockSignals(False)
            self.status_bar.showMessage(
                f"Auto-translated {translated_count} entries using {provider_name}."
            )

        if errors:
            preview = "\n".join(errors[:5])
            message = f"Completed with {len(errors)} issue(s)." + (
                "\n\n" + preview if preview else ""
            )
            QMessageBox.warning(self, "Translate All Missing", message)
        elif not translated_count:
            QMessageBox.warning(
                self,
                "Translate All Missing",
                "No entries were translated. Verify the provider configuration and try again.",
            )

    def update_preview(self):
        """Update the preview text"""
        if not self.current_item:
            self.preview_text.clear()
            return

        placeholder_values = self.get_placeholder_values()
        preview = self.current_item.preview_with_placeholders(placeholder_values)

        if preview:
            self.preview_text.setPlainText(preview)
        else:
            self.preview_text.setPlainText("(No translation provided)")

    def on_translation_changed(self):
        """Handle translation text changes"""
        if not self.current_item:
            return

        new_translation = self.translation_text.toPlainText()

        if new_translation != self.current_item.translation:
            self.current_item.translation = new_translation
            self.current_item.is_translated = bool(new_translation.strip())
            self.is_modified = True

            current_list_item = self.translation_list.currentItem()
            if current_list_item:
                status = "✅" if self.current_item.is_translated else "❌"

                group_indicator = ""
                if len(self.current_item.contexts) > 1:
                    group_indicator = f" 📎{len(self.current_item.contexts)}"

                display_text = f"{status}{group_indicator} {self.current_item.source[:75]}{'...' if len(self.current_item.source) > 75 else ''}"
                current_list_item.setText(display_text)

            self.update_stats()
            self.update_preview()

            if self.current_file:
                filename = Path(self.current_file).name
                self.setWindowTitle(f"Translation Editor - {filename} *")

            if self.current_item.translation.strip():
                is_valid, error_msg = self.current_item.validate_translation()
                if not is_valid:
                    self.status_bar.showMessage(f"Validation Error: {error_msg}")
                else:
                    self.status_bar.showMessage("Translation valid")
            else:
                self.status_bar.showMessage("Ready")

    def filter_translations(self):
        """Filter translations based on search text"""
        self.update_translation_list()

    def copy_source_to_translation(self):
        """Copy source text to translation field"""
        if self.current_item:
            self.translation_text.setPlainText(self.current_item.source)

    def toggle_dark_mode(self, checked):
        """Toggle between dark and light mode"""
        self.dark_mode = checked
        self.apply_theme()

        if self.source_highlighter:
            self.source_highlighter.set_dark_mode(self.dark_mode)
        if self.translation_highlighter:
            self.translation_highlighter.set_dark_mode(self.dark_mode)

        if self.placeholder_group.isVisible():
            self.setup_placeholders()

    def apply_theme(self):
        """Apply dark or light theme to the application"""
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QLineEdit {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 2px;
                }
                QListWidget {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    selection-background-color: #4a90e2;
                    selection-color: #ffffff;
                }
                QListWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #555555;
                    background-color: #3a3a3a;
                }
                QListWidget::item:alternate {
                    background-color: #404040;
                }
                QListWidget::item:selected {
                    background-color: #4a90e2 !important;
                    color: #ffffff !important;
                }
                QListWidget::item:hover {
                    background-color: #4a4a4a;
                }
                QListWidget::item:selected:hover {
                    background-color: #5aa0f2 !important;
                    color: #ffffff !important;
                }
                QGroupBox {
                    color: #ffffff;
                    border: 2px solid #555555;
                    border-radius: 5px;
                    margin-top: 1ex;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QPushButton {
                    background-color: #4a4a4a;
                    color: #ffffff;
                    border: 1px solid #666666;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #3a3a3a;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QStatusBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QMenuBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QMenuBar::item:selected {
                    background-color: #4a4a4a;
                }
                QMenu {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QMenu::item:selected {
                    background-color: #4a4a4a;
                }
                QScrollArea {
                    background-color: #3a3a3a;
                    border: 1px solid #555555;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                    color: #000000;
                }
                QWidget {
                    background-color: #ffffff;
                    color: #000000;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    padding: 2px;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    selection-background-color: #0078d4;
                    selection-color: #ffffff;
                }
                QListWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #eeeeee;
                    color: #000000;
                    background-color: #ffffff;
                }
                QListWidget::item:alternate {
                    background-color: #f8f8f8;
                }
                QListWidget::item:selected {
                    background-color: #0078d4 !important;
                    color: #ffffff !important;
                }
                QListWidget::item:hover {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QListWidget::item:selected:hover {
                    background-color: #106ebe !important;
                    color: #ffffff !important;
                }
                QGroupBox {
                    color: #000000;
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 1ex;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                QCheckBox {
                    color: #000000;
                }
                QLabel {
                    color: #000000;
                }
            """)

        if hasattr(self, "preview_text"):
            if self.dark_mode:
                self.preview_text.setStyleSheet(
                    "background-color: #4a4a4a; border: 1px solid #666666; color: #ffffff;"
                )
            else:
                self.preview_text.setStyleSheet(
                    "background-color: #f0f0f0; border: 1px solid #ccc; color: #000000;"
                )

        if hasattr(self, "provider_status_label") and self.provider_status_label:
            if self.dark_mode:
                self.provider_status_label.setStyleSheet(
                    "font-size: 11px; padding: 2px 0; color: #cccccc;"
                )
            else:
                self.provider_status_label.setStyleSheet(
                    "font-size: 11px; padding: 2px 0; color: #666666;"
                )

    def validate_all_translations(self) -> tuple[bool, List[str]]:
        """Validate all translations for missing placeholders"""
        errors = []

        for i, item in enumerate(self.translations):
            if item.translation.strip():
                is_valid, error_msg = item.validate_translation()
                if not is_valid:
                    errors.append(
                        f"Line {i + 1}: {item.source[:50]}{'...' if len(item.source) > 50 else ''}\n  → {error_msg}"
                    )

        return len(errors) == 0, errors

    def save_file(self):
        """Save the current translation file"""
        if not self.current_file:
            self.save_file_as()
            return

        is_valid, errors = self.validate_all_translations()
        if not is_valid:
            error_msg = "Cannot save: Found placeholder validation errors:\n\n"
            error_msg += "\n\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n\n... and {len(errors) - 5} more errors."
            error_msg += "\n\nPlease fix these issues before saving."

            QMessageBox.warning(self, "Validation Errors", error_msg)
            return

        self.save_ts_file(self.current_file)

    def save_file_as(self):
        """Save the translation file with a new name"""
        if not self.translations:
            QMessageBox.warning(self, "Warning", "No translations to save.")
            return

        is_valid, errors = self.validate_all_translations()
        if not is_valid:
            error_msg = "Cannot save: Found placeholder validation errors:\n\n"
            error_msg += "\n\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n\n... and {len(errors) - 5} more errors."
            error_msg += "\n\nPlease fix these issues before saving."

            QMessageBox.warning(self, "Validation Errors", error_msg)
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Translation File",
            self.current_file or "src/translations/app_new.ts",
            "Qt Translation Files (*.ts);;All Files (*)",
        )

        if file_path:
            self.save_ts_file(file_path)

    def save_ts_file(self, file_path: str):
        """Save translations to a .ts file"""
        try:
            root = ET.Element("TS")
            root.set("version", "2.1")
            root.set("language", "en")  # You might want to make this configurable

            contexts = {}
            for item in self.translations:
                for i, context_name in enumerate(item.contexts):
                    if context_name not in contexts:
                        contexts[context_name] = []

                    filename = ""
                    line = 0
                    if i < len(item.locations):
                        filename, line = item.locations[i]

                    context_item = type(
                        "ContextItem",
                        (),
                        {
                            "source": item.source,
                            "translation": item.translation,
                            "filename": filename,
                            "line": line,
                        },
                    )()

                    contexts[context_name].append(context_item)

            for context_name, items in contexts.items():
                context_elem = ET.SubElement(root, "context")

                name_elem = ET.SubElement(context_elem, "name")
                name_elem.text = context_name

                for item in items:
                    message_elem = ET.SubElement(context_elem, "message")

                    if item.filename:
                        location_elem = ET.SubElement(message_elem, "location")
                        location_elem.set("filename", item.filename)
                        if item.line:
                            location_elem.set("line", str(item.line))

                    source_elem = ET.SubElement(message_elem, "source")
                    source_elem.text = item.source

                    translation_elem = ET.SubElement(message_elem, "translation")
                    if item.translation:
                        translation_elem.text = item.translation
                    else:
                        translation_elem.set("type", "unfinished")

            tree = ET.ElementTree(root)
            ET.indent(tree, space="    ")
            tree.write(file_path, encoding="utf-8", xml_declaration=True)

            self.current_file = file_path
            self.is_modified = False

            filename = Path(file_path).name
            self.setWindowTitle(f"Translation Editor - {filename}")

            total_entries = sum(len(item.contexts) for item in self.translations)
            self.status_bar.showMessage(
                f"Saved {len(self.translations)} unique translations ({total_entries} total entries) to {filename}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def closeEvent(self, event):
        """Handle window close event"""
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )

            if reply == QMessageBox.Save:
                self.save_file()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)

    app.setApplicationName("Translation Editor")
    app.setApplicationDisplayName("Translation Editor - TextureAtlas Toolbox")
    app.setApplicationVersion("1.1.0")
    app.setOrganizationName("AutisticLulu")

    window = TranslationEditor()
    window.show()

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path) and file_path.endswith(".ts"):
            window.load_ts_file(file_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
