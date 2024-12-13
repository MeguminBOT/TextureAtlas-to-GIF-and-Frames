""" 
Code taken from PluieElectrique's Texture Atlas Renderer. 
Repository: https://github.com/PluieElectrique/texture-atlas-renderer

Will be edited to fit TextureAtlas to GIF and Frames functionality.
"""

import warnings
import numpy as np
from PIL import Image, ImageColor


class ColorEffect:
    """Color effects for RGBA images."""

    def __init__(self, effect=None):
        # None is a no-op effect
        self.effect = effect

    @classmethod
    def parse(cls, effect):
        """Create a ColorEffect from a `C` dictionary."""
        mode = effect["M"]
        # Advanced: multiply and offset each channel
        if mode == "AD":
            # Multipliers are in [-1, 1]
            multiplier = np.array(
                [
                    effect["RM"],
                    effect["GM"],
                    effect["BM"],
                    effect["AM"],
                ]
            )
            # Offsets are in [-255, 255]
            offset = np.array(
                [
                    effect["RO"],
                    effect["GO"],
                    effect["BO"],
                    effect["AO"],
                ]
            )
        elif mode == "CA":
            multiplier = np.array([1, 1, 1, effect["AM"]])
            offset = np.zeros(4)
        elif mode == "CBRT":
            brightness = effect["BRT"]
            if brightness < 0:
                multiplier = np.array(
                    [1 + brightness, 1 + brightness, 1 + brightness, 1]
                )
                offset = np.zeros(4)
            else:
                multiplier = np.array(
                    [1 - brightness, 1 - brightness, 1 - brightness, 1]
                )
                offset = brightness * np.array([255, 255, 255, 0])
        elif mode == "T":
            tint_color = ImageColor.getrgb(effect["TC"])
            tint_multiplier = effect["TM"]
            multiplier = np.array(
                [1 - tint_multiplier, 1 - tint_multiplier, 1 - tint_multiplier, 1]
            )
            offset = tint_multiplier * np.array([*tint_color, 0])
        else:
            warnings.warn(f"Unsupported color effect: {effect}")
            return cls()

        return cls((multiplier, offset))

    def __call__(self, im):
        # An effect of None will return the input image.
        if self.effect is not None:
            mode = im.mode
            im = im.convert("RGBA")

            # We could use ImageMath to do everything in Pillow, but it's 4-5x
            # slower than NumPy. We clip to [0, 255] because that's what
            # Animate does. We need to cast to uint8 or the image will be
            # completely messed up.
            multiplier, offset = self.effect
            im = Image.fromarray(
                (np.array(im) * multiplier + offset).clip(0, 255).astype("uint8"),
                mode="RGBA",
            )

            im = im.convert(mode)

        return im

    def __eq__(self, other):
        if type(other) is not ColorEffect:
            return False
        elif self.effect is None or other.effect is None:
            return self.effect is other.effect
        else:
            multiplier_self, offset_self = self.effect
            multiplier_other, offset_other = other.effect
            return (
                multiplier_self.tobytes() == multiplier_other.tobytes()
                and offset_self.tobytes() == offset_other.tobytes()
            )

    def __hash__(self):
        if self.effect is None:
            return hash(None)
        else:
            multiplier, offset = self.effect
            return hash((multiplier.tobytes(), offset.tobytes()))

    def __matmul__(self, other):
        if type(other) is not ColorEffect:
            raise TypeError(
                f"expected type ColorEffect, but operand has type {type(other)}"
            )

        # ColorEffects are immutable, so it's fine to not always return a new instance.
        if self.effect is None:
            return other
        elif other.effect is None:
            return self
        else:
            multiplier_self, offset_self = self.effect
            multiplier_other, offset_other = other.effect
            return ColorEffect(
                (
                    multiplier_self * multiplier_other,
                    multiplier_self * offset_other + offset_self,
                )
            )

    def __repr__(self):
        return f"ColorEffect({self.effect!r})"