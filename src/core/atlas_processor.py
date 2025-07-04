from PIL import Image

# Import our own modules
from parsers.txt_parser import TxtParser
from parsers.xml_parser import XmlParser
from parsers.unknown_parser import UnknownParser
from parsers.animate_parser import AnimateParser


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
        print(f"Opening atlas: {self.atlas_path}")
        atlas = Image.open(self.atlas_path)

        # Check if metadata_path is None or points to an image file (unknown spritesheet)
        if (self.metadata_path is None or 
            self.metadata_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'))):
            print(f"Parsing unknown spritesheet: {self.atlas_path}")
            processed_atlas, sprites = UnknownParser.parse_unknown_image(self.atlas_path, self.parent_window)
            if processed_atlas is not None:
                atlas = processed_atlas

        elif self.metadata_path.endswith(".xml"):
            print(f"Parsing XML metadata: {self.metadata_path}")
            sprites = XmlParser.parse_xml_data(self.metadata_path)
        elif self.metadata_path.endswith(".txt"):
            print(f"Parsing TXT metadata: {self.metadata_path}")
            sprites = TxtParser.parse_txt_packer(self.metadata_path)
        elif self.metadata_path.endswith(".json"):
            # Check if it's an Adobe Animate JSON file
            if AnimateParser.is_animate_json(self.metadata_path):
                print(f"Parsing Adobe Animate JSON metadata: {self.metadata_path}")
                sprites = AnimateParser.parse_animate_data(self.metadata_path)
            else:
                raise ValueError(f"Unsupported JSON format (not Adobe Animate): {self.metadata_path}")
        else:
            raise ValueError(f"Unsupported metadata file format: {self.metadata_path}")
        return atlas, sprites
