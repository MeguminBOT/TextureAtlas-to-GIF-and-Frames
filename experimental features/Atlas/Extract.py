from PIL import Image
from SpriteMapData import SpriteMap
from AnimationData import Animation, Timeline, Frame, Matrix3D

def create_animated_gif_with_timeline(sprite_map_path, sprite_sheet_path, animation_data, output_gif_path, duration=100):
    sprite_map = SpriteMap(sprite_sheet_path)
    sprite_map.load_from_json(sprite_map_path)
    sprite_sheet = Image.open(sprite_sheet_path)

    frames = []
    for timeline in animation_data.TL.L:
        for frame_data in timeline.FR:
            frame = sprite_map.find_frame(frame_data.N)
            box = (frame.x, frame.y, frame.x + frame.width, frame.y + frame.height)
            frame_image = sprite_sheet.crop(box)

            if hasattr(frame_data, 'M3D'):
                frame_image = apply_transform(frame_image, frame_data.M3D)
            frames.append((frame_image, frame_data.DU if hasattr(frame_data, 'DU') else duration))

    if frames:
        images, durations = zip(*frames)
        images[0].save(
            output_gif_path,
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0
        )
    print(f"GIF created at {output_gif_path}")

def apply_transform(image, matrix3d):
    # Matrix3D to a PIL or WAND-compatible transform
    # Placeholder
    print(f"Applying transformation: {matrix3d}")
    return image

## Use example:
# create_animated_gif_with_timeline(
#     sprite_map_path='path_to_sprite_map.json',
#     sprite_sheet_path='spritemap.png',
#     animation_data=Animation(),  # Replace with actual AnimationData instance
#     output_gif_path='output.gif',
#     duration=100
# )
