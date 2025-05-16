import os
import tempfile
import numpy
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from wand.image import Image as WandImg
from wand.color import Color

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
        quant_frames (str):
            Stores quantized frames for optimized GIF generation.

    Methods:
        save_animations(image_tuples, spritesheet_name, animation_name, settings) -> int
            Processes and saves the animation in the specified format (GIF, WebP, or APNG).
        save_gif(images, spritesheet_name, animation_name, fps, delay, period, scale, threshold, max_size, image_tuples, settings)
            Saves the animation as a GIF file.
        save_webp(images, spritesheet_name, animation_name, fps, delay, period, scale, settings)
            Saves the animation as a WebP file.
        save_apng(images, spritesheet_name, animation_name, fps, delay, period, scale, settings)
            Saves the animation as an APNG file.
    """

    def __init__(self, output_dir, current_version, scale_image_func, quant_frames):
        self.output_dir = output_dir
        self.current_version = current_version
        self.scale_image = scale_image_func
        self.quant_frames = quant_frames

    def save_animations(self, image_tuples, spritesheet_name, animation_name, settings):
        anims_generated = 0

        fps = settings.get('fps')
        delay = settings.get('delay')
        period = settings.get('period')
        scale = settings.get('scale')
        threshold = settings.get('threshold')
        animation_format = settings.get('animation_format')

        images = [img[1] for img in image_tuples]
        sizes = [frame.size for frame in images]
        max_size = tuple(map(max, zip(*sizes)))
        min_size = tuple(map(min, zip(*sizes)))

        if max_size != min_size:
            for index, frame in enumerate(images):
                new_frame = Image.new('RGBA', max_size)
                new_frame.paste(frame)
                images[index] = new_frame

        if animation_format == 'GIF':
            self.save_gif(
                images, spritesheet_name, animation_name, fps, delay, period,
                scale, threshold, max_size, image_tuples, settings
            )
        elif animation_format == 'WebP':
            self.save_webp(
                images, spritesheet_name, animation_name, fps, delay, period,
                scale, settings
            )
        elif animation_format == 'APNG':
            self.save_apng(
                images, spritesheet_name, animation_name, fps, delay, period,
                scale, settings
            )

        anims_generated += 1
        return anims_generated

    def save_webp(self, images, spritesheet_name, animation_name, fps, delay, period, scale, settings):
        min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0

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
        if settings.get('crop_option') == 'None':
            final_images = list(map(lambda x: self.scale_image(x, scale), images))
        else:
            for frame in images:
                cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                final_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get('var_delay')
        if var_delay:
            for index in range(len(final_images)):
                durations.append(round((index + 1) * 1000 / fps) - round(index * 1000 / fps))
        else:
            durations = [round(1000 / fps)] * len(final_images)

        durations[-1] += delay
        durations[-1] += max(period - sum(durations), 0)

        formatted_webp_name = Utilities.format_filename(
            settings.get('prefix'),
            spritesheet_name,
            animation_name,
            settings.get('filename_format'),
            settings.get('replace_rules')
        )
        webp_filename = os.path.join(self.output_dir, f"{formatted_webp_name}.webp")

        final_images[0].save(
            webp_filename,
            save_all=True,
            append_images=final_images[1:],
            disposal=2,
            duration=durations,
            loop=0,
            lossless=True
        )
        print(f"Saved WEBP animation: {webp_filename}")

    def save_gif(self, images, spritesheet_name, animation_name, fps, delay, period, scale, threshold, max_size, image_tuples, settings):
        for frame in images:
            alpha = frame.getchannel('A')
            if threshold == 1:
                alpha = alpha.point(lambda i: i >= 255 and 255)
            else:
                alpha = alpha.point(lambda i: i > 255 * threshold and 255)
            frame.putalpha(alpha)

        min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0

        for index, frame in enumerate(images):
            bbox = frame.getbbox()
            if bbox is None:
                continue
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

            quant_key = image_tuples[index][2] + (threshold,)
            if quant_key in self.quant_frames:
                images[index] = self.quant_frames[quant_key]
                if images[index].size != max_size:
                    new_frame = Image.new('RGBA', max_size)
                    new_frame.paste(frame)
                    images[index] = new_frame
            else:
                with WandImg.from_array(numpy.array(frame)) as wand_frame:
                    wand_frame.background_color = Color('None')
                    wand_frame.alpha_channel = 'background'
                    wand_frame.trim(color=Color('None'))
                    if wand_frame.colors > 256:
                        wand_frame.quantize(number_colors=256, colorspace_type='undefined', dither=False)
                    wand_frame.coalesce()
                    fd, temp_filename = tempfile.mkstemp(suffix='.gif')
                    wand_frame.save(filename=temp_filename)
                    with Image.open(temp_filename) as quant_frame:
                        images[index] = quant_frame
                        quant_frame.load()
                        self.quant_frames[quant_key] = quant_frame
                    os.close(fd)
                    os.remove(temp_filename)

        if min_x > max_x:
            return

        final_images = []
        if settings.get('crop_option') == 'None':
            final_images = list(map(lambda x: self.scale_image(x, scale), images))
        else:
            for frame in images:
                cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                final_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get('var_delay')
        if var_delay:
            for index in range(len(images)):
                durations.append(round((index + 1) * 1000 / fps, -1) - round(index * 1000 / fps, -1))
        else:
            durations = [round(1000 / fps, -1)] * len(final_images)

        durations[-1] += delay
        durations[-1] += max(round(period, -1) - sum(durations), 0)

        formatted_gif_name = Utilities.format_filename(
            settings.get('prefix'),
            spritesheet_name,
            animation_name,
            settings.get('filename_format'),
            settings.get('replace_rules')
        )
        gif_filename = os.path.join(self.output_dir, f"{formatted_gif_name}.gif")

        final_images[0].save(
            gif_filename,
            save_all=True,
            append_images=final_images[1:],
            disposal=2,
            optimize=False,
            duration=durations,
            loop=0,
            comment=f'GIF generated by: TextureAtlas to GIF and Frames v{self.current_version}'
        )
        print(f"Saved GIF animation: {gif_filename}")

    def save_apng(self, images, spritesheet_name, animation_name, fps, delay, period, scale, settings):
        min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0

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
        if settings.get('crop_option') == 'None':
            final_images = list(map(lambda x: self.scale_image(x, scale), images))
        else:
            for frame in images:
                cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                final_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get('var_delay')
        if var_delay:
            for index in range(len(images)):
                durations.append(int(round((index + 1) * 1000 / fps)) - int(round(index * 1000 / fps)))
        else:
            durations = [int(round(1000 / fps))] * len(final_images)

        durations[-1] += int(delay)
        durations[-1] += max(int(round(period)) - sum(durations), 0)

        formatted_apng_name = Utilities.format_filename(
            settings.get('prefix'),
            spritesheet_name,
            animation_name,
            settings.get('filename_format'),
            settings.get('replace_rules')
        )
        apng_filename = os.path.join(self.output_dir, f"{formatted_apng_name}.png")

        metadata = PngInfo()
        metadata.add_text("Comment", f'APNG generated by TextureAtlas to GIF and Frames v{self.current_version}')

        final_images[0].save(
            apng_filename,
            save_all=True,
            append_images=final_images[1:],
            duration=durations,
            loop=0,
            format="PNG",
            disposal=2,
            pnginfo=metadata
        )
        print(f"Saved APNG animation: {apng_filename}")