#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt-compatible parser base class and utilities.
Provides UI-agnostic parsing functionality for Qt applications.
"""

from abc import ABC, abstractmethod
from typing import Set, Optional, Callable


class BaseParser(ABC):
    """
    Abstract base class for sprite data parsers.
    
    This provides a UI-agnostic interface for parsing sprite data files.
    Parsers can work with callbacks instead of directly manipulating UI widgets.
    """
    
    def __init__(self, directory: str, filename: str, name_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the parser.
        
        Args:
            directory: Directory containing the file to parse
            filename: Name of the file to parse
            name_callback: Optional callback function to call for each extracted name
        """
        self.directory = directory
        self.filename = filename
        self.name_callback = name_callback
    
    @abstractmethod
    def extract_names(self) -> Set[str]:
        """
        Extract sprite names from the file.
        
        Returns:
            Set of unique sprite names
        """
        pass
    
    def get_data(self) -> Set[str]:
        """
        Parse the file and extract names.
        If a callback is provided, call it for each name.
        
        Returns:
            Set of extracted names
        """
        names = self.extract_names()
        if self.name_callback:
            for name in names:
                self.name_callback(name)
        return names


def populate_qt_listbox(listbox, names: Set[str]):
    """
    Helper function to populate a Qt listbox with names.
    
    Args:
        listbox: Qt listbox widget (QListWidget)
        names: Set of names to add to the listbox
    """
    listbox.clear()
    for name in sorted(names):
        listbox.addItem(name)
