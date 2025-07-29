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

"""

import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QLineEdit,
    QLabel,
    QPushButton,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QGroupBox,
    QStatusBar,
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QIcon


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
            self.placeholder_format.setForeground(QColor(100, 200, 255))  # Light blue
        else:
            self.placeholder_format.setForeground(QColor(0, 100, 200))  # Dark blue
        self.placeholder_format.setFontWeight(QFont.Bold)

    def highlightBlock(self, text):
        """Highlight placeholders in the given text block"""
        # Pattern to match {placeholder} and {placeholder:format}
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
        self.translation = translation or ""  # Handle None values
        self.contexts = [context] if context else []  # List of all contexts using this source
        self.locations = [(filename, line)] if filename else []  # List of all file locations
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
            # Remove braces for lookup
            key = placeholder.strip("{}")
            if key in placeholder_values:
                preview = preview.replace(placeholder, placeholder_values[key])
            elif placeholder in placeholder_values:
                preview = preview.replace(placeholder, placeholder_values[placeholder])
            else:
                # Use placeholder as fallback
                preview = preview.replace(placeholder, f"[{key}]")

        return preview

    def validate_translation(self) -> tuple[bool, str]:
        """Validate that translation contains all required placeholders from source"""
        if not self.translation.strip():
            return True, ""  # Empty translation is valid (unfinished)

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


class TranslationEditor(QMainWindow):
    """Main translation editor window"""

    def __init__(self):
        super().__init__()
        self.current_file = None
        self.translations: List[TranslationItem] = []
        self.current_item: Optional[TranslationItem] = None
        self.is_modified = False
        self.dark_mode = False

        # Placeholder highlighters
        self.source_highlighter = None
        self.translation_highlighter = None

        self.init_ui()
        self.setup_connections()
        self.apply_theme()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Translation Editor - TextureAtlas Toolbox")
        self.setGeometry(100, 100, 1200, 800)

        # Set application icon if available (with fallback to PNG)
        icon_path = Path("assets/icon-ts.ico")
        icon_set = False
        
        # Try ICO first
        if icon_path.exists():
            try:
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    self.setWindowIcon(icon)
                    icon_set = True
            except Exception:
                pass  # Fall back to PNG
        
        # Fallback to PNG if ICO failed or doesn't exist
        if not icon_set:
            png_icon_path = Path("assets/icon-ts.png")
            if png_icon_path.exists():
                try:
                    icon = QIcon(str(png_icon_path))
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                except Exception:
                    pass  # No icon available

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - Translation list
        self.create_left_panel(splitter)

        # Right panel - Translation editor
        self.create_right_panel(splitter)

        # Set splitter proportions (30% list, 70% editor)
        splitter.setSizes([360, 840])

        # Create menu bar and toolbar
        self.create_menu_bar()
        self.create_toolbar()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Open a .ts file to start editing")

    def create_left_panel(self, parent):
        """Create the left panel with translation list"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search translations...")
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        left_layout.addLayout(filter_layout)

        # Translation list
        self.translation_list = QListWidget()
        self.translation_list.setAlternatingRowColors(True)  # Required for CSS ::alternate selector
        left_layout.addWidget(self.translation_list)

        # Stats
        self.stats_label = QLabel("No file loaded")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 5px;")
        left_layout.addWidget(self.stats_label)

        parent.addWidget(left_widget)

    def create_right_panel(self, parent):
        """Create the right panel with translation editor"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Source text (read-only)
        source_group = QGroupBox("Source Text")
        source_layout = QVBoxLayout(source_group)
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setMaximumHeight(100)
        self.source_text.setFont(QFont("Consolas", 10))

        # Add syntax highlighting for source text
        self.source_highlighter = PlaceholderHighlighter(
            self.source_text.document(), self.dark_mode
        )

        source_layout.addWidget(self.source_text)
        right_layout.addWidget(source_group)

        # Translation text (editable)
        translation_group = QGroupBox("Translation")
        translation_layout = QVBoxLayout(translation_group)

        # Add a horizontal layout for translation controls
        translation_controls = QHBoxLayout()

        # Copy button to copy source to translation
        self.copy_source_btn = QPushButton("📋 Copy Source")
        self.copy_source_btn.setToolTip("Copy source text to translation field")
        self.copy_source_btn.clicked.connect(self.copy_source_to_translation)
        self.copy_source_btn.setEnabled(False)
        translation_controls.addWidget(self.copy_source_btn)

        # Add stretch to push button to the left
        translation_controls.addStretch()

        translation_layout.addLayout(translation_controls)

        self.translation_text = QTextEdit()
        self.translation_text.setMaximumHeight(100)
        self.translation_text.setFont(QFont("Consolas", 10))

        # Add syntax highlighting for translation text
        self.translation_highlighter = PlaceholderHighlighter(
            self.translation_text.document(), self.dark_mode
        )

        translation_layout.addWidget(self.translation_text)
        right_layout.addWidget(translation_group)

        # Placeholder values (shown only when needed)
        self.placeholder_group = QGroupBox("Placeholder Values (for preview)")
        placeholder_layout = QVBoxLayout(self.placeholder_group)

        # Scrollable area for dynamic placeholder inputs
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

        # Preview text (read-only)
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setFont(QFont("Consolas", 10))
        # Style preview differently
        self.preview_text.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        preview_layout.addWidget(self.preview_text)
        right_layout.addWidget(preview_group)

        # Context info
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

        # File menu
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

    def create_toolbar(self):
        """Create toolbar with main actions"""
        toolbar = self.addToolBar("Main")

        # Open button
        open_btn = QPushButton("Open .ts File")
        open_btn.clicked.connect(self.open_file)
        toolbar.addWidget(open_btn)

        # Save button
        self.save_btn = QPushButton("Save .ts File")
        self.save_btn.clicked.connect(self.save_file)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

        # Save as button
        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.clicked.connect(self.save_file_as)
        self.save_as_btn.setEnabled(False)
        toolbar.addWidget(self.save_as_btn)

        # Spacer
        toolbar.addSeparator()

        # Dark mode toggle
        self.dark_mode_checkbox = QCheckBox("Dark Mode")
        self.dark_mode_checkbox.toggled.connect(self.toggle_dark_mode)
        toolbar.addWidget(self.dark_mode_checkbox)

    def setup_connections(self):
        """Setup signal connections"""
        self.translation_list.currentItemChanged.connect(self.on_translation_selected)
        self.translation_text.textChanged.connect(self.on_translation_changed)
        self.filter_input.textChanged.connect(self.filter_translations)

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
            translation_groups = {}  # Dictionary to group by source string

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

                    # Get file location info
                    filename = ""
                    line = 0
                    if location_elem is not None:
                        filename = location_elem.get("filename", "")
                        line = int(location_elem.get("line", 0))

                    # Skip empty sources
                    if source.strip():
                        if source in translation_groups:
                            # Add this context to existing group
                            existing_item = translation_groups[source]
                            existing_item.add_context(context_name, filename, line)
                            # If this context has a translation and the existing doesn't, use it
                            if translation.strip() and not existing_item.translation.strip():
                                existing_item.translation = translation
                                existing_item.is_translated = True
                        else:
                            # Create new translation item
                            item = TranslationItem(
                                source, translation, context_name, filename, line
                            )
                            translation_groups[source] = item

            # Convert grouped translations to list
            self.translations = list(translation_groups.values())

            self.current_file = file_path
            self.is_modified = False
            self.update_translation_list()
            self.update_stats()
            self.save_btn.setEnabled(True)
            self.save_as_btn.setEnabled(True)

            # Update status message to show grouping info
            total_entries = sum(len(item.contexts) for item in self.translations)
            grouped_msg = f"Loaded {len(self.translations)} unique translations ({total_entries} total entries) from {Path(file_path).name}"

            self.setWindowTitle(f"Translation Editor - {Path(file_path).name}")
            self.status_bar.showMessage(grouped_msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def update_translation_list(self):
        """Update the translation list widget"""
        self.translation_list.clear()

        filter_text = self.filter_input.text().lower()

        for item in self.translations:
            # Apply filter
            if (
                filter_text
                and filter_text not in item.source.lower()
                and filter_text not in item.translation.lower()
            ):
                continue

            # Create list item
            list_item = QListWidgetItem()

            # Visual indicators instead of background colors for dark mode compatibility
            if item.is_translated:
                status = "✅"  # Green checkmark for translated
            else:
                status = "❌"  # Red X for untranslated

            # Add grouping indicator if multiple contexts
            group_indicator = ""
            if len(item.contexts) > 1:
                group_indicator = f" 📎{len(item.contexts)}"  # Paperclip with count

            # Format display text
            display_text = f"{status}{group_indicator} {item.source[:75]}{'...' if len(item.source) > 75 else ''}"
            list_item.setText(display_text)

            # Store reference to translation item
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

        # Enable copy button
        self.copy_source_btn.setEnabled(True)

        # Update source text
        self.source_text.setPlainText(self.current_item.source)

        # Update translation text
        self.translation_text.blockSignals(True)  # Prevent triggering change event
        self.translation_text.setPlainText(self.current_item.translation)
        self.translation_text.blockSignals(False)

        # Update context info to show all contexts
        if len(self.current_item.contexts) == 1:
            context_info = f"Context: {self.current_item.contexts[0]}\n"
            context_info += f"File: {self.current_item.filename}:{self.current_item.line}"
        else:
            context_info = f"Used in {len(self.current_item.contexts)} contexts:\n\n"
            context_info += self.current_item.get_all_contexts_info()

        self.context_label.setText(context_info)

        # Handle placeholders
        self.setup_placeholders()

        # Update preview
        self.update_preview()

    def setup_placeholders(self):
        """Setup placeholder input fields if needed"""
        if not self.current_item or not self.current_item.has_placeholders():
            self.placeholder_group.setVisible(False)
            return

        # Clear existing placeholder widgets
        for i in reversed(range(self.placeholder_layout.count())):
            child = self.placeholder_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Create input fields for each placeholder
        placeholders = self.current_item.get_placeholders()
        for placeholder in placeholders:
            placeholder_key = placeholder.strip("{}")

            # Create label and input
            label = QLabel(f"{placeholder}:")
            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Example value for {placeholder}")
            input_field.textChanged.connect(self.update_preview)

            # Style placeholder input with distinct color
            if self.dark_mode:
                input_field.setStyleSheet(
                    "QLineEdit { color: #FFA500; background-color: #3a3a3a; }"
                )  # Orange text on dark
            else:
                input_field.setStyleSheet(
                    "QLineEdit { color: #FF6600; background-color: #ffffff; }"
                )  # Orange text on light

            # Add some default values for common patterns
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
                    # Extract placeholder from label text
                    label_text = label_widget.text().rstrip(":")
                    placeholder_key = label_text.strip("{}")

                    values[label_text] = input_widget.text()
                    values[placeholder_key] = input_widget.text()

        return values

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

            # Update list item appearance
            current_list_item = self.translation_list.currentItem()
            if current_list_item:
                status = "✅" if self.current_item.is_translated else "❌"

                # Add grouping indicator if multiple contexts
                group_indicator = ""
                if len(self.current_item.contexts) > 1:
                    group_indicator = f" 📎{len(self.current_item.contexts)}"

                display_text = f"{status}{group_indicator} {self.current_item.source[:75]}{'...' if len(self.current_item.source) > 75 else ''}"
                current_list_item.setText(display_text)

            # Update stats and preview
            self.update_stats()
            self.update_preview()

            # Update window title to show modification
            if self.current_file:
                filename = Path(self.current_file).name
                self.setWindowTitle(f"Translation Editor - {filename} *")

            # Show validation status for current item
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
            # This will trigger on_translation_changed automatically

    def toggle_dark_mode(self, checked):
        """Toggle between dark and light mode"""
        self.dark_mode = checked
        self.apply_theme()

        # Update highlighters
        if self.source_highlighter:
            self.source_highlighter.set_dark_mode(self.dark_mode)
        if self.translation_highlighter:
            self.translation_highlighter.set_dark_mode(self.dark_mode)

        # Refresh placeholder inputs if any are shown
        if self.placeholder_group.isVisible():
            self.setup_placeholders()

    def apply_theme(self):
        """Apply dark or light theme to the application"""
        if self.dark_mode:
            # Dark theme
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
            # Light theme (default)
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

        # Update preview text styling
        if hasattr(self, "preview_text"):
            if self.dark_mode:
                self.preview_text.setStyleSheet(
                    "background-color: #4a4a4a; border: 1px solid #666666; color: #ffffff;"
                )
            else:
                self.preview_text.setStyleSheet(
                    "background-color: #f0f0f0; border: 1px solid #ccc; color: #000000;"
                )

    def validate_all_translations(self) -> tuple[bool, List[str]]:
        """Validate all translations for missing placeholders"""
        errors = []

        for i, item in enumerate(self.translations):
            if item.translation.strip():  # Only validate non-empty translations
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

        # Validate translations before saving
        is_valid, errors = self.validate_all_translations()
        if not is_valid:
            error_msg = "Cannot save: Found placeholder validation errors:\n\n"
            error_msg += "\n\n".join(errors[:5])  # Show first 5 errors
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

        # Validate translations before saving
        is_valid, errors = self.validate_all_translations()
        if not is_valid:
            error_msg = "Cannot save: Found placeholder validation errors:\n\n"
            error_msg += "\n\n".join(errors[:5])  # Show first 5 errors
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
            # Create XML structure
            root = ET.Element("TS")
            root.set("version", "2.1")
            root.set("language", "en")  # You might want to make this configurable

            # Group translations by context, expanding grouped items
            contexts = {}
            for item in self.translations:
                # For each context this source string appears in
                for i, context_name in enumerate(item.contexts):
                    if context_name not in contexts:
                        contexts[context_name] = []

                    # Create individual entry for each context
                    filename = ""
                    line = 0
                    if i < len(item.locations):
                        filename, line = item.locations[i]

                    # Create a temporary item for this specific context
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

            # Create context elements
            for context_name, items in contexts.items():
                context_elem = ET.SubElement(root, "context")

                name_elem = ET.SubElement(context_elem, "name")
                name_elem.text = context_name

                for item in items:
                    message_elem = ET.SubElement(context_elem, "message")

                    # Add location if available
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

            # Write to file
            tree = ET.ElementTree(root)
            ET.indent(tree, space="    ")  # Pretty formatting
            tree.write(file_path, encoding="utf-8", xml_declaration=True)

            self.current_file = file_path
            self.is_modified = False

            filename = Path(file_path).name
            self.setWindowTitle(f"Translation Editor - {filename}")

            # Calculate total entries for status message
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

    # Set application info
    app.setApplicationName("Translation Editor")
    app.setApplicationDisplayName("Translation Editor - TextureAtlas Toolbox")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AutisticLulu")

    # Create and show main window
    window = TranslationEditor()
    window.show()

    # Check for command line file argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path) and file_path.endswith(".ts"):
            window.load_ts_file(file_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
