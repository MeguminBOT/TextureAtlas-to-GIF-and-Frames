import os
import xml.etree.ElementTree as ET
import tkinter as tk

# Import our own modules
from utils.utilities import Utilities

class XmlParser:
    """
    A class to parse XML files and extract sprite data.
    Currently only supports XML files in the Starling/Sparrow format.

    Attributes:
        directory: The directory where the XML file is located.
        xml_filename: The name of the XML file to parse.
        tree: The Tkinter Treeview to populate with extracted names.
        parent_id: The parent ID in the Treeview to add children under.

    Methods:
        get_data(): Parses the XML file and populates the Treeview with names.
        extract_names(xml_root): Extracts names from the XML root element.
        get_names(names): Populates the Treeview with the given names.
        parse_xml_data(file_path): Static method to parse XML data from a file and return sprite information.
    """

    def __init__(self, directory, xml_filename, tree, parent_id=None):
        self.directory = directory
        self.xml_filename = xml_filename
        self.tree = tree
        self.parent_id = parent_id

    def get_data(self):
        tree = ET.parse(os.path.join(self.directory, self.xml_filename))
        xml_root = tree.getroot()
        names = self.extract_names(xml_root)
        self.get_names(names)

    def extract_names(self, xml_root):
        names = set()
        for subtexture in xml_root.findall(".//SubTexture"):
            name = subtexture.get('name')
            name = Utilities.strip_trailing_digits(name)
            names.add(name)
        return names

    def get_names(self, names):
        for name in names:
            if self.parent_id:
                self.tree.insert(self.parent_id, 'end', text=name, values=("Animation",))
            else:
                self.tree.insert('', 'end', text=name, values=("Animation",))

    @staticmethod
    def parse_xml_data(file_path):
        tree = ET.parse(file_path)
        xml_root = tree.getroot()
        sprites = [
            {
                'name': sprite.get('name'),
                'x': int(sprite.get('x')),
                'y': int(sprite.get('y')),
                'width': int(sprite.get('width')),
                'height': int(sprite.get('height')),
                'frameX': int(sprite.get('frameX', 0)),
                'frameY': int(sprite.get('frameY', 0)),
                'frameWidth': int(sprite.get('frameWidth', sprite.get('width'))),
                'frameHeight': int(sprite.get('frameHeight', sprite.get('height'))),
                'rotated': sprite.get('rotated', 'false') == 'true'
            } for sprite in xml_root.findall('SubTexture')
        ]
        return sprites