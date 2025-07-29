#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt-compatible XML parser for sprite data.
Replaces the tkinter-dependent xml_parser.py with a UI-agnostic implementation.
"""

import os
import xml.etree.ElementTree as ET
from typing import Set, Optional, Callable, List, Dict, Any

# Import our own modules
from utils.utilities import Utilities
from parsers.base_parser import BaseParser, populate_qt_listbox


class XmlParser(BaseParser):
    """
    A Qt-compatible class to parse XML files and extract sprite data.
    Currently only supports XML files in the Starling/Sparrow format.

    This class is UI-agnostic and can work with both Qt and tkinter interfaces.
    """

    def __init__(self, directory: str, xml_filename: str, listbox_data=None, name_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the XML parser.
        
        Args:
            directory: The directory where the XML file is located
            xml_filename: The name of the XML file to parse
            listbox_data: Optional listbox widget (Qt or tkinter) to populate with extracted names
            name_callback: Optional callback function to call for each extracted name
        """
        super().__init__(directory, xml_filename, name_callback)
        self.listbox_data = listbox_data

    def get_data(self) -> Set[str]:
        """Parse the XML file and populate the listbox if provided."""
        try:
            tree = ET.parse(os.path.join(self.directory, self.filename))
            xml_root = tree.getroot()
            names = self.extract_names_from_root(xml_root)
            
            # Populate listbox if provided
            if self.listbox_data:
                self.populate_listbox(names)
            
            # Call the callback if provided
            if self.name_callback:
                for name in names:
                    self.name_callback(name)
                    
            return names
        except Exception as e:
            print(f"Error parsing XML file {self.filename}: {e}")
            return set()

    def extract_names(self) -> Set[str]:
        """Extract sprite names from the XML file."""
        try:
            tree = ET.parse(os.path.join(self.directory, self.filename))
            xml_root = tree.getroot()
            return self.extract_names_from_root(xml_root)
        except Exception as e:
            print(f"Error extracting names from XML file {self.filename}: {e}")
            return set()

    def extract_names_from_root(self, xml_root) -> Set[str]:
        """Extract names from the XML root element."""
        names = set()
        for subtexture in xml_root.findall(".//SubTexture"):
            name = subtexture.get("name")
            if name:
                name = Utilities.strip_trailing_digits(name)
                names.add(name)
        return names

    def populate_listbox(self, names: Set[str]):
        """Populate the Qt listbox with names."""
        if self.listbox_data is None:
            return
            
        populate_qt_listbox(self.listbox_data, names)

    @staticmethod
    def parse_xml_data(file_path: str) -> List[Dict[str, Any]]:
        """
        Static method to parse XML data from a file and return sprite information.
        
        Args:
            file_path: Path to the XML file
            
        Returns:
            List of dictionaries containing sprite data
        """
        try:
            tree = ET.parse(file_path)
            xml_root = tree.getroot()
            sprites = []
            
            for sprite in xml_root.findall("SubTexture"):
                sprite_data = {
                    "name": sprite.get("name"),
                    "x": int(sprite.get("x", 0)),
                    "y": int(sprite.get("y", 0)),
                    "width": int(sprite.get("width", 0)),
                    "height": int(sprite.get("height", 0)),
                    "frameX": int(sprite.get("frameX", 0)),
                    "frameY": int(sprite.get("frameY", 0)),
                    "frameWidth": int(sprite.get("frameWidth", sprite.get("width", 0))),
                    "frameHeight": int(sprite.get("frameHeight", sprite.get("height", 0))),
                    "rotated": sprite.get("rotated", "false") == "true",
                }
                sprites.append(sprite_data)
                
            return sprites
        except Exception as e:
            print(f"Error parsing XML data from {file_path}: {e}")
            return []
