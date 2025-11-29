"""Sprite atlas slicing and transformation for Adobe Spritemap exports.

Provides ``SpriteAtlas``, which parses spritemap JSON, caches cropped sprites,
and applies affine transforms and colour effects before returning render-ready
images.
"""

from __future__ import annotations

import math
import warnings
import numpy as np
from PIL import Image

from .transform_matrix import TransformMatrix
from .color_effect import ColorEffect


class SpriteAtlas:
    """Cache and transform sprites defined in spritemap JSON metadata.

    Sprites are lazily cropped from the atlas on first access and cached for
    subsequent renders. Transforms and colour effects are applied per-request.

    Attributes:
        img: The atlas image converted to ``RGBa`` mode for compositing.
        canvas_width: Target canvas width in pixels.
        canvas_height: Target canvas height in pixels.
        resample: Pillow resampling filter used for affine transforms.
        sprite_info: Dict mapping sprite names to bounding boxes and rotation.
        sprites: Cache of cropped sprite images keyed by name.
    """

    def __init__(self, spritemap_json, atlas_image, canvas_size, resample):
        """Load sprite metadata and prepare the atlas for fast cropping.

        Args:
            spritemap_json: Parsed JSON dict describing sprite regions.
            atlas_image: PIL ``Image`` of the packed atlas.
            canvas_size: ``(width, height)`` of the target render canvas.
            resample: Pillow resampling constant (e.g., ``Image.BICUBIC``).
        """

        if atlas_image.mode == "P":
            atlas_image = atlas_image.convert("RGBA")
        self.img = atlas_image.convert("RGBa")
        self.canvas_width, self.canvas_height = canvas_size
        self.resample = resample
        self.sprite_info = {}
        self.sprites = {}

        for sprite in spritemap_json.get("ATLAS", {}).get("SPRITES", []):
            data = sprite["SPRITE"] if "SPRITE" in sprite else sprite
            x = data.get("x", 0)
            y = data.get("y", 0)
            w = data.get("w", 0)
            h = data.get("h", 0)
            self.sprite_info[data["name"]] = {
                "box": (x, y, x + w, y + h),
                "rotated": data.get("rotated", False),
            }

    def get_sprite(self, name, matrix: TransformMatrix, color: ColorEffect):
        """Return a transformed sprite image and its canvas offset.

        The sprite is cropped from the atlas on first access and cached. The
        provided transform and colour effect are then applied.

        Args:
            name: Sprite identifier from the spritemap JSON.
            matrix: Affine transform to apply.
            color: Colour effect chain to apply before transforming.

        Returns:
            A tuple ``(image, (x, y))`` where ``image`` is an RGBA PIL Image
            and ``(x, y)`` is the top-left canvas coordinate. Returns
            ``(None, None)`` if the sprite is out of bounds or unknown.
        """

        if name not in self.sprites:
            sprite_info = self.sprite_info.get(name)
            if sprite_info is None:
                return None, None
            sprite = self.img.crop(sprite_info["box"])
            if sprite_info.get("rotated"):
                sprite = sprite.transpose(Image.ROTATE_90)
            self.sprites[name] = sprite
        else:
            sprite = self.sprites[name]

        width, height = sprite.size
        corners = matrix.m @ np.array(
            [[0, width, 0, width], [0, 0, height, height], [1, 1, 1, 1]]
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
        matrix = TransformMatrix(c=-min_x, f=-min_y) @ matrix
        sprite = color(sprite)
        sprite = sprite.transform(
            transform_size, Image.AFFINE, data=matrix.data(), resample=self.resample
        )
        return sprite.convert("RGBA"), (min_x, min_y)
