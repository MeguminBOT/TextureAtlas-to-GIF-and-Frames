import os
import numpy
from PIL.PngImagePlugin import PngInfo
from wand.color import Color
from wand.image import Image as WandImg

from core.extractor.frame_pipeline import (
    build_frame_durations,
    compute_shared_bbox,
    prepare_scaled_sequence,
)
from core.extractor.image_utils import pad_frames_to_canvas
from utils.utilities import Utilities


class AnimationExporter:
    """
    Exports animations (GIF, WebP, APNG) from a sequence of image frames.

    Attributes:
        output_dir (str):
            Directory where exported animations will be saved.
        current_version (str):
            Version string to include in metadata.
        scale_image_func (str):
            Function to scale images before saving.

    Methods:
        save_animations(image_tuples, spritesheet_name, animation_name, settings) -> int
            Processes and saves the animation in the specified format (GIF, WebP, or APNG).
        remove_dups(animation)
            Removes duplicate frames from a Wand animation, merging delays as needed.
        save_gif(images, filename, fps, delay, period, scale, threshold, settings)
            Saves the animation as a GIF file.
        save_webp(images, filename, fps, delay, period, scale, settings)
            Saves the animation as a WebP file.
        save_apng(images, filename, fps, delay, period, scale, settings)
            Saves the animation as an APNG file.
    """

    def __init__(self, output_dir, current_version, scale_image_func):
        self.output_dir = output_dir
        self.current_version = current_version
        self.scale_image = scale_image_func

    def save_animations(self, image_tuples, spritesheet_name, animation_name, settings):
        anims_generated = 0

        if not image_tuples:
            print(
                f"No frames available for animation: {animation_name}, skipping animation export"
            )
            return anims_generated

        fps = settings.get("fps")
        delay = settings.get("delay")
        period = settings.get("period")
        scale = settings.get("scale")
        threshold = settings.get("threshold")
        animation_format = settings.get("animation_format")

        images = pad_frames_to_canvas([img[1] for img in image_tuples])

        filename = settings.get("filename")

        if not filename:
            filename = Utilities.format_filename(
                settings.get("prefix"),
                spritesheet_name,
                animation_name,
                settings.get("filename_format"),
                settings.get("replace_rules"),
                settings.get("suffix"),
            )

        if animation_format == "GIF":
            self.save_gif(
                images, filename, fps, delay, period, scale, threshold, settings
            )
        elif animation_format == "WebP":
            self.save_webp(images, filename, fps, delay, period, scale, settings)
        elif animation_format == "APNG":
            self.save_apng(images, filename, fps, delay, period, scale, settings)

        anims_generated += 1
        return anims_generated

    def save_webp(self, images, filename, fps, delay, period, scale, settings):
        final_images = prepare_scaled_sequence(
            images,
            self.scale_image,
            scale,
            settings.get("crop_option"),
        )
        if not final_images:
            return

        durations = build_frame_durations(
            len(final_images),
            fps,
            delay,
            period,
            settings.get("var_delay", False),
        )
        if not durations:
            return

        webp_filename = os.path.join(self.output_dir, f"{filename}.webp")

        final_images[0].save(
            webp_filename,
            save_all=True,
            append_images=final_images[1:],
            disposal=2,
            duration=durations,
            loop=0,
            lossless=True,
        )
        print(f"Saved WEBP animation: {webp_filename}")

    def remove_dups(self, animation):
        animation.iterator_reset()
        if len(animation.sequence) < 2:
            return

        while animation.iterator_next():
            index = animation.iterator_get()
            if index == 0:
                continue

            if (
                animation.get_image_distortion(
                    animation.sequence[index - 1], metric="absolute"
                )
                == 0
            ):
                delay = animation.delay
                animation.image_remove()
                animation.iterator_set(index - 1)
                animation.delay += delay

    def save_gif(
        self, images, filename, fps, delay, period, scale, threshold, settings
    ):
        durations = build_frame_durations(
            len(images),
            fps,
            delay,
            period,
            settings.get("var_delay", False),
            round_to_ten=True,
        )
        if not durations:
            return

        width, height = images[0].size
        crop_option = settings.get("crop_option")
        crop_mode = (crop_option or "None").lower()
        should_crop = crop_mode != "none"
        crop_bounds = None
        if should_crop:
            crop_bounds = compute_shared_bbox(images)
            if crop_bounds is None:
                should_crop = False

        left, upper, right, lower = width, height, 0, 0
        with WandImg(width=width, height=height) as animation:
            animation.image_remove()
            for index, pil_frame in enumerate(images):
                arr = numpy.array(pil_frame)
                with WandImg.from_array(arr) as wand_frame:
                    if should_crop:
                        if threshold == 1:
                            wand_frame.negate(channel="alpha")
                            wand_frame.threshold(0, channel="alpha")
                            wand_frame.negate(channel="alpha")
                        else:
                            wand_frame.threshold(threshold, channel="alpha")

                    wand_frame.background_color = Color("None")
                    wand_frame.alpha_channel = "background"

                    wand_frame.delay = int(durations[index] / 10)
                    wand_frame.dispose = "background"
                    animation.sequence.append(wand_frame)
            if should_crop and crop_bounds is None:
                print(f"Warning: No frames to save for GIF: {filename}.gif")
                return
            if should_crop and crop_bounds:
                left, upper, right, lower = crop_bounds
            if should_crop and left > right:
                print(f"Warning: No frames to save for GIF: {filename}.gif")
                return
            self.remove_dups(animation)
            animation.quantize(
                number_colors=256, colorspace_type="undefined", dither=False
            )
            # Removing duplicates after quantization ensures palette changes are accounted for once.
            self.remove_dups(animation)
            for i in range(len(animation.sequence)):
                animation.iterator_set(i)
                if should_crop and crop_bounds:
                    animation.crop(left, upper, right, lower)

                animation.sample(
                    width=int(animation.width * abs(scale)),
                    height=int(animation.height * abs(scale)),
                )

                if scale < 0:
                    animation.flop()

            gif_filename = os.path.join(self.output_dir, f"{filename}.gif")
            animation.loop = 0
            animation.options["comment"] = (
                f"GIF generated by: TextureAtlas to GIF and Frames v{self.current_version}"
            )
            animation.save(filename=gif_filename)

            print(f"Saved GIF animation: {gif_filename}")

    def save_apng(self, images, filename, fps, delay, period, scale, settings):
        final_images = prepare_scaled_sequence(
            images,
            self.scale_image,
            scale,
            settings.get("crop_option"),
        )
        if not final_images:
            return

        durations = build_frame_durations(
            len(final_images),
            fps,
            delay,
            period,
            settings.get("var_delay", False),
        )
        if not durations:
            return

        apng_filename = os.path.join(self.output_dir, f"{filename}.png")

        metadata = PngInfo()
        metadata.add_text(
            "Comment",
            f"APNG generated by TextureAtlas to GIF and Frames v{self.current_version}",
        )

        final_images[0].save(
            apng_filename,
            save_all=True,
            append_images=final_images[1:],
            duration=durations,
            loop=0,
            format="PNG",
            disposal=2,
            pnginfo=metadata,
        )
        print(f"Saved APNG animation: {apng_filename}")
