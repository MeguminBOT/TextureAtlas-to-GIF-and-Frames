#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt-compatible TXT parser for sprite data.
Replaces the tkinter-dependent txt_parser.py with a UI-agnostic implementation.
"""

import os
from typing import Set, Optional, Callable, List, Dict, Any

# Import our own modules
from utils.utilities import Utilities
from parsers.base_parser import BaseParser, populate_qt_listbox


class TxtParser(BaseParser):
    """
    A Qt-compatible class to parse TXT files and extract sprite data.
    Currently only supports TXT files in the TextPacker format.

    This class is UI-agnostic and can work with both Qt and tkinter interfaces.
    """

    def __init__(self, directory: str, txt_filename: str, listbox_data=None, name_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the TXT parser.
        
        Args:
            directory: The directory where the TXT file is located
            txt_filename: The name of the TXT file to parse
            listbox_data: Optional listbox widget (Qt or tkinter) to populate with extracted names
            name_callback: Optional callback function to call for each extracted name
        """
        super().__init__(directory, txt_filename, name_callback)
        self.listbox_data = listbox_data

    def get_data(self) -> Set[str]:
        """Parse the TXT file and populate the listbox if provided."""
        try:
            names = self.extract_names()
            
            # Populate listbox if provided
            if self.listbox_data:
                self.populate_listbox(names)
            
            # Call the callback if provided
            if self.name_callback:
                for name in names:
                    self.name_callback(name)
                    
            return names
        except Exception as e:
            print(f"Error parsing TXT file {self.filename}: {e}")
            return set()

    def extract_names(self) -> Set[str]:
        """Extract sprite names from the TXT file."""
        names = set()
        try:
            with open(os.path.join(self.directory, self.filename), "r") as file:
                for line in file:
                    if " = " in line:
                        parts = line.split(" = ")[0]
                        name = Utilities.strip_trailing_digits(parts.strip())
                        if name:
                            names.add(name)
        except Exception as e:
            print(f"Error extracting names from TXT file {self.filename}: {e}")
        
        return names

    def populate_listbox(self, names: Set[str]):
        """Populate the Qt listbox with names."""
        if self.listbox_data is None:
            return
            
        populate_qt_listbox(self.listbox_data, names)

    @staticmethod
    def parse_txt_packer(file_path: str) -> List[Dict[str, Any]]:
        """
        Static method to parse TXT data from a file and return sprite information.
        
        Args:
            file_path: Path to the TXT file
            
        Returns:
            List of dictionaries containing sprite data
        """
        sprites = []
        try:
            with open(file_path, "r") as file:
                for line in file:
                    line = line.strip()
                    if " = " in line:
                        parts = line.split(" = ")
                        if len(parts) == 2:
                            name = parts[0].strip()
                            coords = parts[1].strip().split()
                            if len(coords) >= 4:
                                try:
                                    x, y, width, height = map(int, coords[:4])
                                    sprite_data = {
                                        "name": name,
                                        "x": x,
                                        "y": y,
                                        "width": width,
                                        "height": height
                                    }
                                    sprites.append(sprite_data)
                                except ValueError as e:
                                    print(f"Error parsing coordinates for sprite '{name}': {e}")
        except Exception as e:
            print(f"Error parsing TXT data from {file_path}: {e}")
        
        return sprites
