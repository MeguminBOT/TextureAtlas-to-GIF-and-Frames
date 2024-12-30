def extract_sprites(atlas_path, metadata_path, output_dir, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, set_indices, keep_frames, var_delay, hq_colors):
    frames_generated = 0
    anims_generated = 0
    sprites_failed = 0
    try:
        atlas = Image.open(atlas_path)

        if metadata_path.endswith('.xml'):
            tree = ET.parse(metadata_path)
            root = tree.getroot()
            sprites = [
                {
                    'name': sprite.get('name'),
                    'x': int(sprite.get('x')),
                    'y': int(sprite.get('y')),
                    'width': int(sprite.get('width')),
                    'height': int(sprite.get('height')),
                    'frameX': int(sprite.get('frameX', 0)),
                    'frameY': int(sprite.get('frameY', 0)),
                    'frameWidth': int(sprite.get('frameWidth', sprite.get('width'))),
                    'frameHeight': int(sprite.get('frameHeight', sprite.get('height'))),
                    'rotated': sprite.get('rotated', 'false') == 'true'
                } for sprite in root.findall('SubTexture')
            ]
        else:
            sprites = parse_plain_text_atlas(metadata_path)

        animations = {}
        quant_frames = {}
        spritesheet_name = os.path.split(atlas_path)[1]

        for sprite in sprites:
            name = sprite['name']
            x, y, width, height = sprite['x'], sprite['y'], sprite['width'], sprite['height']
            frameX = sprite.get('frameX', 0)
            frameY = sprite.get('frameY', 0)
            frameWidth = sprite.get('frameWidth', width)
            frameHeight = sprite.get('frameHeight', height)
            rotated = sprite.get('rotated', False)

            sprite_image = atlas.crop((x, y, x + width, y + height))

            if rotated:
                sprite_image = sprite_image.rotate(90, expand=True)
                frameWidth = max(height-frameX, frameWidth, 1)
                frameHeight = max(width-frameY, frameHeight, 1)
            else:
                frameWidth = max(width-frameX, frameWidth, 1)
                frameHeight = max(height-frameY, frameHeight, 1)

            frame_image = Image.new('RGBA', (frameWidth, frameHeight))
            frame_image.paste(sprite_image, (-frameX, -frameY))

            if frame_image.mode != 'RGBA':
                frame_image = frame_image.convert('RGBA')
            folder_name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()

            animations.setdefault(folder_name, []).append((name, frame_image, (x, y, width, height, frameX, frameY)))

        for animation_name, image_tuples in animations.items():
            settings = user_settings.get(spritesheet_name + '/' + animation_name, {})
            scale = settings.get('scale', set_scale)
            image_tuples.sort(key=lambda x: x[0])

            indices = settings.get('indices', set_indices)

            if indices:
                indices = list(filter(lambda i: ((i < len(image_tuples)) & (i >= 0)), indices))
                image_tuples = [image_tuples[i] for i in indices]

            single_frame = True
            for i in image_tuples:
                if i[2] != image_tuples[0][2]:
                    single_frame = False
                    break

            if single_frame:
                kept_frames = '0'
            else:
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
                kept_frames = [ele for ele in kept_frames.split(',')]

            kept_frame_indices = set()
            for entry in kept_frames:
                try:
                    frame_index = int(entry)
                    if frame_index < 0:
                       frame_index += len(image_tuples)
                    if frame_index >= 0 and frame_index < len(image_tuples):
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
                        frame_range = range(max(start_frame,0),min(end_frame+1,len(image_tuples)))
                        for i in frame_range:
                            kept_frame_indices.add(i)

            if single_frame:
                frame_filename = os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.png")
                if len(image_tuples) == 0:
                    continue
                frame_image = image_tuples[0][1]
                bbox = frame_image.getbbox()
                if bbox is None:
                    continue
                cropped_frame_image = scale_image(frame_image.crop(bbox), scale)
                cropped_frame_image.save(frame_filename)
                frames_generated += 1
                continue
            else:
                frames_folder = os.path.join(output_dir, animation_name)
                for index, frame in enumerate(image_tuples):
                    frame_filename = os.path.join(frames_folder, image_tuples[index][0] + '.png')
                    if index in kept_frame_indices:
                        frame_image = image_tuples[index][1]
                        bbox = frame_image.getbbox()
                        if bbox is None:
                            continue
                        cropped_frame_image = scale_image(frame_image.crop(bbox), scale)
                        os.makedirs(frames_folder, exist_ok=True)
                        cropped_frame_image.save(frame_filename)
                        frames_generated += 1
                    
            if create_gif or create_webp:
                fps = settings.get('fps', set_framerate)
                delay = settings.get('delay', set_loopdelay)
                period = settings.get('period', set_minperiod)
                threshold = settings.get('threshold', min(max(set_threshold,0),1))
                images = [img[1] for img in image_tuples]
                sizes = [frame.size for frame in images]
                max_size = tuple(map(max, zip(*sizes)))
                min_size = tuple(map(min, zip(*sizes)))
                if max_size != min_size:
                    for index, frame in enumerate(images):
                        new_frame = Image.new('RGBA', max_size)
                        new_frame.paste(frame)
                        images[index] = new_frame

                if create_webp:
                    durations = []
                    if var_delay:
                        for index in range(len(images)):
                            durations.append(round((index+1)*1000/fps) - round(index*1000/fps))
                    else:
                        durations = [round(1000/fps)] * len(images)
                    durations[-1] += delay
                    durations[-1] += max(period - sum(durations), 0)
                    scaled_images = list(map(lambda x: scale_image(x, scale), images))

                    scaled_images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.webp"), save_all=True, append_images=images[1:], disposal=2, duration=durations, loop=0, lossless=True)

                if create_gif:
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
    
                        if not hq_colors:
                            continue

                        if image_tuples[index][2] + (threshold,) in quant_frames:
                            images[index] = quant_frames[image_tuples[index][2] + (threshold,)]
                            if images[index].size != max_size:
                                new_frame = Image.new('RGBA', max_size)
                                new_frame.paste(frame)
                                images[index] = new_frame
                        else:
                            with WandImg.from_array(numpy.array(frame)) as wand_frame:
                                wand_frame.background_color = Color('None')
                                wand_frame.alpha_channel = 'background'
                                wand_frame.trim(background_color='None')
                                wand_frame.quantize(number_colors=256, dither=False)
                                wand_frame.coalesce()
                                fd, temp_filename = tempfile.mkstemp(suffix='.gif')
                                wand_frame.save(filename=temp_filename)
                                with Image.open(temp_filename) as quant_frame:
                                    images[index] = quant_frame
                                    quant_frame.load()
                                    quant_frames[image_tuples[index][2] + (threshold,)] = quant_frame
                                os.close(fd)
                                os.remove(temp_filename)
                        
                    width, height = max_x - min_x, max_y - min_y
                    cropped_images = []
                    for frame in images:
                        cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                        cropped_images.append(scale_image(cropped_frame, scale))
                    durations = []
                    if var_delay:
                        for index in range(len(images)):
                            durations.append(round((index+1)*1000/fps, -1) - round(index*1000/fps, -1))
                    else:
                        durations = [round(1000/fps, -1)] * len(cropped_images)
                    durations[-1] += delay
                    durations[-1] += max(round(period, -1) - sum(durations), 0)
                    cropped_images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.gif"), save_all=True, append_images=cropped_images[1:], disposal=2, optimize=False, duration=durations, loop=0, comment=f'GIF generated by: TextureAtlas to GIF and Frames v{current_version}')
