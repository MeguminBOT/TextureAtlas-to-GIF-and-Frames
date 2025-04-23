from PIL import Image
import os
import re
import tempfile
from wand.image import Image as WandImg
from wand.color import Color
import numpy

class AnimationProcessor:
    """
    A class to process animations from a texture atlas and save them as individual frames or animations (GIF/WebP).
    Attributes:
        animations (dict): A dictionary containing animation names and their corresponding image tuples.
        atlas_path (str): The path to the texture atlas.
        output_dir (str): The directory where the output frames and animations will be saved.
        create_gif (bool): Flag to indicate whether to create GIF animations.
        create_webp (bool): Flag to indicate whether to create WebP animations.
        set_framerate (int): The framerate for the animations.
        set_loopdelay (int): The delay between loops for the animations.
        set_minperiod (int): The minimum period for the animations.
        set_scale (float): The scale factor for the images.
        set_threshold (float): The threshold for transparency in GIFs.
        set_indices (list): The indices of frames to be used.
        keep_frames (str): The frames to keep ('all', 'first', 'last', 'none', or a range).
        crop_option (str): The cropping type to use for PNG images.
        var_delay (bool): Flag to indicate whether to use variable delay between frames.
        fnf_idle_loop (bool): *FNF* Flag to indicate whether to set 'loop delay' to 0 for idle animations.
        user_settings (dict): User-defined settings for specific animations.
        quant_frames (dict): A dictionary to store quantized frames.
        current_version (str): The current version of the processor.
    Methods:
        process_animations(): Processes the animations and saves the frames and animations.
        is_single_frame(image_tuples): Checks if the animation consists of a single frame.
        get_kept_frames(settings, keep_frames, single_frame): Determines which frames to keep based on settings.
        get_kept_frame_indices(kept_frames, image_tuples): Gets the indices of the frames to keep.
        save_frames(image_tuples, kept_frame_indices, spritesheet_name, animation_name, scale): Saves the individual frames.
        save_animations(image_tuples, spritesheet_name, animation_name, settings, current_version): Saves the animations as GIF or WebP.
        save_webp(images, spritesheet_name, animation_name, fps, delay, period): Saves the animation as a WebP file.
        save_gif(images, spritesheet_name, animation_name, fps, delay, period, threshold, max_size, image_tuples, current_version): Saves the animation as a GIF file.
        scale_image(img, size): Scales the image by the given size factor.
    """

    def __init__(self, animations, atlas_path, output_dir, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, set_indices, keep_frames, crop_option, var_delay, fnf_idle_loop, user_settings, current_version):
        self.animations = animations
        self.atlas_path = atlas_path
        self.output_dir = output_dir
        self.create_gif = create_gif
        self.create_webp = create_webp
        self.set_framerate = set_framerate
        self.set_loopdelay = set_loopdelay
        self.set_minperiod = set_minperiod
        self.set_scale = set_scale
        self.set_threshold = set_threshold
        self.set_indices = set_indices
        self.keep_frames = keep_frames
        self.crop_option = crop_option
        self.var_delay = var_delay
        self.fnf_idle_loop = fnf_idle_loop
        self.user_settings = user_settings
        self.quant_frames = {}
        self.current_version = current_version

    def process_animations(self):
        frames_generated = 0
        anims_generated = 0
        spritesheet_name = os.path.split(self.atlas_path)[1]
        for animation_name, image_tuples in self.animations.items():
            print(f"Processing animation: {animation_name}")
            settings = self.user_settings.get(spritesheet_name + '/' + animation_name, {})
            scale = settings.get('scale', self.set_scale)
            image_tuples.sort(key=lambda x: x[0])
            indices = settings.get('indices', self.set_indices)
            if indices:
                indices = list(filter(lambda i: ((i < len(image_tuples)) & (i >= 0)), indices))
                image_tuples = [image_tuples[i] for i in indices]
            single_frame = self.is_single_frame(image_tuples)
            kept_frames = self.get_kept_frames(settings, self.keep_frames, single_frame)
            kept_frame_indices = self.get_kept_frame_indices(kept_frames, image_tuples)
            if self.fnf_idle_loop and "idle" in animation_name.lower():
                settings['delay'] = 0
            frames_generated += self.save_frames(image_tuples, kept_frame_indices, animation_name, scale)
            if self.create_gif or self.create_webp:
                anims_generated += self.save_animations(image_tuples, spritesheet_name, animation_name, settings, self.current_version)
        return frames_generated, anims_generated

    def is_single_frame(self, image_tuples):
        for i in image_tuples:
            if i[2] != image_tuples[0][2]:
                return False
        return True

    def get_kept_frames(self, settings, keep_frames, single_frame):
        if single_frame:
            return '0'
        kept_frames = settings.get('frames', keep_frames)
        if kept_frames == 'all':
            kept_frames = '0--1'
        elif kept_frames == 'first':
            kept_frames = '0'
        elif kept_frames == 'last':
            kept_frames = '-1'
        elif re.fullmatch(r'first, ?last', kept_frames):
            kept_frames = '0,-1'
        elif kept_frames == 'none':
            kept_frames = ''
        return [ele for ele in kept_frames.split(',')]

    def get_kept_frame_indices(self, kept_frames, image_tuples):
        kept_frame_indices = set()
        for entry in kept_frames:
            try:
                if '--' in entry:
                    start_frame, end_frame = map(int, entry.split('--'))
                    if start_frame < 0:
                        start_frame += len(image_tuples)
                    if end_frame < 0:
                        end_frame += len(image_tuples)
                    frame_range = range(max(start_frame, 0), min(end_frame + 1, len(image_tuples)))
                    kept_frame_indices.update(frame_range)
                else:
                    frame_index = int(entry)
                    if frame_index < 0:
                        frame_index += len(image_tuples)
                    if 0 <= frame_index < len(image_tuples):
                        kept_frame_indices.add(frame_index)
            except ValueError:
                if entry != '':
                    start_frame = int(re.match(r'-?\d+', entry).group())
                    if start_frame < 0:
                        start_frame += len(image_tuples)
                    end_frame = int(re.search(r'(?<=-)-?\d+$', entry).group())
                    if end_frame < 0:
                        end_frame += len(image_tuples)
                    if (start_frame < 0 and end_frame < 0) or (start_frame >= len(image_tuples) and end_frame >= len(image_tuples)):
                        continue
                    frame_range = range(max(start_frame, 0), min(end_frame + 1, len(image_tuples)))
                    kept_frame_indices.update(frame_range)
        return kept_frame_indices

    def save_frames(self, image_tuples, kept_frame_indices, animation_name, scale):
        frames_generated = 0
        if len(image_tuples) == 0:
            return frames_generated

        frames_folder = os.path.join(self.output_dir, animation_name)
        os.makedirs(frames_folder, exist_ok=True)

        if self.crop_option == "Animation based":
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
                frame_filename = os.path.join(frames_folder, frame[0] + '.png')
                frame_image = frame[1]
                bbox = frame_image.getbbox()
                if bbox:
                    if self.crop_option == "Frame based":
                        cropped_frame = frame_image.crop(bbox)
                        final_frame_image = self.scale_image(cropped_frame, scale)
                    elif self.crop_option == "Animation based":
                        cropped_frame = frame_image.crop((min_x, min_y, max_x, max_y))
                        final_frame_image = self.scale_image(cropped_frame, scale)
                    else:
                        final_frame_image = self.scale_image(frame_image, scale)
                    final_frame_image.save(frame_filename)
                    frames_generated += 1
                    print(f"Saved frame: {frame_filename}")
        return frames_generated

    def save_animations(self, image_tuples, spritesheet_name, animation_name, settings, current_version):
        anims_generated = 0
        fps = settings.get('fps', self.set_framerate)
        delay = settings.get('delay', self.set_loopdelay)
        period = settings.get('period', self.set_minperiod)
        scale = settings.get('scale', self.set_scale)
        threshold = settings.get('threshold', min(max(self.set_threshold,0),1))
        images = [img[1] for img in image_tuples]
        sizes = [frame.size for frame in images]
        max_size = tuple(map(max, zip(*sizes)))
        min_size = tuple(map(min, zip(*sizes)))
        if max_size != min_size:
            for index, frame in enumerate(images):
                new_frame = Image.new('RGBA', max_size)
                new_frame.paste(frame)
                images[index] = new_frame

        if self.create_webp:
            self.save_webp(images, spritesheet_name, animation_name, fps, delay, period, scale)
            print(f"Saved WEBP animation: {os.path.join(self.output_dir, os.path.splitext(spritesheet_name)[0] + f' {animation_name}.webp')}")
        if self.create_gif:
            self.save_gif(images, spritesheet_name, animation_name, fps, delay, period, scale, threshold, max_size, image_tuples, current_version)
            print(f"Saved GIF animation: {os.path.join(self.output_dir, os.path.splitext(spritesheet_name)[0] + f' {animation_name}.gif')}")
        anims_generated += 1
        return anims_generated

    def save_webp(self, images, spritesheet_name, animation_name, fps, delay, period, scale):
        durations = []
        if self.var_delay:
            for index in range(len(images)):
                durations.append(round((index+1)*1000/fps) - round(index*1000/fps))
        else:
            durations = [round(1000/fps)] * len(images)
        durations[-1] += delay
        durations[-1] += max(period - sum(durations), 0)
        scaled_images = list(map(lambda x: self.scale_image(x, scale), images))
        scaled_images[0].save(os.path.join(self.output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.webp"), save_all=True, append_images=scaled_images[1:], disposal=2, duration=durations, loop=0, lossless=True)

    def save_gif(self, images, spritesheet_name, animation_name, fps, delay, period, scale, threshold, max_size, image_tuples, current_version):
        for frame in images:
            alpha = frame.getchannel('A')
            if (threshold == 1):
                alpha = alpha.point(lambda i: i >= 255 and 255)
            else:
                alpha = alpha.point(lambda i: i > 255*threshold and 255)
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
        if self.var_delay:
            for index in range(len(images)):
                durations.append(round((index+1)*1000/fps, -1) - round(index*1000/fps, -1))
        else:
            durations = [round(1000/fps, -1)] * len(cropped_images)
        durations[-1] += delay
        durations[-1] += max(round(period, -1) - sum(durations), 0)
        cropped_images[0].save(os.path.join(self.output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.gif"), save_all=True, append_images=cropped_images[1:], disposal=2, optimize=False, duration=durations, loop=0, comment=f'GIF generated by: TextureAtlas to GIF and Frames v{current_version}')

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
