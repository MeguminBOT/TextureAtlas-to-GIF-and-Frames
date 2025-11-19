"""Symbol timeline renderer for Adobe Spritemap support."""

from __future__ import annotations

import warnings
from typing import Dict, List, Optional

import numpy as np
from PIL import Image, ImageChops

from .transform_matrix import TransformMatrix
from .color_effect import ColorEffect
from .metadata import compute_layers_length, extract_label_ranges_from_layers

IDENTITY_M3D = [
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
]


class Symbols:
    """Render nested symbol timelines exported by Adobe Animate."""

    def __init__(self, animation_json, sprite_atlas, canvas_size):
        self.background_color = (0, 0, 0, 0)
        self.canvas_size = canvas_size
        self.sprite_atlas = sprite_atlas
        self.timelines = {}

        for symbol in animation_json.get("SD", {}).get("S", []):
            name = symbol.get("SN")
            if name in self.timelines:
                raise ValueError(f"Symbol `{name}` is not unique")
            self.timelines[name] = symbol.get("TL", {}).get("L", [])

        self.timelines[None] = animation_json.get("AN", {}).get("TL", {}).get("L", [])
        self.label_map: Dict[Optional[str], List[Dict[str, int]]] = {
            name: extract_label_ranges_from_layers(layers)
            for name, layers in self.timelines.items()
        }
        self.center_in_canvas = TransformMatrix(c=canvas_size[0] // 2, f=canvas_size[1] // 2)

    def length(self, symbol_name):
        return compute_layers_length(self.timelines.get(symbol_name))

    def render_symbol(self, name, frame_index):
        canvas = Image.new("RGBA", self.canvas_size, color=self.background_color)
        self._render_symbol(canvas, name, frame_index, self.center_in_canvas, ColorEffect())
        return canvas

    def _render_symbol(self, canvas, name, frame_index, matrix, color):
        canvas_stack = []
        for layer in reversed(self.timelines.get(name, [])):
            frames = layer.get("FR", [])
            if not frames:
                continue

            low = 0
            high = len(frames) - 1
            while low != high:
                mid = (low + high + 1) // 2
                if frame_index < frames[mid]["I"]:
                    high = mid - 1
                else:
                    low = mid
            frame = frames[low]
            if not (frame["I"] <= frame_index < frame["I"] + frame["DU"]):
                continue

            if (layer.get("Clpb") and not canvas_stack) or layer.get("LT") == "Clp":
                canvas_stack.append(canvas)
                canvas = Image.new("RGBA", self.canvas_size, color=(0, 0, 0, 0))

            for element in frame.get("E", []):
                if "SI" in element:
                    instance = element["SI"]
                    element_name = instance.get("SN")
                    first_frame = instance.get("FF", 0)
                    element_color = color @ ColorEffect.parse(instance["C"]) if "C" in instance else color
                    transform = TransformMatrix.parse(instance.get("M3D", IDENTITY_M3D))
                    self._render_symbol(canvas, element_name, first_frame, matrix @ transform, element_color)
                else:
                    atlas_instance = element.get("ASI", {})
                    sprite_name = atlas_instance.get("N")
                    transform = TransformMatrix.parse(atlas_instance.get("M3D", IDENTITY_M3D))
                    sprite, dest = self.sprite_atlas.get_sprite(sprite_name, matrix @ transform, color)
                    if sprite is not None:
                        canvas.alpha_composite(sprite, dest=dest)

            if layer.get("LT") == "Clp":
                mask_canvas = canvas
                masked_canvas = canvas_stack.pop()
                base_canvas = canvas_stack.pop()

                mask_bbox = mask_canvas.getbbox()
                if mask_bbox is None:
                    warnings.warn(f"Mask `{layer.get('LN')}` in symbol `{name}` is fully transparent")
                    base_canvas.alpha_composite(masked_canvas)
                else:
                    mask_canvas = mask_canvas.crop(mask_bbox)
                    masked_canvas = masked_canvas.crop(mask_bbox)
                    masked_alpha = masked_canvas.getchannel("A")

                    mask_alpha = np.array(mask_canvas.getchannel("A"))
                    mask_alpha = mask_alpha if np.max(mask_alpha) == 0 else mask_alpha / np.max(mask_alpha) * 255
                    mask_alpha = Image.fromarray(mask_alpha.clip(0, 255).astype("uint8"), "L")
                    masked_canvas.putalpha(ImageChops.multiply(masked_alpha, mask_alpha))
                    base_canvas.alpha_composite(masked_canvas, dest=mask_bbox[:2])

                canvas = base_canvas

    def get_label_ranges(self, symbol_name: Optional[str]):
        return self.label_map.get(symbol_name, [])

    def get_label_range(self, symbol_name: Optional[str], label_name: str):
        for entry in self.label_map.get(symbol_name, []):
            if entry["name"] == label_name:
                return entry
        return None
