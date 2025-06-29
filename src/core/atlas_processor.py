from PIL import Image

# Import our own modules
from parsers.txt_parser import TxtParser
from parsers.xml_parser import XmlParser
from parsers.unknown_parser import UnknownParser

# Import debug window functionality
try:
    from gui.debug_window import print_to_ui
except ImportError:
    # Fallback if debug window not available
    def print_to_ui(message, level="info"):
        print(message)


class AtlasProcessor:
    """
    A class to process texture atlases and their metadata.

    Attributes:
        atlas_path (str): The file path to the texture atlas image.
        metadata_path (str): The file path to the metadata file.
        atlas (PIL.Image.Image): The opened texture atlas image.
        sprites (list): The parsed sprite data from the metadata file.

    Methods:
        open_atlas_and_parse_metadata():
            Opens the texture atlas image and parses the metadata file.
            Returns:
                tuple: A tuple containing the opened atlas image and the parsed sprite data.
    """

    def __init__(self, atlas_path, metadata_path, parent_window=None):
        self.atlas_path = atlas_path
        self.metadata_path = metadata_path
        self.parent_window = parent_window
        self.atlas, self.sprites = self.open_atlas_and_parse_metadata()

    def open_atlas_and_parse_metadata(self):
        print_to_ui(f"Opening atlas: {self.atlas_path}", "info")
        atlas = Image.open(self.atlas_path)

        # Check if metadata_path is None or points to an image file (unknown spritesheet)
        if (self.metadata_path is None or 
            self.metadata_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'))):
            print_to_ui(f"Parsing unknown spritesheet: {self.atlas_path}", "warning")
            processed_atlas, sprites = UnknownParser.parse_unknown_image(self.atlas_path, self.parent_window)
            if processed_atlas is not None:
                atlas = processed_atlas

        elif self.metadata_path.endswith(".xml"):
            print_to_ui(f"Parsing XML metadata: {self.metadata_path}", "info")
            sprites = XmlParser.parse_xml_data(self.metadata_path)
        elif self.metadata_path.endswith(".txt"):
            print_to_ui(f"Parsing TXT metadata: {self.metadata_path}", "info")
            sprites = TxtParser.parse_txt_packer(self.metadata_path)
        else:
            raise ValueError(f"Unsupported metadata file format: {self.metadata_path}")
        return atlas, sprites
