from PIL import Image
from wand.image import Image as WandImg

from txt_parser import TxtParser
from xml_parser import XmlParser

class AtlasProcessor:
    def __init__(self, atlas_path, metadata_path):
        self.atlas_path = atlas_path
        self.metadata_path = metadata_path
        self.atlas, self.sprites = self.open_atlas_and_parse_metadata()

    def open_atlas_and_parse_metadata(self):
        print(f"Opening atlas: {self.atlas_path}")
        atlas = Image.open(self.atlas_path)
        if self.metadata_path.endswith('.xml'):
            print(f"Parsing XML metadata: {self.metadata_path}")
            sprites = XmlParser.parse_xml_data(self.metadata_path)
        elif self.metadata_path.endswith('.txt'):
            print(f"Parsing TXT metadata: {self.metadata_path}")
            sprites = TxtParser.parse_txt_packer(self.metadata_path)
        return atlas, sprites