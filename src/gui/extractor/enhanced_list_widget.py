#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QListWidget subclass with convenience methods for item management.

Provides helpers for adding items with associated data and retrieving
selections without manual data role handling.
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt


class EnhancedListWidget(QListWidget):
    """QListWidget with convenience methods for data association.

    Simplifies common patterns like storing user data alongside display
    text and retrieving the current selection.
    """

    def __init__(self, parent=None):
        """Create an enhanced list widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def tr(self, text):
        """Translate a string using Qt's translation system.

        Args:
            text: String to translate.

        Returns:
            Translated string for the current locale.
        """
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def add_item(self, text, data=None):
        """Append an item with optional user data.

        Args:
            text: Display text for the item.
            data: Arbitrary data to associate via UserRole.

        Returns:
            The newly created QListWidgetItem.
        """
        item = QListWidgetItem(text)
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        self.addItem(item)
        return item

    def get_selected_data(self):
        """Return the user data for the currently selected item.

        Returns:
            Data stored in UserRole, or None if nothing is selected.
        """
        current_item = self.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

    def get_selected_text(self):
        """Return the display text of the currently selected item.

        Returns:
            Item text string, or None if nothing is selected.
        """
        current_item = self.currentItem()
        if current_item:
            return current_item.text()
        return None

    def get_all_texts(self):
        """Collect the display text of every item in the list.

        Returns:
            List of text strings in display order.
        """
        return [self.item(i).text() for i in range(self.count())]

    def find_item_by_text(self, text):
        """Locate an item by its display text.

        Args:
            text: Exact text to match.

        Returns:
            Matching QListWidgetItem, or None if not found.
        """
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == text:
                return item
        return None
