import re

import numpy as np

from utils.utilities import Utilities


class SpriteProcessor:
    """Process sprite metadata extracted from an atlas image."""

    def __init__(self, atlas, sprites):
        self.atlas = atlas
        # Cache an RGBA atlas so downstream crops avoid repeated conversions.
        self._atlas_rgba = atlas if atlas.mode == "RGBA" else atlas.convert("RGBA")
        # Keep a NumPy view of the atlas so each sprite extraction is a cheap slice.
        self._atlas_array = np.ascontiguousarray(np.asarray(self._atlas_rgba))
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

        sprite_array = self._atlas_array[y : y + height, x : x + width]
        requires_canvas = rotated or frame_x or frame_y

        if rotated:
            sprite_array = np.rot90(sprite_array)
            sprite_height, sprite_width = sprite_array.shape[:2]
            frame_width = max(height - frame_x, frame_width, 1)
            frame_height = max(width - frame_y, frame_height, 1)
        else:
            sprite_height, sprite_width = sprite_array.shape[:2]
            frame_width = max(width - frame_x, frame_width, 1)
            frame_height = max(height - frame_y, frame_height, 1)

        if frame_width != sprite_width or frame_height != sprite_height:
            requires_canvas = True

        if requires_canvas:
            frame_array = self._compose_frame_array(
                sprite_array,
                frame_width,
                frame_height,
                frame_x,
                frame_y,
            )
        else:
            frame_array = sprite_array

        metadata = (x, y, width, height, frame_x, frame_y)
        return name, frame_array, metadata

    @staticmethod
    def _compose_frame_array(
        sprite_array: np.ndarray,
        frame_width: int,
        frame_height: int,
        frame_x: int,
        frame_y: int,
    ) -> np.ndarray:
        """Place the trimmed sprite onto its logical canvas using NumPy slices."""

        canvas = np.zeros(
            (frame_height, frame_width, sprite_array.shape[2]), dtype=np.uint8
        )

        # Negative frame offsets mean the sprite content belongs farther right/down on the canvas.
        dest_x = max(0, -frame_x)
        dest_y = max(0, -frame_y)
        src_x = max(0, frame_x)
        src_y = max(0, frame_y)

        copy_width = min(frame_width - dest_x, sprite_array.shape[1] - src_x)
        copy_height = min(frame_height - dest_y, sprite_array.shape[0] - src_y)

        if copy_width > 0 and copy_height > 0:
            canvas[
                dest_y : dest_y + copy_height,
                dest_x : dest_x + copy_width,
            ] = sprite_array[
                src_y : src_y + copy_height,
                src_x : src_x + copy_width,
            ]

        return canvas
