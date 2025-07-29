#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QScrollArea,
    QWidget,
    QGroupBox,
)
from PySide6.QtCore import Qt


class FindReplaceWindow(QDialog):
    """
    A Qt dialog for managing find-and-replace rules for filenames.

    This class creates a Qt window that allows the user to add, edit, and delete find-and-replace rules,
    including support for regular expressions, to be applied to exported filenames.
    """

    def __init__(self, on_store_callback, replace_rules=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Find and Replace"))
        self.setGeometry(200, 200, 500, 400)
        self.on_store_callback = on_store_callback
        self.replace_rules = replace_rules or []
        self.rule_widgets = []
        self.setup_ui()
        self.load_existing_rules()

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def setup_ui(self):
        """Sets up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel(self.tr("Find and Replace Rules"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Instructions
        instructions = QLabel(
            "Create rules to find and replace text in exported filenames. "
            "Regular expressions are supported for advanced pattern matching."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(instructions)

        # Scrollable area for rules
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Rules container
        self.rules_container = QWidget()
        self.rules_layout = QVBoxLayout(self.rules_container)
        self.rules_layout.setSpacing(5)
        self.rules_layout.addStretch()  # Add stretch at the end

        scroll_area.setWidget(self.rules_container)
        layout.addWidget(scroll_area)

        # Add Rule button
        add_btn = QPushButton(self.tr("Add Rule"))
        add_btn.clicked.connect(self.add_rule)
        add_btn.setMaximumWidth(100)
        layout.addWidget(add_btn)

        # Buttons
        button_layout = QHBoxLayout()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_changes)
        ok_btn.setDefault(True)

        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def load_existing_rules(self):
        """Load existing rules into the UI."""
        for rule in self.replace_rules:
            self.add_rule(rule)

    def add_rule(self, rule_data=None):
        """Add a new rule entry to the window."""
        if rule_data is None:
            rule_data = {"find": "", "replace": "", "regex": False}
        elif not isinstance(rule_data, dict):
            # Handle case where rule_data is not a dictionary (e.g., boolean, string, etc.)
            rule_data = {"find": "", "replace": "", "regex": False}

        # Create rule frame
        rule_frame = QGroupBox()
        rule_frame.setStyleSheet("""
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)

        rule_layout = QVBoxLayout(rule_frame)
        rule_layout.setSpacing(8)

        # Find field
        find_layout = QHBoxLayout()
        find_label = QLabel(self.tr("Find:"))
        find_label.setMinimumWidth(60)
        find_entry = QLineEdit()
        find_entry.setText(rule_data.get("find", ""))
        find_entry.setPlaceholderText("Text to find...")
        find_layout.addWidget(find_label)
        find_layout.addWidget(find_entry)
        rule_layout.addLayout(find_layout)

        # Replace field
        replace_layout = QHBoxLayout()
        replace_label = QLabel(self.tr("Replace:"))
        replace_label.setMinimumWidth(60)
        replace_entry = QLineEdit()
        replace_entry.setText(rule_data.get("replace", ""))
        replace_entry.setPlaceholderText("Replacement text...")
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(replace_entry)
        rule_layout.addLayout(replace_layout)

        # Options and delete button
        options_layout = QHBoxLayout()
        regex_checkbox = QCheckBox("Regular Expression")
        regex_checkbox.setChecked(rule_data.get("regex", False))

        delete_btn = QPushButton(self.tr("Delete"))
        delete_btn.clicked.connect(lambda: self.delete_rule(rule_frame))
        delete_btn.setMaximumWidth(80)
        delete_btn.setStyleSheet("QPushButton { color: #cc0000; }")

        options_layout.addWidget(regex_checkbox)
        options_layout.addStretch()
        options_layout.addWidget(delete_btn)
        rule_layout.addLayout(options_layout)

        # Store widget references for later retrieval
        rule_frame.find_entry = find_entry
        rule_frame.replace_entry = replace_entry
        rule_frame.regex_checkbox = regex_checkbox

        # Add to rules layout (before the stretch)
        self.rules_layout.insertWidget(self.rules_layout.count() - 1, rule_frame)
        self.rule_widgets.append(rule_frame)

    def delete_rule(self, rule_frame):
        """Delete a rule from the window."""
        if rule_frame in self.rule_widgets:
            self.rule_widgets.remove(rule_frame)
        self.rules_layout.removeWidget(rule_frame)
        rule_frame.deleteLater()

    def accept_changes(self):
        """Collect all rules and call the callback."""
        rules = []
        for rule_frame in self.rule_widgets:
            rule = {
                "find": rule_frame.find_entry.text(),
                "replace": rule_frame.replace_entry.text(),
                "regex": rule_frame.regex_checkbox.isChecked(),
            }
            rules.append(rule)

        self.on_store_callback(rules)
        self.accept()

    @staticmethod
    def show_find_replace_window(on_store_callback, replace_rules=None, parent=None):
        """Static method to show the find and replace window."""
        window = FindReplaceWindow(on_store_callback, replace_rules, parent)
        window.exec()
