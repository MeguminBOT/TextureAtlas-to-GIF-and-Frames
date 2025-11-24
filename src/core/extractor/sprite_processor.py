import re

from PIL import Image

from utils.utilities import Utilities


class SpriteProcessor:
    """Process sprite metadata extracted from an atlas image."""

    def __init__(self, atlas, sprites):
        self.atlas = atlas
        self.sprites = sprites

    def process_sprites(self):
        """Process all sprites in the atlas and group them into animations."""
        animations = {}
        for sprite in self.sprites:
            frame_tuple = self._build_frame_tuple(sprite)
            if frame_tuple is None:
                continue
            name = frame_tuple[0]
            folder_name = Utilities.strip_trailing_digits(name)
            animations.setdefault(folder_name, []).append(frame_tuple)
        return animations

    def process_specific_animation(self, animation_name):
        """Process only sprites belonging to a specific animation."""
        patterns = [
            animation_name,
            re.sub(r"\d+$", "", animation_name),
            re.sub(r"_?\d+$", "", animation_name),
            re.sub(r"[-_]?\d+$", "", animation_name),
        ]
        patterns = list(dict.fromkeys(patterns))

        matching_sprites = []
        for sprite in self.sprites:
            sprite_name = sprite.get("name", "")
            if any(
                sprite_name == pat or sprite_name.startswith(pat) for pat in patterns
            ):
                matching_sprites.append(sprite)

        if not matching_sprites:
            return {}

        animations = {}
        for sprite in matching_sprites:
            frame_tuple = self._build_frame_tuple(sprite)
            if frame_tuple is None:
                continue
            name = frame_tuple[0]
            folder_name = Utilities.strip_trailing_digits(name)
            animations.setdefault(folder_name, []).append(frame_tuple)

        return animations

    def _build_frame_tuple(self, sprite):
        try:
            name = sprite["name"]
            x, y, width, height = (
                sprite["x"],
                sprite["y"],
                sprite["width"],
                sprite["height"],
            )
        except KeyError:
            return None

        frame_x = sprite.get("frameX", 0)
        frame_y = sprite.get("frameY", 0)
        frame_width = sprite.get("frameWidth", width)
        frame_height = sprite.get("frameHeight", height)
        rotated = sprite.get("rotated", False)

        sprite_image = self.atlas.crop((x, y, x + width, y + height))
        if rotated:
            sprite_image = sprite_image.rotate(90, expand=True)
            frame_width = max(height - frame_x, frame_width, 1)
            frame_height = max(width - frame_y, frame_height, 1)
        else:
            frame_width = max(width - frame_x, frame_width, 1)
            frame_height = max(height - frame_y, frame_height, 1)

        frame_image = Image.new("RGBA", (frame_width, frame_height))
        frame_image.paste(sprite_image, (-frame_x, -frame_y))
        if frame_image.mode != "RGBA":
            frame_image = frame_image.convert("RGBA")

        metadata = (x, y, width, height, frame_x, frame_y)
        return name, frame_image, metadata
