import os
import numpy
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from wand.color import Color
from wand.image import Image as WandImg

# Import our own modules
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
            print(f"No frames available for animation: {animation_name}, skipping animation export")
            return anims_generated

        fps = settings.get("fps")
        delay = settings.get("delay")
        period = settings.get("period")
        scale = settings.get("scale")
        threshold = settings.get("threshold")
        animation_format = settings.get("animation_format")

        images = [img[1] for img in image_tuples]
        sizes = [frame.size for frame in images]
        max_size = tuple(map(max, zip(*sizes)))
        min_size = tuple(map(min, zip(*sizes)))

        if max_size != min_size:
            for index, frame in enumerate(images):
                new_frame = Image.new("RGBA", max_size)
                new_frame.paste(frame)
                images[index] = new_frame

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
            self.save_gif(images, filename, fps, delay, period, scale, threshold, settings)
        elif animation_format == "WebP":
            self.save_webp(images, filename, fps, delay, period, scale, settings)
        elif animation_format == "APNG":
            self.save_apng(images, filename, fps, delay, period, scale, settings)

        anims_generated += 1
        return anims_generated

    def save_webp(self, images, filename, fps, delay, period, scale, settings):
        min_x, min_y, max_x, max_y = float("inf"), float("inf"), 0, 0

        for frame in images:
            bbox = frame.getbbox()
            if bbox is None:
                continue
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

        if min_x > max_x:
            return

        final_images = []
        if settings.get("crop_option") == "None":
            final_images = list(map(lambda x: self.scale_image(x, scale), images))
        else:
            for frame in images:
                cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                final_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get("var_delay")
        if var_delay:
            for index in range(len(final_images)):
                durations.append(round((index + 1) * 1000 / fps) - round(index * 1000 / fps))
        else:
            durations = [round(1000 / fps)] * len(final_images)

        durations[-1] += delay
        durations[-1] += max(period - sum(durations), 0)

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

        while animation.iterator_next():
            index = animation.iterator_get()

            if (animation.get_image_distortion(animation.sequence[index - 1], metric="absolute") == 0):
                delay = animation.delay
                animation.image_remove()
                animation.iterator_set(index - 1)
                animation.delay += delay

    def save_gif(self, images, filename, fps, delay, period, scale, threshold, settings):
        durations = []
        if settings.get("var_delay"):
            for index in range(len(images)):
                durations.append(round((index + 1) * 1000 / fps, -1) - round(index * 1000 / fps, -1))
        else:
            durations = [round(1000 / fps, -1)] * len(images)
        durations[-1] += delay
        durations[-1] += max(round(period, -1) - sum(durations), 0)

        width, height = images[0].size
        left, upper, right, lower = width, height, 0, 0
        with WandImg(width=width, height=height) as animation:
            animation.image_remove()
            for index, pil_frame in enumerate(images):
                arr = numpy.array(pil_frame)
                with WandImg.from_array(arr) as wand_frame:
                    if threshold == 1:
                        wand_frame.negate(channel="alpha")
                        wand_frame.threshold(0, channel="alpha")
                        wand_frame.negate(channel="alpha")
                    else:
                        wand_frame.threshold(threshold, channel="alpha")

                    wand_frame.background_color = Color("None")
                    wand_frame.alpha_channel = "background"
                    wand_frame.trim(color="None")
                    wand_frame.delay = int(durations[index] / 10)
                    wand_frame.dispose = "background"

                    if wand_frame.size > (1, 1) or wand_frame[0][0].alpha > 0:
                        left = min(wand_frame.page_x, left)
                        upper = min(wand_frame.page_y, upper)
                        right = max(wand_frame.page_x + wand_frame.width, right)
                        lower = max(wand_frame.page_y + wand_frame.height, lower)
                    else:
                        wand_frame.sample(width=width, height=height)
                    animation.sequence.append(wand_frame)
            if left > right:
                print(f"Warning: No frames to save for GIF: {filename}.gif")
                return
            self.remove_dups(animation)
            animation.iterator_reset()
            for i in range(len(animation.sequence)):
                animation.iterator_set(i)
                animation.quantize(number_colors=256, colorspace_type="undefined", dither=False)
            # We remove duplicate frames twice because different frames may become the same after quantization.
            self.remove_dups(animation)
            for i in range(len(animation.sequence)):
                animation.iterator_set(i)
                animation.extent(width, height, -animation.page_x, -animation.page_y)
                animation.reset_coords()
                
                if settings.get("crop_option") != "None":
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
        min_x, min_y, max_x, max_y = float("inf"), float("inf"), 0, 0

        for frame in images:
            bbox = frame.getbbox()
            if bbox is None:
                continue
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

        if min_x > max_x:
            return

        final_images = []
        if settings.get("crop_option") == "None":
            final_images = list(map(lambda x: self.scale_image(x, scale), images))
        else:
            for frame in images:
                cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                final_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get("var_delay")
        if var_delay:
            for index in range(len(images)):
                start_time = int(round((index + 1) * 1000 / fps))
                end_time = int(round(index * 1000 / fps))
                durations.append(start_time - end_time)
        else:
            durations = [int(round(1000 / fps))] * len(final_images)

        durations[-1] += int(delay)
        durations[-1] += max(int(round(period)) - sum(durations), 0)

        apng_filename = os.path.join(self.output_dir, f"{filename}.png")

        metadata = PngInfo()
        metadata.add_text(
            "Comment", f"APNG generated by TextureAtlas to GIF and Frames v{self.current_version}"
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
