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

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
)

from core import TranslationItem
from core.translation_manager import TranslationManager
from gui import apply_app_theme
from gui.editor_tab import EditorTab
from gui.manage_tab import ManageTab
from localization import LocalizationOperations
from utils.preferences import load_preferences, save_preferences


class TranslationEditor(QMainWindow):
    """Main translation editor window."""

    def __init__(self) -> None:
        super().__init__()
        self.translation_manager = TranslationManager()
        self.localization_ops = LocalizationOperations()
        self.thread_pool = QThreadPool.globalInstance()
        self.current_ts_language: Optional[str] = None
        self.preferences: Dict[str, Any] = load_preferences()
        self.dark_mode = bool(self.preferences.get("dark_mode", False))
        self._apply_saved_translations_dir()

        self.tabs: Optional[QTabWidget] = None
        self.status_bar: Optional[QStatusBar] = None
        self.editor_tab: Optional[EditorTab] = None
        self.manage_tab: Optional[ManageTab] = None
        self.dark_mode_action: Optional[QAction] = None

        self.init_ui()
        self.apply_theme()
        if self.editor_tab:
            self.editor_tab.set_dark_mode(self.dark_mode)

    @staticmethod
    def _find_asset(relative_path: str) -> Optional[Path]:
        """Locate an asset path starting from common project roots."""

        script_path = Path(__file__).resolve()
        candidates = [Path.cwd()]
        candidates.extend(list(script_path.parents)[:4])
        checked = set()
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

    def init_ui(self) -> None:
        """Initialize the user interface."""

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
            except Exception:  # Best effort icon loading
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

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Open a .ts file to start editing")

        self.editor_tab = EditorTab(
            parent=self,
            translation_manager=self.translation_manager,
            status_bar=self.status_bar,
        )
        self.manage_tab = ManageTab(
            parent=self,
            localization_ops=self.localization_ops,
            thread_pool=self.thread_pool,
            status_bar=self.status_bar,
            on_translations_dir_changed=self._handle_translations_dir_change,
            open_ts_callback=self._open_ts_file_from_manage,
        )

        self.tabs.addTab(self.manage_tab, "Manage Files")
        self.tabs.addTab(self.editor_tab, "Editor")
        self.tabs.setCurrentWidget(self.manage_tab)

        self.create_menu_bar()

    def create_menu_bar(self) -> None:
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

        options_menu = menubar.addMenu("Options")
        self.dark_mode_action = options_menu.addAction("Dark Mode")
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(self.dark_mode)
        self.dark_mode_action.toggled.connect(self.toggle_dark_mode)

        help_menu = menubar.addMenu("Help")

        usage_action = help_menu.addAction("Using the Translator App")
        usage_action.triggered.connect(self.show_usage_help)

        api_help_action = help_menu.addAction("Translation API Keys")
        api_help_action.triggered.connect(self.show_api_key_help)

    def show_usage_help(self) -> None:
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

    def show_api_key_help(self) -> None:
        html = (
            "<p>Machine translation is optional. Provide your own API key.</p>"
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

    def show_help_dialog(self, title: str, html: str) -> None:
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

    def open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Translation File",
            "src/translations",
            "Qt Translation Files (*.ts);;All Files (*)",
        )
        if file_path:
            self.load_ts_file(file_path)

    def load_ts_file(self, file_path: str) -> None:
        if not self.editor_tab:
            return
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            self.current_ts_language = self._extract_language_from_root(root)
            if not self.current_ts_language:
                self.current_ts_language = self._infer_language_from_path(file_path)
            translation_groups: dict[str, TranslationItem] = {}

            for context in root.findall("context"):
                context_name_elem = context.find("name")
                context_name = context_name_elem.text if context_name_elem is not None else ""

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
                            translation_groups[source] = TranslationItem(
                                source, translation, context_name, filename, line
                            )

            translations = list(translation_groups.values())
            self.editor_tab.load_translations(file_path, translations)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{exc}")

    def save_file(self) -> None:
        if not self.editor_tab:
            return
        current_file = self.editor_tab.get_current_file()
        if not current_file:
            self.save_file_as()
            return
        is_valid, errors = self.editor_tab.validate_all_translations()
        if not is_valid:
            error_msg = "Cannot save: Found placeholder validation errors:\n\n"
            error_msg += "\n\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n\n... and {len(errors) - 5} more errors."
            error_msg += "\n\nPlease fix these issues before saving."
            QMessageBox.warning(self, "Validation Errors", error_msg)
            return
        self.save_ts_file(current_file)

    def save_file_as(self) -> None:
        if not self.editor_tab or not self.editor_tab.get_translations():
            QMessageBox.warning(self, "Warning", "No translations to save.")
            return
        is_valid, errors = self.editor_tab.validate_all_translations()
        if not is_valid:
            error_msg = "Cannot save: Found placeholder validation errors:\n\n"
            error_msg += "\n\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n\n... and {len(errors) - 5} more errors."
            error_msg += "\n\nPlease fix these issues before saving."
            QMessageBox.warning(self, "Validation Errors", error_msg)
            return
        current_file = self.editor_tab.get_current_file()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Translation File",
            current_file or "src/translations/app_new.ts",
            "Qt Translation Files (*.ts);;All Files (*)",
        )
        if file_path:
            self.save_ts_file(file_path)

    def save_ts_file(self, file_path: str) -> None:
        if not self.editor_tab:
            return
        try:
            translations = self.editor_tab.get_translations()
            root = ET.Element("TS")
            root.set("version", "2.1")
            language = self._infer_language_from_path(file_path) or self.current_ts_language
            if language:
                root.set("language", language)
                self.current_ts_language = language

            contexts: dict[str, List[tuple[TranslationItem, int]]] = {}
            for item in translations:
                for i, context_name in enumerate(item.contexts):
                    contexts.setdefault(context_name, [])
                    contexts[context_name].append((item, i))

            for context_name, entries in contexts.items():
                context_elem = ET.SubElement(root, "context")
                name_elem = ET.SubElement(context_elem, "name")
                name_elem.text = context_name

                for item, index in entries:
                    message_elem = ET.SubElement(context_elem, "message")
                    filename = ""
                    line = 0
                    if index < len(item.locations):
                        filename, line = item.locations[index]
                    if filename:
                        location_elem = ET.SubElement(message_elem, "location")
                        location_elem.set("filename", filename)
                        if line:
                            location_elem.set("line", str(line))

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

            self.editor_tab.mark_saved(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{exc}")

    def _extract_language_from_root(self, root: ET.Element) -> Optional[str]:
        return root.get("language") or root.get("sourcelanguage")

    def _infer_language_from_path(self, file_path: str) -> Optional[str]:
        filename = Path(file_path).name
        match = re.search(r"app_([A-Za-z0-9_\-]+)\.ts$", filename, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.editor_tab and self.editor_tab.has_unsaved_changes():
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

    def toggle_dark_mode(self, checked: bool) -> None:
        self.dark_mode = checked
        if self.dark_mode_action and self.dark_mode_action.isChecked() != checked:
            self.dark_mode_action.blockSignals(True)
            self.dark_mode_action.setChecked(checked)
            self.dark_mode_action.blockSignals(False)
        self.apply_theme()
        if self.editor_tab:
            self.editor_tab.set_dark_mode(self.dark_mode)

    def apply_theme(self) -> None:
        apply_app_theme(self, dark_mode=self.dark_mode)

    def _open_ts_file_from_manage(self, ts_path: Path) -> None:
        if not ts_path.exists():
            QMessageBox.warning(self, "File Missing", f"Translation file not found:\n{ts_path}")
            return
        self.load_ts_file(str(ts_path))
        if self.tabs and self.editor_tab:
            editor_index = self.tabs.indexOf(self.editor_tab)
            if editor_index != -1:
                self.tabs.setCurrentIndex(editor_index)

    def _handle_translations_dir_change(self, path: Path) -> None:
        self.preferences["translations_folder"] = str(path)
        self._persist_preferences()

    def _apply_saved_translations_dir(self) -> None:
        saved_path = self.preferences.get("translations_folder")
        if not saved_path:
            return
        try:
            self.localization_ops.set_translations_dir(Path(saved_path))
        except ValueError:
            self.preferences.pop("translations_folder", None)
            self._persist_preferences()

    def _persist_preferences(self) -> None:
        prefs = dict(self.preferences)
        prefs["dark_mode"] = self.dark_mode
        prefs["translations_folder"] = str(self.localization_ops.paths.translations_dir)
        save_preferences(prefs)
        self.preferences = prefs


def main() -> None:
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
