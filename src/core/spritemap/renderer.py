"""High level Adobe Spritemap renderer used by the extractor."""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from PIL import Image

from utils.utilities import Utilities
from .sprite_atlas import SpriteAtlas
from .symbols import Symbols


class AdobeSpritemapRenderer:
    """Render symbol animations defined by Adobe Animate spritemaps."""

    def __init__(
        self,
        animation_path: str,
        spritemap_json_path: str,
        atlas_image_path: str,
        canvas_size=None,
        resample=Image.BICUBIC,
        filter_single_frame: bool = True,
    ):
        self.animation_path = animation_path
        self.spritemap_json_path = spritemap_json_path
        self.atlas_image_path = atlas_image_path

        with open(animation_path, "r", encoding="utf-8") as animation_file:
            self.animation_json = json.load(animation_file)

        with open(spritemap_json_path, "rb") as spritemap_file:
            spritemap_json = json.loads(spritemap_file.read().decode("utf-8-sig"))

        atlas_image = Image.open(atlas_image_path)
        if canvas_size is None:
            canvas_size = atlas_image.size

        self.frame_rate = self.animation_json.get("MD", {}).get("FRT", 24)
        self.filter_single_frame = filter_single_frame
        self.sprite_atlas = SpriteAtlas(spritemap_json, atlas_image, canvas_size, resample)
        self.symbols = Symbols(self.animation_json, self.sprite_atlas, canvas_size)

    def list_symbol_names(self) -> List[str]:
        return [symbol.get("SN") for symbol in self.animation_json.get("SD", {}).get("S", []) if symbol.get("SN")]

    def build_animation_frames(self) -> Dict[str, List[Tuple[str, Image.Image, Tuple[int, int, int, int, int, int]]]]:
        animations: Dict[str, List[Tuple[str, Image.Image, Tuple[int, int, int, int, int, int]]]] = {}

        for symbol_name in self.list_symbol_names():
            frames = self._render_symbol_frames(symbol_name)
            if not frames:
                continue
            if self.filter_single_frame and len(frames) <= 1:
                continue
            folder_name = Utilities.strip_trailing_digits(symbol_name)
            animations.setdefault(folder_name, []).extend(frames)

        for label in self.symbols.get_label_ranges(None):
            frames = self._render_symbol_frames(
                None,
                start_frame=label["start"],
                end_frame=label["end"],
                frame_name_prefix=label["name"],
            )
            if not frames:
                continue
            if self.filter_single_frame and len(frames) <= 1:
                continue
            folder_name = label["name"]
            animations.setdefault(folder_name, []).extend(frames)

        return animations

    def _render_symbol_frames(
        self,
        symbol_name: Optional[str],
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        frame_name_prefix: Optional[str] = None,
    ):
        total_frames = self.symbols.length(symbol_name)
        if total_frames == 0:
            return []

        if end_frame is None or end_frame > total_frames:
            end_frame = total_frames

        if start_frame >= end_frame:
            return []

        rendered_frames: List[Tuple[str, Image.Image, Tuple[int, int, int, int, int, int]]] = []
        frames_with_index = []

        for frame_index in range(start_frame, end_frame):
            frame_image = self.symbols.render_symbol(symbol_name, frame_index)
            if frame_image is None:
                continue
            frames_with_index.append((frame_index - start_frame, frame_image))

        if not frames_with_index:
            return []

        sizes = [frame.size for _, frame in frames_with_index]
        max_width = max(width for width, _ in sizes)
        max_height = max(height for _, height in sizes)
        canvas_size = (max_width, max_height)

        normalized_frames = []
        for frame_index, frame in frames_with_index:
            if frame.size != canvas_size:
                new_frame = Image.new("RGBA", canvas_size)
                offset = ((canvas_size[0] - frame.size[0]) // 2, (canvas_size[1] - frame.size[1]) // 2)
                new_frame.paste(frame, offset)
                frame = new_frame
            normalized_frames.append((frame_index, frame))

        min_x, min_y, max_x, max_y = float("inf"), float("inf"), 0, 0
        for _, frame in normalized_frames:
            bbox = frame.getbbox()
            if bbox:
                min_x = min(min_x, bbox[0])
                min_y = min(min_y, bbox[1])
                max_x = max(max_x, bbox[2])
                max_y = max(max_y, bbox[3])

        if min_x > max_x:
            return []

        prefix = frame_name_prefix or (symbol_name if symbol_name else "timeline")

        for frame_index, frame in normalized_frames:
            cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
            frame_name = f"{prefix}_{frame_index:04d}"
            rendered_frames.append((frame_name, cropped_frame, (0, 0, cropped_frame.width, cropped_frame.height, 0, 0)))

        return rendered_frames

    def ensure_animation_defaults(self, settings_manager, spritesheet_name):
        for animation_name in self.list_symbol_names():
            folder_name = Utilities.strip_trailing_digits(animation_name)
            full_name = f"{spritesheet_name}/{folder_name}"
            sprite_settings = settings_manager.animation_settings.setdefault(full_name, {})
            sprite_settings.setdefault("fps", self.frame_rate)

        for label in self.symbols.get_label_ranges(None):
            label_name = label["name"]
            full_name = f"{spritesheet_name}/{label_name}"
            sprite_settings = settings_manager.animation_settings.setdefault(full_name, {})
            sprite_settings.setdefault("fps", self.frame_rate)

    def render_animation(self, target):
        target_type, target_value = self._normalize_target(target)

        if target_type == "timeline_label":
            label_range = self.symbols.get_label_range(None, target_value)
            if not label_range:
                return []
            return self._render_symbol_frames(
                None,
                start_frame=label_range["start"],
                end_frame=label_range["end"],
                frame_name_prefix=target_value,
            )

        return self._render_symbol_frames(target_value)

    def _normalize_target(self, target):
        if isinstance(target, dict):
            return target.get("type", "symbol"), target.get("value")
        return "symbol", target
