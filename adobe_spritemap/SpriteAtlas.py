""" 
Code taken from PluieElectrique's Texture Atlas Renderer. 
Repository: https://github.com/PluieElectrique/texture-atlas-renderer

Will be edited to fit TextureAtlas to GIF and Frames functionality.
"""

import math
import warnings
import numpy as np

from functools import lru_cache
from PIL import Image

# Import our local modules
from TransformMatrix import TransformMatrix


class SpriteAtlas:
    """Extract and transform sprites."""

    def __init__(self, spritemap_json, img, canvas_size, resample):
        if img.mode == "P":
            img = img.convert("RGBA")
        img = img.convert("RGBa")

        self.img = img
        self.canvas_width, self.canvas_height = canvas_size
        self.resample = resample
        self.sprite_info = {}
        self.sprites = {}

        for sprite in spritemap_json["ATLAS"]["SPRITES"]:
            sprite = sprite["SPRITE"]
            x = sprite["x"]
            y = sprite["y"]
            w = sprite["w"]
            h = sprite["h"]
            self.sprite_info[sprite["name"]] = {
                "box": (x, y, x + w, y + h),
                "rotated": sprite["rotated"],
            }

    # On the animations I tested, 1024 gets almost all of the possible cache
    # hits, so there's little benefit to increasing maxsize further.
    @lru_cache(maxsize=1024)
    def get_sprite(self, name, m, color_effect):
        """Apply a transformation and color effect to a sprite.

        Image.transform() is very slow, and its slowness scales with the output
        size. So, before every .transform(), we add a translation to `m` so that
        the top-left corner of the transformed sprite's bbox is at the origin.
        This keeps the output image as small as possible.
        Thus, this method returns (sprite, (x, y)), where (x, y) is a
        translation offset to put the sprite back at the correct position.
        """
        if name not in self.sprites:
            sprite_info = self.sprite_info[name]
            sprite = self.img.crop(sprite_info["box"])
            if sprite_info["rotated"]:
                sprite = sprite.transpose(Image.ROTATE_90)
            self.sprites[name] = sprite
        else:
            sprite = self.sprites[name]

        w, h = sprite.size
        corners = m.m @ np.array(
            [
                [0, w, 0, w],
                [0, 0, h, h],
                [1, 1, 1, 1],
            ]
        )

        min_x = math.floor(min(corners[0]))
        max_x = math.ceil(max(corners[0]))
        min_y = math.floor(min(corners[1]))
        max_y = math.ceil(max(corners[1]))

        if (
            max_x < 0
            or self.canvas_width <= min_x
            or max_y < 0
            or self.canvas_height <= min_y
        ):
            warnings.warn(
                f"Sprite `{name}` is out of bounds, increase canvas size: "
                f"({min_x:.2f}, {min_y:.2f}) x ({max_x:.2f}, {max_y:.2f})"
            )
            return None, None

        min_x = max(0, min_x)
        max_x = min(self.canvas_width - 1, max_x)
        min_y = max(0, min_y)
        max_y = min(self.canvas_height - 1, max_y)

        transform_size = (max_x - min_x + 1, max_y - min_y + 1)

        # Bring top-left corner to (0, 0) to minimize output size.
        m = TransformMatrix(c=-min_x, f=-min_y) @ m

        # Apply color effect
        sprite = color_effect(sprite)

        sprite = sprite.transform(
            transform_size, Image.AFFINE, data=m.data(), resample=self.resample
        )

        return sprite.convert("RGBA"), (min_x, min_y)