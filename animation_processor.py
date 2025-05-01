from PIL import Image
from PIL.PngImagePlugin import PngInfo
import os
import re
import tempfile
from wand.image import Image as WandImg
from wand.color import Color
import numpy

# Import our own modules
from utilities import Utilities

class AnimationProcessor:
    """
    A class to process animations from a texture atlas and save them as individual frames or animations (GIF/WebP).

    Attributes:
        animations (dict): A dictionary containing animation names and their corresponding image tuples.
        atlas_path (str): The path to the texture atlas.
        output_dir (str): The directory where the output frames and animations will be saved.
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        current_version (str): The current version of the application.
        quant_frames (dict): A dictionary to store quantized frames for optimized GIF generation.

    Methods:
        process_animations():
            Processes the animations and saves the frames and animations.
        is_single_frame(image_tuples):
            Checks if the animation consists of a single frame (or repeats of the same frame).
        get_kept_frames(settings, single_frame):
            Determines which frames to keep based on the settings and whether the animation is a single frame.
        get_kept_frame_indices(kept_frames, image_tuples):
            Gets the indices of the frames to keep based on the kept frames.
        save_frames(image_tuples, kept_frame_indices, spritesheet_name, animation_name, scale, settings):
            Saves the individual frames to the output directory.
        save_animations(image_tuples, spritesheet_name, animation_name, settings):
            Saves the animations as GIF or WebP files based on the settings.
        save_webp(images, spritesheet_name, animation_name, fps, delay, period, scale, settings):
            Saves the animation as a WebP file.
        save_gif(images, spritesheet_name, animation_name, fps, delay, period, scale, threshold, max_size, image_tuples, settings):
            Saves the animation as a GIF file with optional transparency and optimization.
        scale_image(img, size):
            Scales the image by the given size factor, optionally flipping it horizontally.
    """

    def __init__(self, animations, atlas_path, output_dir, settings_manager, current_version):
        self.animations = animations
        self.atlas_path = atlas_path
        self.output_dir = output_dir
        self.settings_manager = settings_manager
        self.current_version = current_version
        self.quant_frames = {}

    def process_animations(self):
        frames_generated = 0
        anims_generated = 0

        spritesheet_name = os.path.split(self.atlas_path)[1]

        for animation_name, image_tuples in self.animations.items():
            print(f"Processing animation: {animation_name}")

            settings = self.settings_manager.get_settings(spritesheet_name, animation_name)
            scale = settings.get('scale', 1)
            image_tuples.sort(key=lambda x: x[0])

            indices = settings.get('indices', None)
            if indices:
                indices = list(filter(lambda i: ((i < len(image_tuples)) & (i >= 0)), indices))
                image_tuples = [image_tuples[i] for i in indices]
            single_frame = self.is_single_frame(image_tuples)

            kept_frames = self.get_kept_frames(settings, single_frame, image_tuples)
            kept_frame_indices = self.get_kept_frame_indices(kept_frames, image_tuples)

            if settings.get('fnf_idle_loop', False) and "idle" in animation_name.lower():
                settings['delay'] = 0
            frames_generated += self.save_frames(image_tuples, kept_frame_indices, spritesheet_name, animation_name, scale, settings)

            animation_format = settings.get('animation_format', 'None')
            if not single_frame and animation_format != 'None':
                anims_generated += self.save_animations(image_tuples, spritesheet_name, animation_name, settings)

        return frames_generated, anims_generated

    def is_single_frame(self, image_tuples):
        for i in image_tuples:
            if i[2] != image_tuples[0][2]:
                for i in image_tuples:
                    if i[1] != image_tuples[0][1]:
                        return False
                return True
        return True

    def get_kept_frames(self, settings, single_frame, image_tuples):
        if single_frame:
            return ['0']

        kept_frames = settings.get('keep_frames', 'All')
        if kept_frames == 'All':
            return [str(i) for i in range(len(image_tuples))]
        elif kept_frames == 'First':
            return ['0']
        elif kept_frames == 'Last':
            return ['-1']
        elif kept_frames == 'First, Last':
            return ['0', '-1']
        elif kept_frames == 'None':
            return []
        elif kept_frames == 'No duplicates':
            unique_frames = []
            unique_indices = []
            for i, frame in enumerate(image_tuples):
                if frame[1] not in unique_frames:
                    unique_frames.append(frame[1])
                    unique_indices.append(str(i))
            return unique_indices
        else:
            return kept_frames.split(',')

    def get_kept_frame_indices(self, kept_frames, image_tuples):
        kept_frame_indices = set()
        
        for entry in kept_frames:
            if '-' in entry:
                try:
                    start, end = map(int, entry.split('-'))
                    if start < 0:
                        start += len(image_tuples)
                    if end < 0:
                        end += len(image_tuples)
                    kept_frame_indices.update(range(max(0, start), min(len(image_tuples), end + 1)))
                except ValueError:
                    continue
            else:
                try:
                    frame_index = int(entry)
                    if frame_index < 0:
                        frame_index += len(image_tuples)
                    if 0 <= frame_index < len(image_tuples):
                        kept_frame_indices.add(frame_index)
                except ValueError:
                    continue
        return kept_frame_indices

    def save_frames(self, image_tuples, kept_frame_indices, spritesheet_name, animation_name, scale, settings):
        frames_generated = 0
        if len(image_tuples) == 0:
            return frames_generated

        frames_folder = os.path.join(self.output_dir, animation_name)
        os.makedirs(frames_folder, exist_ok=True)

        crop_option = settings.get('crop_option', 'None')

        if crop_option == "Animation based":
            min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0
            for index, frame in enumerate(image_tuples):
                if index in kept_frame_indices:
                    bbox = frame[1].getbbox()
                    if bbox:
                        min_x = min(min_x, bbox[0])
                        min_y = min(min_y, bbox[1])
                        max_x = max(max_x, bbox[2])
                        max_y = max(max_y, bbox[3])

            if min_x > max_x:
                return frames_generated

        for index, frame in enumerate(image_tuples):
            if index in kept_frame_indices:
                formatted_frame_name = Utilities.format_filename(
                    settings.get('prefix', ''),
                    spritesheet_name,
                    frame[0],
                    settings.get('filename_format', 'Standardized')
                )
                frame_filename = os.path.join(frames_folder, f"{formatted_frame_name}.png")
                frame_image = frame[1]

                bbox = frame_image.getbbox()
                if bbox:
                    if crop_option == "Frame based":
                        cropped_frame = frame_image.crop(bbox)
                        final_frame_image = self.scale_image(cropped_frame, scale)

                    elif crop_option == "Animation based":
                        cropped_frame = frame_image.crop((min_x, min_y, max_x, max_y))
                        final_frame_image = self.scale_image(cropped_frame, scale)

                    else:
                        final_frame_image = self.scale_image(frame_image, scale)

                    metadata = PngInfo()
                    metadata.add_text("Comment", f'PNG generated by TextureAtlas to GIF and Frames v{self.current_version}')

                    final_frame_image.save(frame_filename, pnginfo=metadata)
                    frames_generated += 1
                    print(f"Saved frame: {frame_filename}")
        return frames_generated

    def save_animations(self, image_tuples, spritesheet_name, animation_name, settings):
        anims_generated = 0

        fps = settings.get('fps', 24)
        delay = settings.get('delay', 250)
        period = settings.get('period', 0)
        scale = settings.get('scale', 1)
        threshold = settings.get('threshold', 0.5)
        animation_format = settings.get('animation_format', 'None')

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
            self.save_gif(images, spritesheet_name, animation_name, fps, delay, period, scale, threshold, max_size, image_tuples, settings)
        elif animation_format == 'WebP':
            self.save_webp(images, spritesheet_name, animation_name, fps, delay, period, scale, settings)
        elif animation_format == 'APNG':
            self.save_apng(images, spritesheet_name, animation_name, fps, delay, period, scale, settings)

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

        cropped_images = []
        for frame in images:
            cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
            cropped_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get('var_delay', False)
        if var_delay:
            for index in range(len(cropped_images)):
                durations.append(round((index + 1) * 1000 / fps) - round(index * 1000 / fps))
        else:
            durations = [round(1000 / fps)] * len(cropped_images)
        durations[-1] += delay
        durations[-1] += max(period - sum(durations), 0)

        formatted_webp_name = Utilities.format_filename(
            settings.get('prefix', ''),
            spritesheet_name,
            animation_name,
            settings.get('filename_format', 'Standardized')
        )
        webp_filename = os.path.join(self.output_dir, f"{formatted_webp_name}.webp")

        cropped_images[0].save(
            webp_filename,
            save_all=True,
            append_images=cropped_images[1:],
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

            if image_tuples[index][2] + (threshold,) in self.quant_frames:
                images[index] = self.quant_frames[image_tuples[index][2] + (threshold,)]
                if images[index].size != max_size:
                    new_frame = Image.new('RGBA', max_size)
                    new_frame.paste(frame)
                    images[index] = new_frame
            else:
                with WandImg.from_array(numpy.array(frame)) as wand_frame:
                    wand_frame.background_color = Color('None')
                    wand_frame.alpha_channel = 'background'
                    wand_frame.trim(background_color='None')

                    if wand_frame.colors > 256:
                        wand_frame.quantize(number_colors=256, colorspace_type='undefined', dither=False)
                    wand_frame.coalesce()

                    fd, temp_filename = tempfile.mkstemp(suffix='.gif')
                    wand_frame.save(filename=temp_filename)

                    with Image.open(temp_filename) as quant_frame:
                        images[index] = quant_frame
                        quant_frame.load()
                        self.quant_frames[image_tuples[index][2] + (threshold,)] = quant_frame
                    os.close(fd)
                    os.remove(temp_filename)

        if min_x > max_x:
            return

        cropped_images = []
        for frame in images:
            cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
            cropped_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get('var_delay', False)
        if var_delay:
            for index in range(len(images)):
                durations.append(round((index + 1) * 1000 / fps, -1) - round(index * 1000 / fps, -1))
        else:
            durations = [round(1000 / fps, -1)] * len(cropped_images)
        durations[-1] += delay
        durations[-1] += max(round(period, -1) - sum(durations), 0)

        formatted_gif_name = Utilities.format_filename(
            settings.get('prefix', ''), 
            spritesheet_name, 
            animation_name, 
            settings.get('filename_format', 'Standardized')
        )
        gif_filename = os.path.join(self.output_dir, f"{formatted_gif_name}.gif")

        cropped_images[0].save(
            gif_filename,
            save_all=True,
            append_images=cropped_images[1:],
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

        cropped_images = []
        for frame in images:
            cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
            cropped_images.append(self.scale_image(cropped_frame, scale))

        durations = []
        var_delay = settings.get('var_delay', False)
        if var_delay:
            for index in range(len(images)):
                durations.append(int(round((index + 1) * 1000 / fps)) - int(round(index * 1000 / fps)))
        else:
            durations = [int(round(1000 / fps))] * len(cropped_images)
        durations[-1] += int(delay)
        durations[-1] += max(int(round(period)) - sum(durations), 0)

        formatted_apng_name = Utilities.format_filename(
            settings.get('prefix', ''),
            spritesheet_name,
            animation_name,
            settings.get('filename_format', 'Standardized')
        )
        apng_filename = os.path.join(self.output_dir, f"{formatted_apng_name}.png")
        
        metadata = PngInfo()
        metadata.add_text("Comment", f'APNG generated by TextureAtlas to GIF and Frames v{self.current_version}')

        cropped_images[0].save(
            apng_filename,
            save_all=True,
            append_images=cropped_images[1:],
            duration=durations,
            loop=0,
            format="PNG",
            disposal=2,
            pnginfo=metadata
        )
        print(f"Saved APNG animation: {apng_filename}")

    def scale_image(self, img, size):
        if size < 0:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if abs(size) == 1:
            return img
        else:
            new_width_float = img.width * abs(size)
            new_height_float = img.height * abs(size)
            new_width = round(new_width_float)
            new_height = round(new_height_float)
            return img.resize((new_width, new_height), Image.NEAREST)