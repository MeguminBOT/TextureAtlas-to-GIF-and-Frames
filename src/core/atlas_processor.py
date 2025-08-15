import os

# Import our own modules
from parsers.txt_parser import TxtParser
from parsers.xml_parser import XmlParser
from parsers.unknown_parser import UnknownParser


class AtlasProcessor:
    """A class to process texture atlases and their metadata.

    Attributes:
        atlas_path (str): The file path to the texture atlas image.
        metadata_path (str): The file path to the metadata file.
        atlas (PIL.Image.Image): The opened texture atlas image.
        sprites (list): The parsed sprite data from the metadata file.

    Methods:
        open_atlas_and_parse_metadata():
            Opens the texture atlas image and parses the metadata file.
            Returns a tuple containing the opened atlas image and the parsed sprite data.
        parse_xml_for_preview(animation_name):
            Parse XML metadata but only extract sprites for a specific animation.
            Reduces memory usage and processing time for preview generation.
        parse_txt_for_preview(animation_name):
            Parse TXT metadata but only extract sprites for a specific animation.
            Reduces memory usage and processing time for preview generation.
    """

    def __init__(self, atlas_path, metadata_path, parent_window=None):
        self.atlas_path = atlas_path
        self.metadata_path = metadata_path
        self.parent_window = parent_window
        self.atlas, self.sprites = self.open_atlas_and_parse_metadata()

    def open_atlas_and_parse_metadata(self):
        from PIL import Image

        print(f"Opening atlas: {self.atlas_path}")
        atlas = None
        sprites = []
        try:
            # Ignore any decompression bomb warnings/errors and always allow large images
            Image.MAX_IMAGE_PIXELS = None
            atlas = Image.open(self.atlas_path)
        except Exception as e:
            print(f"Error opening atlas: {e}")
            return None, []

        # Check if metadata_path is None or points to an image file (unknown spritesheet)
        if self.metadata_path is None or self.metadata_path.lower().endswith(
            (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
        ):
            print(f"Parsing unknown spritesheet: {self.atlas_path}")
            processed_atlas, sprites = UnknownParser.parse_unknown_image(
                self.atlas_path, self.parent_window
            )
            if processed_atlas is not None:
                atlas = processed_atlas

        elif self.metadata_path.endswith(".xml"):
            print(f"Parsing XML metadata: {self.metadata_path}")
            sprites = XmlParser.parse_xml_data(self.metadata_path)
        elif self.metadata_path.endswith(".txt"):
            print(f"Parsing TXT metadata: {self.metadata_path}")
            sprites = TxtParser.parse_txt_packer(self.metadata_path)
        else:
            raise ValueError(f"Unsupported metadata file format: {self.metadata_path}")
        return atlas, sprites

    def parse_xml_for_preview(self, animation_name):
        """
        Parse XML metadata but only extract sprites for a specific animation.
        This reduces memory usage and processing time for preview generation.

        Args:
            animation_name (str): The name of the animation to extract sprites for

        Returns:
            list: List of sprite dictionaries matching the animation
        """
        if not self.metadata_path or not self.metadata_path.endswith(".xml"):
            return []

        try:
            import xml.etree.ElementTree as ET
            import re

            tree = ET.parse(self.metadata_path)
            xml_root = tree.getroot()

            # Create animation name patterns for matching
            anim_patterns = [
                animation_name,  # Exact match
                re.sub(r"\d+$", "", animation_name),  # Remove trailing numbers
                re.sub(r"_?\d+$", "", animation_name),  # Remove _digits
                re.sub(r"[-_]?\d+$", "", animation_name),  # Remove -/digits
            ]
            # Remove duplicates while preserving order
            anim_patterns = list(dict.fromkeys(anim_patterns))

            animation_sprites = []
            for sprite in xml_root.findall("SubTexture"):
                sprite_name = sprite.get("name", "")
                # Only process sprites that belong to this animation
                is_match = False
                for pattern in anim_patterns:
                    if sprite_name == pattern or sprite_name.startswith(pattern):
                        is_match = True
                        break

                if is_match:
                    sprite_data = {
                        "name": sprite_name,
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
                    animation_sprites.append(sprite_data)

            return animation_sprites

        except Exception as e:
            print(f"Error parsing XML for animation {animation_name}: {e}")
            return []

    def parse_txt_for_preview(self, animation_name):
        """
        Parse TXT metadata but only extract sprites for a specific animation.
        This reduces memory usage and processing time for preview generation.

        Args:
            animation_name (str): The name of the animation to extract sprites for

        Returns:
            list: List of sprite dictionaries matching the animation
        """
        if not self.metadata_path or not self.metadata_path.endswith(".txt"):
            return []

        try:
            import re

            # Get all sprites first (TXT parser is already efficient)
            all_sprites = TxtParser.parse_txt_packer(self.metadata_path)

            # Create animation name patterns for matching
            anim_patterns = [
                animation_name,  # Exact match
                re.sub(r"\d+$", "", animation_name),  # Remove trailing numbers
                re.sub(r"_?\d+$", "", animation_name),  # Remove _digits
                re.sub(r"[-_]?\d+$", "", animation_name),  # Remove -/digits
            ]
            anim_patterns = list(dict.fromkeys(anim_patterns))

            # Filter to only sprites matching the animation
            animation_sprites = []
            for sprite in all_sprites:
                sprite_name = sprite.get("name", "")
                is_match = False
                for pattern in anim_patterns:
                    if sprite_name == pattern or sprite_name.startswith(pattern):
                        is_match = True
                        break
                if is_match:
                    animation_sprites.append(sprite)

            return animation_sprites

        except Exception as e:
            print(f"Error parsing TXT for animation {animation_name}: {e}")
            return []
