"""Load texture atlases and parse their accompanying metadata.

Provides ``AtlasProcessor`` which opens atlas images and delegates to the
appropriate parser (XML, TXT, or unknown) based on the metadata file extension.
"""

from parsers.txt_parser import TxtParser
from parsers.xml_parser import XmlParser
from parsers.unknown_parser import UnknownParser


class AtlasProcessor:
    """Open a texture atlas and parse sprite metadata.

    Automatically selects the correct parser based on the metadata file
    extension. For unknown spritesheets (no metadata or image-only paths),
    falls back to heuristic sprite detection.

    Attributes:
        atlas_path: Filesystem path to the atlas image.
        metadata_path: Filesystem path to the metadata file, or ``None``.
        parent_window: Optional parent widget for progress dialogs.
        atlas: The opened PIL ``Image``, or ``None`` on failure.
        sprites: List of parsed sprite dicts.
    """

    def __init__(self, atlas_path, metadata_path, parent_window=None):
        """Load the atlas and parse metadata on construction.

        Args:
            atlas_path: Path to the texture atlas image.
            metadata_path: Path to the XML/TXT metadata, or ``None`` for
                unknown spritesheets.
            parent_window: Optional parent widget for dialogs.
        """
        self.atlas_path = atlas_path
        self.metadata_path = metadata_path
        self.parent_window = parent_window
        self.atlas, self.sprites = self.open_atlas_and_parse_metadata()

    def open_atlas_and_parse_metadata(self):
        """Open the atlas image and parse sprite metadata.

        Selects the appropriate parser based on ``metadata_path`` extension.
        Falls back to ``UnknownParser`` when metadata is missing or points to
        an image file.

        Returns:
            A tuple ``(atlas, sprites)`` where ``atlas`` is a PIL ``Image``
            (or ``None`` on error) and ``sprites`` is a list of sprite dicts.

        Raises:
            ValueError: If the metadata file has an unsupported extension.
        """
        from PIL import Image

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
            processed_atlas, sprites = UnknownParser.parse_unknown_image(
                self.atlas_path, self.parent_window
            )
            if processed_atlas is not None:
                atlas = processed_atlas

        elif self.metadata_path.endswith(".xml"):
            sprites = XmlParser.parse_xml_data(self.metadata_path)
        elif self.metadata_path.endswith(".txt"):
            sprites = TxtParser.parse_txt_packer(self.metadata_path)
        else:
            raise ValueError(f"Unsupported metadata file format: {self.metadata_path}")
        return atlas, sprites

    def parse_xml_for_preview(self, animation_name):
        """Parse XML metadata for a single animation's sprites.

        Only extracts sprites whose names match ``animation_name``, reducing
        memory and processing time for preview generation.

        Args:
            animation_name: Animation prefix to filter by.

        Returns:
            List of sprite dicts matching the animation.
        """
        if not self.metadata_path or not self.metadata_path.endswith(".xml"):
            return []

        try:
            import xml.etree.ElementTree as ET
            import re

            tree = ET.parse(self.metadata_path)
            xml_root = tree.getroot()

            anim_patterns = [
                animation_name,
                re.sub(r"\d+$", "", animation_name),  # Remove trailing numbers
                re.sub(r"_?\d+$", "", animation_name),  # Remove _digits
                re.sub(r"[-_]?\d+$", "", animation_name),  # Remove -/digits
            ]

            # Remove duplicates while preserving order
            anim_patterns = list(dict.fromkeys(anim_patterns))

            animation_sprites = []
            for sprite in xml_root.findall("SubTexture"):
                sprite_name = sprite.get("name", "")
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
                        "frameWidth": int(
                            sprite.get("frameWidth", sprite.get("width", 0))
                        ),
                        "frameHeight": int(
                            sprite.get("frameHeight", sprite.get("height", 0))
                        ),
                        "rotated": sprite.get("rotated", "false") == "true",
                    }
                    animation_sprites.append(sprite_data)

            return animation_sprites

        except Exception as e:
            print(f"Error parsing XML for animation {animation_name}: {e}")
            return []

    def parse_txt_for_preview(self, animation_name):
        """Parse TXT metadata for a single animation's sprites.

        Only extracts sprites whose names match ``animation_name``, reducing
        memory and processing time for preview generation.

        Args:
            animation_name: Animation prefix to filter by.

        Returns:
            List of sprite dicts matching the animation.
        """
        if not self.metadata_path or not self.metadata_path.endswith(".txt"):
            return []

        try:
            import re

            all_sprites = TxtParser.parse_txt_packer(self.metadata_path)

            anim_patterns = [
                animation_name,
                re.sub(r"\d+$", "", animation_name),  # Remove trailing numbers
                re.sub(r"_?\d+$", "", animation_name),  # Remove _digits
                re.sub(r"[-_]?\d+$", "", animation_name),  # Remove -/digits
            ]
            anim_patterns = list(dict.fromkeys(anim_patterns))

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
