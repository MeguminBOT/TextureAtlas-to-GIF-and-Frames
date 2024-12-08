""" 
Code taken from PluieElectrique's Texture Atlas Renderer. 
Repository: https://github.com/PluieElectrique/texture-atlas-renderer

Will be edited to fit TextureAtlas to GIF and Frames functionality.
"""

import warnings
import numpy as np
from PIL import Image, ImageChops

# Import our local modules
from TransformMatrix import TransformMatrix
from ColorEffect import ColorEffect


class Symbols:
    """Render symbols."""

    def __init__(self, animation_json, sprite_atlas, canvas_size):
 
        self.background_color = (0, 0, 0, 0)

        self.canvas_size = canvas_size
        self.sprite_atlas = sprite_atlas
        self.timelines = {}
        for symbol in animation_json["SD"]["S"]:
            name = symbol["SN"]
            layers = symbol["TL"]["L"]
            # I hope that symbol names are unique
            assert name not in self.timelines, f"Symbol name `{name}` isn't unique"
            self.timelines[name] = layers

        assert None not in self.timelines
        self.timelines[None] = animation_json["AN"]["TL"]["L"]

        self.center_in_canvas = TransformMatrix(
            c=canvas_size[0] // 2, f=canvas_size[1] // 2
        )

    def length(self, symbol_name):
        """The length of a symbol is the index of its final frame."""
        length = 0
        for layer in self.timelines[symbol_name]:
            if layer["FR"]:
                last_frame = layer["FR"][-1]
                length = max(length, last_frame["I"] + last_frame["DU"])
        return length

    def render_symbol(self, name, frame_idx):
        """Render a symbol (on a certain frame) to an image."""
        canvas = Image.new("RGBA", self.canvas_size, color=self.background_color)
        self._render_symbol(
            canvas, name, frame_idx, self.center_in_canvas, ColorEffect()
        )
        return canvas

    def _render_symbol(self, canvas, name, frame_idx, m, color):
        # If this symbol has mask layers, we will need to deal with three
        # canvases: the canvas containing all non-masked sprites, the canvas with the sprites to be masked, and the mask canvas.
        # They will be pushed to this stack in that order (except for the mask canvas, which isn't pushed).
        canvas_stack = []

        # Layers are ordered from front to back. We reverse so that the symbol
        # will be ordered from back to front for rendering.
        for layer in reversed(self.timelines[name]):
            frames = layer["FR"]
            if not frames:
                continue

            # Find frame using binary search
            low = 0
            high = len(frames) - 1
            while low != high:
                mid = (low + high + 1) // 2
                if frame_idx < frames[mid]["I"]:
                    high = mid - 1
                else:
                    low = mid
            frame = frames[low]
            if not (frame["I"] <= frame_idx < frame["I"] + frame["DU"]):
                continue


            if ("Clpb" in layer and not canvas_stack) or layer.get("LT") == "Clp":
                canvas_stack.append(canvas)
                canvas = Image.new("RGBA", self.canvas_size, color=(0, 0, 0, 0))

            # Elements are ordered from back to front, so we don't reverse.
            for element in frame["E"]:
                # Symbol instance
                if "SI" in element:
                    element = element["SI"]
                    element_name = element["SN"]
                    first_frame = element.get("FF", 0)

                    if "C" in element:
                        element_color = color @ ColorEffect.parse(element["C"])
                    else:
                        element_color = color

                    self._render_symbol(
                        canvas,
                        element_name,
                        first_frame,
                        m @ TransformMatrix.parse(element["M3D"]),
                        element_color,
                    )
                # Atlas sprite instance
                else:
                    element = element["ASI"]
                    element_name = element["N"]
                    sprite, dest = self.sprite_atlas.get_sprite(
                        element_name, m @ TransformMatrix.parse(element["M3D"]), color
                    )
                    if sprite is not None:
                        canvas.alpha_composite(sprite, dest=dest)

            # If this is a mask layer, we've finished compositing it, so it's
            # time to apply it.
            if layer.get("LT") == "Clp":
                mask_canvas = canvas
                masked_canvas = canvas_stack.pop()
                base_canvas = canvas_stack.pop()

                # Masks are usually small, so it's faster to first crop the
                # canvas to its visible region.
                mask_bbox = mask_canvas.getbbox()
                if mask_bbox is None:
                    # Animate will apply a mask even if it's completely
                    # transparent because it knows the shape of the mask. But,
                    # a transparent mask is exported as a truly transparent
                    # image, which means we can't apply the mask.
                    warnings.warn(
                        f"Mask `{layer.get('LN')}` in symbol `{name}` "
                        "is fully transparent and can't be applied."
                    )
                    base_canvas.alpha_composite(masked_canvas)
                else:
                    mask_canvas = mask_canvas.crop(mask_bbox)
                    masked_canvas = masked_canvas.crop(mask_bbox)
                    masked_alpha = masked_canvas.getchannel("A")

                    # A mask is supposed to ignore color/transparency and only
                    # care about whether a pixel is "filled" or not. But, all
                    # we have is an image, so we have to use alpha to determine
                    # the shape of the mask.
                    # We could just count non-zero alpha as opaque, but that
                    # may lead to harsh edges. So, to preserve antialiasing, we
                    # use the alpha as it is.
                    # The problem is that a color effect may have scaled alpha.
                    # So, we scale alpha's maximum back to 255.
                    # (It'd be better to skip color effects on mask layers, but
                    # that's complicated. At worst, this approach introduces a
                    # bit of quantization error by casting to uint8 twice.)
                    mask_alpha = np.array(mask_canvas.getchannel("A"))
                    mask_alpha = Image.fromarray(
                        (mask_alpha / np.max(mask_alpha) * 255)
                        .clip(0, 255)
                        .astype("uint8"),
                        "L",
                    )

                    # It's faster to convert mask_alpha to an image and use
                    # ImageChops than it is to convert masked_alpha to a NumPy
                    # array, multiply, and then convert back to an Image.
                    masked_canvas.putalpha(
                        ImageChops.multiply(masked_alpha, mask_alpha)
                    )
                    base_canvas.alpha_composite(masked_canvas, dest=mask_bbox[:2])

                # Restore the original canvas
                canvas = base_canvas