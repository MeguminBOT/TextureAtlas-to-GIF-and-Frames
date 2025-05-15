import os
import tkinter as tk

# Import our own modules
from utils.utilities import Utilities

class TxtParser:
    """
    A class to parse TXT files and extract sprite data.
    Currently only supports TXT files in the TextPacker format.

    Attributes:
        directory: The directory where the TXT file is located.
        txt_filename: The name of the TXT file to parse.
        tree: The Tkinter Treeview to populate with extracted names.
        parent_id: The ID of the parent node in the Treeview, if applicable.

    Methods:
        get_data(): Parses the TXT file and populates the Treeview with names.
        extract_names(): Extracts names from each line of the TXT file.
        get_names(names): Populates the Treeview with the given names.
        parse_txt_packer(file_path): Static method to parse TXT data from a file and return sprite information.
    """

    def __init__(self, directory, txt_filename, tree, parent_id=None):
        self.directory = directory
        self.txt_filename = txt_filename
        self.tree = tree
        self.parent_id = parent_id

    def get_data(self):
        names = self.extract_names()
        self.get_names(names)

    def extract_names(self):
        names = set()
        with open(os.path.join(self.directory, self.txt_filename), 'r') as file:
            for line in file:
                parts = line.split(' = ')[0]
                name = Utilities.strip_trailing_digits(parts)
                names.add(name)
        return names

    def get_names(self, names):
        for name in names:
            if self.parent_id:
                self.tree.insert(self.parent_id, 'end', text=name, values=("Animation",))
            else:
                self.tree.insert('', 'end', text=name, values=("Animation",))

    @staticmethod
    def parse_txt_packer(file_path):
        sprites = []
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.split(' = ')
                name = parts[0].strip()
                x, y, width, height = map(int, parts[1].split())
                sprites.append({'name': name, 'x': x, 'y': y, 'width': width, 'height': height})
        return sprites