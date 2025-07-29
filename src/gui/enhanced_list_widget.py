#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Qt UI helper to replace QListView with QListWidget for easier list management.
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt


class EnhancedListWidget(QListWidget):
    """Enhanced QListWidget with additional convenience methods."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication
        return QCoreApplication.translate(self.__class__.__name__, text)


    def add_item(self, text, data=None):
        """Add an item with optional associated data."""
        item = QListWidgetItem(text)
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        self.addItem(item)
        return item

    def get_selected_data(self):
        """Get the data associated with the currently selected item."""
        current_item = self.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

    def get_selected_text(self):
        """Get the text of the currently selected item."""
        current_item = self.currentItem()
        if current_item:
            return current_item.text()
        return None

    def get_all_texts(self):
        """Get all text items in the list."""
        return [self.item(i).text() for i in range(self.count())]

    def find_item_by_text(self, text):
        """Find an item by its text."""
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == text:
                return item
        return None
