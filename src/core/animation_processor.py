from PIL import Image
import os

# Import our own modules
from core.frame_selector import FrameSelector
from core.frame_exporter import FrameExporter
from core.animation_exporter import AnimationExporter


class AnimationProcessor:
    """
    A class to process animations from a texture atlas.

    Attributes:
        animations (dict): A dictionary containing animation names and their corresponding image tuples.
        atlas_path (str): The path to the texture atlas.
        output_dir (str): The directory where the output frames and animations will be saved.
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        current_version (str): The current version of the application.

    Methods:
        process_animations(is_unknown_spritesheet=False):
            Processes the animations and saves the frames and animations. 
            is_unknown_spritesheet parameter determines whether to apply extra cropping for unknown spritesheets.
        scale_image(img, size):
            Scales the image by the given size factor, optionally flipping it horizontally.
    """

    def __init__(self, animations, atlas_path, output_dir, settings_manager, current_version, spritesheet_label=None):
        self.animations = animations
        self.atlas_path = atlas_path
        self.output_dir = output_dir
        self.settings_manager = settings_manager
        self.current_version = current_version
        self.spritesheet_label = spritesheet_label or os.path.split(self.atlas_path)[1]
        self.frame_exporter = FrameExporter(
            self.output_dir, self.current_version, self.scale_image
        )
        self.animation_exporter = AnimationExporter(
            self.output_dir, self.current_version, self.scale_image
        )

    def process_animations(self, is_unknown_spritesheet=False):
        frames_generated = 0
        anims_generated = 0

        spritesheet_name = self.spritesheet_label

        for animation_name, image_tuples in self.animations.items():
            print(f"Processing animation: {animation_name}")

            settings = self.settings_manager.get_settings(
                spritesheet_name, f"{spritesheet_name}/{animation_name}"
            )
            scale = settings.get("scale")
            image_tuples.sort(key=lambda x: x[0])

            indices = settings.get("indices")
            if indices:
                indices = list(
                    filter(lambda i: ((i < len(image_tuples)) & (i >= 0)), indices)
                )
                image_tuples = [image_tuples[i] for i in indices]
            single_frame = FrameSelector.is_single_frame(image_tuples)

            kept_frames = FrameSelector.get_kept_frames(
                settings, single_frame, image_tuples
            )
            kept_frame_indices = FrameSelector.get_kept_frame_indices(
                kept_frames, image_tuples
            )

            alignment_overrides = settings.get("alignment_overrides")
            aligned_tuples = (
                self._apply_alignment_overrides(image_tuples, alignment_overrides)
                if alignment_overrides
                else image_tuples
            )

            if settings.get("fnf_idle_loop") and "idle" in animation_name.lower():
                settings["delay"] = 0

            # Check if frame export is enabled and format is available
            frame_export = settings.get("frame_export", False)
            if frame_export and settings.get("frame_format") != "None":
                frames_generated += self.frame_exporter.save_frames(
                    aligned_tuples,
                    kept_frame_indices,
                    spritesheet_name,
                    animation_name,
                    scale,
                    settings,
                    is_unknown_spritesheet,
                )

            # Check if animation export is enabled and format is available
            animation_export = settings.get("animation_export", False)
            animation_format = settings.get("animation_format")
            if not single_frame and animation_export and animation_format != "None":
                anims_generated += self.animation_exporter.save_animations(
                    aligned_tuples, spritesheet_name, animation_name, settings
                )

        return frames_generated, anims_generated

    def _apply_alignment_overrides(self, image_tuples, overrides):
        """Rebuild frames using the manual offsets configured in the editor."""
        canvas = overrides.get("canvas") or []
        default_offset = overrides.get("default", {})
        default_x = int(default_offset.get("x", 0))
        default_y = int(default_offset.get("y", 0))
        frames_map = overrides.get("frames", {})

        if len(canvas) == 2:
            canvas_width = max(1, int(canvas[0]))
            canvas_height = max(1, int(canvas[1]))
        else:
            widths = [img[1].width for img in image_tuples]
            heights = [img[1].height for img in image_tuples]
            canvas_width = max(widths) if widths else 1
            canvas_height = max(heights) if heights else 1

        adjusted = []
        for name, frame_image, metadata in image_tuples:
            offset_data = frames_map.get(name, {})
            offset_x = int(offset_data.get("x", default_x))
            offset_y = int(offset_data.get("y", default_y))
            canvas_image = Image.new("RGBA", (canvas_width, canvas_height))
            # Anchor around the center so offsets nudge relative to the origin crosshair
            target_x = (canvas_width - frame_image.width) // 2 + offset_x
            target_y = (canvas_height - frame_image.height) // 2 + offset_y
            canvas_image.paste(frame_image, (target_x, target_y), frame_image)
            adjusted.append((name, canvas_image, metadata))

        return adjusted

    def scale_image(self, img, size):
        if size < 0:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        new_width_float = img.width * abs(size)
        new_height_float = img.height * abs(size)
        new_width = round(new_width_float)
        new_height = round(new_height_float)
        return img.resize((new_width, new_height), Image.NEAREST)
